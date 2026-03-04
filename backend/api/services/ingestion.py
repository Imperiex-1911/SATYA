"""Ingestion pipeline orchestrator — download → extract → upload S3 → dispatch SQS."""

import os
import json
import logging
import tempfile
import shutil
import time
from typing import Optional, Dict, Any
from decimal import Decimal

from langdetect import detect as detect_language_text
from langdetect.lang_detect_exception import LangDetectException

from api.config import get_settings, get_boto3_session
from api.services.youtube import extract_video_id, fetch_metadata, download_video
from api.services.media import extract_audio, extract_frames, get_video_info
from api.services.storage import upload_analysis_media

logger = logging.getLogger(__name__)


# ── Language Detection ──────────────────────────────────────────


def detect_language(metadata: Dict[str, Any]) -> str:
    """Detect content language from YouTube metadata.

    Stage 1: YouTube API metadata fields (defaultAudioLanguage / defaultLanguage)
    Stage 2: Text-based detection on title + description via langdetect
    """
    # Stage 1: YouTube metadata
    lang = (
        metadata.get("default_audio_language")
        or metadata.get("default_language")
    )
    if lang:
        return lang[:2].lower()

    # Stage 2: Text-based detection
    text = f"{metadata.get('title', '')} {metadata.get('description', '')}"
    if len(text.strip()) > 20:
        try:
            detected = detect_language_text(text)
            return detected
        except LangDetectException:
            pass

    return "en"  # Default fallback


# ── SQS Dispatch ────────────────────────────────────────────────


def dispatch_sqs_jobs(
    analysis_id: str,
    created_at: str,
    content_url: str,
    platform: str,
    language: str,
    s3_paths: Dict[str, Any],
    video_info: Dict[str, Any],
    metadata: Dict[str, Any],
):
    """Dispatch 3 SQS messages — one per analysis module (video, audio, text)."""
    settings = get_settings()
    session = get_boto3_session()
    sqs = session.client("sqs")

    base_payload = {
        "analysis_id": analysis_id,
        "created_at": created_at,
        "content_url": content_url,
        "platform": platform,
        "language": language,
        "s3_prefix": s3_paths.get("s3_prefix", ""),
    }

    # Video worker job
    if settings.video_queue_url:
        video_payload = {
            **base_payload,
            "module": "video",
            "s3_video": s3_paths.get("video", ""),
            "s3_frames": s3_paths.get("frames", []),
            "frame_count": len(s3_paths.get("frames", [])),
            "video_info": video_info,
        }
        sqs.send_message(
            QueueUrl=settings.video_queue_url,
            MessageBody=json.dumps(video_payload, default=str),
            MessageAttributes={
                "module": {"StringValue": "video", "DataType": "String"},
                "analysis_id": {"StringValue": analysis_id, "DataType": "String"},
            },
        )
        logger.info(f"[{analysis_id}] Dispatched video job")

    # Audio worker job
    if settings.audio_queue_url and s3_paths.get("audio"):
        audio_payload = {
            **base_payload,
            "module": "audio",
            "s3_audio": s3_paths.get("audio", ""),
            "has_audio": video_info.get("has_audio", False),
        }
        sqs.send_message(
            QueueUrl=settings.audio_queue_url,
            MessageBody=json.dumps(audio_payload, default=str),
            MessageAttributes={
                "module": {"StringValue": "audio", "DataType": "String"},
                "analysis_id": {"StringValue": analysis_id, "DataType": "String"},
            },
        )
        logger.info(f"[{analysis_id}] Dispatched audio job")

    # Text analysis job
    if settings.text_queue_url:
        text_payload = {
            **base_payload,
            "module": "text",
            "title": metadata.get("title", ""),
            "description": metadata.get("description", ""),
            "tags": metadata.get("tags", []),
            "comment_count": metadata.get("comment_count", 0),
            "view_count": metadata.get("view_count", 0),
            "like_count": metadata.get("like_count", 0),
        }
        sqs.send_message(
            QueueUrl=settings.text_queue_url,
            MessageBody=json.dumps(text_payload, default=str),
            MessageAttributes={
                "module": {"StringValue": "text", "DataType": "String"},
                "analysis_id": {"StringValue": analysis_id, "DataType": "String"},
            },
        )
        logger.info(f"[{analysis_id}] Dispatched text job")


# ── DynamoDB Helpers ────────────────────────────────────────────


def _sanitize_for_dynamodb(value):
    """Convert floats to Decimal and remove empty strings for DynamoDB."""
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {k: _sanitize_for_dynamodb(v) for k, v in value.items() if v != ""}
    if isinstance(value, list):
        return [_sanitize_for_dynamodb(v) for v in value]
    if value == "":
        return None
    return value


