"""Text worker — polls satya-text-jobs SQS queue.

Pipeline:
    1. Parse title + description + tags + engagement counts from SQS message
    2. Run LLM text detector (statistical burstiness analysis)
    3. Run bot/coordinated behavior detector
    4. Compute text score
    5. Write results to DynamoDB

Run on host machine:
    cd C:\\AIB\\backend
    python -m workers.text_worker.worker
"""

import os
import sys
import json
import time
import logging
from decimal import Decimal

# Ensure backend/ is on path when run directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from api.config import get_settings, get_boto3_session
from workers.text_worker.llm_detector import detect_llm_text
from workers.text_worker.bot_detector import detect_bot_signals
from workers.text_worker.scorer import compute_text_score

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("text_worker")


# ── DynamoDB Helper ──────────────────────────────────────────────


def _to_decimal(value):
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {k: _to_decimal(v) for k, v in value.items() if v != "" and v is not None}
    if isinstance(value, list):
        return [_to_decimal(v) for v in value]
    return value


def update_dynamodb(analysis_id: str, created_at: str, text_data: dict):
    settings = get_settings()
    session = get_boto3_session()
    db = session.resource("dynamodb")
    table = db.Table(settings.analyses_table_name)

    text_score = text_data.get("text_score", 50.0)

    table.update_item(
        Key={"analysis_id": analysis_id, "created_at": created_at},
        UpdateExpression=(
            "SET text_score = :ts, text_result = :tr, "
            "text_completed_at = :tca"
        ),
        ExpressionAttributeValues={
            ":ts": _to_decimal(text_score),
            ":tr": _to_decimal(text_data),
            ":tca": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
    )
    logger.info(f"[{analysis_id}] DynamoDB updated: text_score={text_score}")


# ── Job Processor ────────────────────────────────────────────────


def process_job(message: dict):
    body = json.loads(message["Body"])
    analysis_id = body.get("analysis_id", "unknown")
    created_at = body.get("created_at", "")

    title = body.get("title", "")
    description = body.get("description", "")
    tags = body.get("tags", [])
    comment_count = int(body.get("comment_count", 0))

    # Engagement data — may not always be present (depends on YouTube API response)
    view_count = int(body.get("view_count", 0))
    like_count = int(body.get("like_count", 0))

    logger.info(f"[{analysis_id}] Processing text job | title='{title[:50]}'")

    try:
        # ── Step 1: LLM text detection ──
        llm_result = detect_llm_text(title, description)

        # ── Step 2: Bot/engagement signal detection ──
        bot_result = detect_bot_signals(
            title=title,
            description=description,
            tags=tags,
            view_count=view_count,
            like_count=like_count,
            comment_count=comment_count,
        )

        # ── Step 3: Score ──
        text_data = compute_text_score(llm_result, bot_result)

        # ── Step 4: DynamoDB ──
        update_dynamodb(analysis_id, created_at, text_data)

        logger.info(f"[{analysis_id}] ✅ Text complete: score={text_data['text_score']}")

    except Exception as e:
        logger.error(f"[{analysis_id}] ❌ Text job failed: {e}", exc_info=True)
        try:
            settings = get_settings()
            session = get_boto3_session()
            db = session.resource("dynamodb")
            table = db.Table(settings.analyses_table_name)
            table.update_item(
                Key={"analysis_id": analysis_id, "created_at": created_at},
                UpdateExpression="SET text_error = :e",
                ExpressionAttributeValues={":e": str(e)[:500]},
            )
        except Exception:
            pass


# ── SQS Poll Loop ────────────────────────────────────────────────


def main():
    settings = get_settings()
    session = get_boto3_session()
    sqs = session.client("sqs")

    queue_url = settings.text_queue_url
    if not queue_url:
        logger.error("TEXT_QUEUE_URL not set")
        sys.exit(1)

    logger.info(f"Text worker started — polling {queue_url}")

    while True:
        try:
            response = sqs.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=20,
                VisibilityTimeout=120,   # 2 min is plenty for text analysis
                MessageAttributeNames=["All"],
            )
            messages = response.get("Messages", [])
            if not messages:
                continue

            message = messages[0]
            receipt_handle = message["ReceiptHandle"]

            try:
                process_job(message)
                sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
            except Exception as e:
                logger.error(f"Job failed, message returned to queue: {e}")

        except KeyboardInterrupt:
            logger.info("Text worker shutting down")
            break
        except Exception as e:
            logger.error(f"SQS poll error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
