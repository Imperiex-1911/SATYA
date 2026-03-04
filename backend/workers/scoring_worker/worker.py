"""Scoring worker — polls DynamoDB for completed analyses and computes final SATYA score.

Unlike the video/audio/text workers that consume SQS, this worker polls DynamoDB
directly — it looks for records where component scores exist but satya_score doesn't.

Run on host machine:
    cd C:\\AIB\\backend
    python -m workers.scoring_worker.worker
"""

import os
import sys
import time
import logging
from decimal import Decimal
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from boto3.dynamodb.conditions import Attr
from api.config import get_settings, get_boto3_session
from api.services.scorer import compute_satya_score, build_findings, build_recommendations
from api.services.explainer import generate_explanation

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("scoring_worker")

_POLL_INTERVAL = 8   # seconds between DynamoDB scans


# ── Helpers ──────────────────────────────────────────────────────


def _f(value) -> float:
    """Safely convert DynamoDB Decimal to float."""
    if value is None:
        return None
    return float(value)


def _to_decimal(value):
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {k: _to_decimal(v) for k, v in value.items() if v is not None and v != ""}
    if isinstance(value, list):
        return [_to_decimal(v) for v in value]
    return value


# ── Trending table write ──────────────────────────────────────────


def _write_trending(table_trending, item: dict, satya_score: float, verdict: str):
    """Write HIGH_RISK and SUSPICIOUS results to the trending table."""
    if verdict not in ("HIGH_RISK", "SUSPICIOUS"):
        return
    try:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        table_trending.put_item(Item={
            "date": today,
            "analysis_id": item["analysis_id"],
            "content_url": item.get("content_url", ""),
            "platform": item.get("platform", ""),
            "satya_score": _to_decimal(satya_score),
            "verdict": verdict,
            "title": item.get("video_result", {}).get("title", ""),
            "created_at": item.get("created_at", ""),
        })
        logger.info(f"[{item['analysis_id']}] Written to trending table ({verdict})")
    except Exception as e:
        logger.warning(f"Trending write failed (non-fatal): {e}")


# ── Core scoring logic ────────────────────────────────────────────


def score_item(item: dict, table, table_trending):
    analysis_id = item["analysis_id"]
    created_at  = item.get("created_at", "")

    video_score = _f(item.get("video_score"))
    audio_score = _f(item.get("audio_score"))
    text_score  = _f(item.get("text_score"))

    logger.info(
        f"[{analysis_id}] Scoring: video={video_score}, "
        f"audio={audio_score}, text={text_score}"
    )

    # ── Step 1: Fuse scores ──
    satya_score, verdict, confidence, weights = compute_satya_score(
        video_score, audio_score, text_score
    )

    # ── Step 2: Build findings list ──
    findings = build_findings(item)

    # ── Step 3: Recommendations ──
    recommendations = build_recommendations(verdict)

    # ── Step 4: Bedrock explanation ──
    title = item.get("video_result", {}).get("title", item.get("content_url", "Unknown"))
    language = item.get("language", "en")

    explanation = generate_explanation(
        satya_score=satya_score,
        verdict=verdict,
        confidence=confidence,
        video_score=video_score,
        audio_score=audio_score,
        text_score=text_score,
        findings=findings,
        title=title,
        language=language,
    )

    summary = explanation.get("summary", "")
    key_concern = explanation.get("key_concern", "")
    confidence_reason = explanation.get("confidence_reason", "")

    # ── Step 5: Compute processing time ──
    try:
        started = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        processing_ms = int((now - started).total_seconds() * 1000)
    except Exception:
        processing_ms = 0

    # ── Step 6: Write final result to DynamoDB ──
    table.update_item(
        Key={"analysis_id": analysis_id, "created_at": created_at},
        UpdateExpression=(
            "SET satya_score = :ss, verdict = :v, confidence = :c, "
            "summary = :su, findings = :fi, recommendations = :rc, "
            "key_concern = :kc, confidence_reason = :cr, "
            "weights_used = :wu, #st = :status, "
            "processing_time_ms = :pt, completed_at = :ca"
        ),
        ExpressionAttributeNames={"#st": "status"},
        ExpressionAttributeValues={
            ":ss":     _to_decimal(satya_score),
            ":v":      verdict,
            ":c":      confidence,
            ":su":     summary,
            ":fi":     _to_decimal(findings),
            ":rc":     recommendations,
            ":kc":     key_concern,
            ":cr":     confidence_reason,
            ":wu":     _to_decimal(weights),
            ":status": "completed",
            ":pt":     processing_ms,
            ":ca":     datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
    )

    logger.info(
        f"[{analysis_id}] ✅ SATYA score={satya_score}, verdict={verdict}, "
        f"confidence={confidence}, time={processing_ms // 1000}s"
    )

    # ── Step 7: Write to trending table if suspicious or high-risk ──
    _write_trending(table_trending, item, satya_score, verdict)


# ── Poll loop ─────────────────────────────────────────────────────


def main():
    settings = get_settings()
    session  = get_boto3_session()
    db       = session.resource("dynamodb")
    table         = db.Table(settings.analyses_table_name)
    table_trending = db.Table(settings.trending_table_name)

    logger.info("Scoring worker started — polling DynamoDB for unscored analyses")

    while True:
        try:
            # Find records with video_score present but no satya_score yet
            # Audio and text may or may not have completed — adaptive weights handle it
            response = table.scan(
                FilterExpression=(
                    Attr("video_score").exists()
                    & Attr("satya_score").not_exists()
                    & Attr("status").ne("failed")
                ),
                Limit=10,   # process up to 10 at a time
            )

            items = response.get("Items", [])
            if items:
                logger.info(f"Found {len(items)} item(s) ready to score")
                for item in items:
                    try:
                        score_item(item, table, table_trending)
                    except Exception as e:
                        logger.error(
                            f"[{item.get('analysis_id', '?')}] Scoring failed: {e}",
                            exc_info=True,
                        )
            else:
                logger.debug("No items ready to score — waiting")

        except KeyboardInterrupt:
            logger.info("Scoring worker shutting down")
            break
        except Exception as e:
            logger.error(f"Poll error: {e}", exc_info=True)

        time.sleep(_POLL_INTERVAL)


if __name__ == "__main__":
    main()