def update_dynamodb_status(
    analysis_id: str,
    created_at: str,
    status: str,
    extra_attrs: Dict[str, Any] = None,
):
    """Update analysis record in DynamoDB."""
    settings = get_settings()
    session = get_boto3_session()
    db = session.resource("dynamodb")
    table = db.Table(settings.analyses_table_name)

    update_expr = "SET #st = :st"
    expr_names = {"#st": "status"}
    expr_values = {":st": status}

    if extra_attrs:
        for key, value in extra_attrs.items():
            if value is None:
                continue
            sanitized = _sanitize_for_dynamodb(value)
            if sanitized is None:
                continue
            placeholder = key.replace("-", "_")
            update_expr += f", #{placeholder} = :{placeholder}"
            expr_names[f"#{placeholder}"] = key
            expr_values[f":{placeholder}"] = sanitized

    table.update_item(
        Key={"analysis_id": analysis_id, "created_at": created_at},
        UpdateExpression=update_expr,
        ExpressionAttributeNames=expr_names,
        ExpressionAttributeValues=expr_values,
    )


# ── Main Ingestion Pipeline ────────────────────────────────────


async def run_ingestion(
    analysis_id: str,
    content_url: str,
    platform: str,
    created_at: str,
    language_override: Optional[str] = None,
):
    """Full ingestion pipeline: download → extract → upload S3 → dispatch SQS.

    Runs as a FastAPI BackgroundTask after the API returns 202.
    """
    work_dir = tempfile.mkdtemp(prefix=f"satya-{analysis_id[:8]}-")
    start_time = time.time()

    try:
        logger.info(f"[{analysis_id}] Starting ingestion for {content_url}")

        # ── Step 1: Extract video ID and fetch metadata ──
        video_id = extract_video_id(content_url)
        if not video_id:
            raise ValueError(f"Could not extract video ID from: {content_url}")

        metadata = await fetch_metadata(video_id)
        logger.info(f"[{analysis_id}] Metadata: \"{metadata['title'][:60]}\"")

        # ── Step 2: Detect language ──
        language = language_override if language_override and language_override != "auto" else detect_language(metadata)
        logger.info(f"[{analysis_id}] Language: {language}")

        # ── Step 3: Download video ──
        video_path = download_video(content_url, work_dir)
        file_size = os.path.getsize(video_path)
        logger.info(f"[{analysis_id}] Downloaded: {file_size:,} bytes")

        # ── Step 4: Get video info via ffprobe ──
        video_info = get_video_info(video_path)
        logger.info(
            f"[{analysis_id}] Video: {video_info.get('duration_seconds', 0):.1f}s, "
            f"{video_info.get('video_width', 0)}x{video_info.get('video_height', 0)}, "
            f"audio={video_info.get('has_audio', False)}"
        )

        # ── Step 5: Extract audio ──
        audio_path = None
        if video_info.get("has_audio", True):
            try:
                audio_path = extract_audio(video_path, work_dir)
            except RuntimeError as e:
                logger.warning(f"[{analysis_id}] Audio extraction failed: {e}")

        # ── Step 6: Extract frames — 1fps, max 30 frames ──
        frame_paths = extract_frames(video_path, work_dir, fps=1, max_frames=30)
        logger.info(f"[{analysis_id}] Extracted {len(frame_paths)} frames")

        # ── Step 7: Upload all to S3 ──
        s3_paths = upload_analysis_media(
            analysis_id=analysis_id,
            video_path=video_path,
            audio_path=audio_path,
            frame_paths=frame_paths,
            metadata=metadata,
        )
        logger.info(f"[{analysis_id}] S3 upload complete")

        # ── Step 8: Dispatch SQS jobs ──
        dispatch_sqs_jobs(
            analysis_id=analysis_id,
            created_at=created_at,
            content_url=content_url,
            platform=platform,
            language=language,
            s3_paths=s3_paths,
            video_info=video_info,
            metadata=metadata,
        )

        # ── Step 9: Update DynamoDB to processing ──
        elapsed_ms = int((time.time() - start_time) * 1000)
        update_dynamodb_status(
            analysis_id=analysis_id,
            created_at=created_at,
            status="processing",
            extra_attrs={
                "language": language,
                "video_title": metadata.get("title", "Unknown"),
                "s3_prefix": s3_paths.get("s3_prefix", ""),
                "frame_count": len(frame_paths),
                "duration_seconds": video_info.get("duration_seconds", 0),
                "has_audio": video_info.get("has_audio", False),
                "ingestion_time_ms": elapsed_ms,
            },
        )

        logger.info(
            f"[{analysis_id}] ✅ Ingestion complete in {elapsed_ms}ms — "
            f"{len(frame_paths)} frames, audio={'yes' if audio_path else 'no'}, "
            f"3 SQS jobs dispatched"
        )

    except Exception as e:
        logger.error(f"[{analysis_id}] ❌ Ingestion failed: {e}", exc_info=True)
        try:
            update_dynamodb_status(
                analysis_id=analysis_id,
                created_at=created_at,
                status="failed",
                extra_attrs={"error_message": str(e)[:500]},
            )
        except Exception:
            logger.error(f"[{analysis_id}] Failed to update error status in DynamoDB")

    finally:
        # Clean up temp directory
        try:
            shutil.rmtree(work_dir, ignore_errors=True)
            logger.debug(f"[{analysis_id}] Cleaned up {work_dir}")
        except Exception:
            pass
