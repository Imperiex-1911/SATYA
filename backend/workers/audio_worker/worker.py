"""Audio worker — polls satya-audio-jobs SQS queue.

Pipeline:
    1. Download audio WAV from S3
    2. Run Amazon Transcribe (speech-to-text)
    3. Analyze prosody anomalies (librosa)
    4. Detect voice cloning (spectral features)
    5. Compute audio score
    6. Write results to DynamoDB

Run on host machine:
    cd C:\\AIB\\backend
    python -m workers.audio_worker.worker
"""

import os
import sys
import json
import time
import logging
import tempfile
import shutil
from decimal import Decimal

import boto3

# Ensure backend/ is on path when run directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from api.config import get_settings, get_boto3_session
from workers.audio_worker.transcribe import run_transcription
from workers.audio_worker.prosody_analyzer import analyze_prosody
from workers.audio_worker.voice_clone_detector import detect_voice_clone
from workers.audio_worker.scorer import compute_audio_score

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("audio_worker")


# ── DynamoDB Helpers ─────────────────────────────────────────────


def _to_decimal(value):
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {k: _to_decimal(v) for k, v in value.items() if v != "" and v is not None}
    if isinstance(value, list):
        return [_to_decimal(v) for v in value]
    return value


def update_dynamodb(analysis_id: str, created_at: str, status: str, audio_data: dict):
    settings = get_settings()
    session = get_boto3_session()
    db = session.resource("dynamodb")
    table = db.Table(settings.analyses_table_name)

    audio_score = audio_data.get("audio_score", 50.0)

    table.update_item(
        Key={"analysis_id": analysis_id, "created_at": created_at},
        UpdateExpression=(
            "SET #st = :st, audio_score = :as_val, "
            "audio_result = :ar, audio_completed_at = :aca"
        ),
        ExpressionAttributeNames={"#st": "status"},
        ExpressionAttributeValues={
            ":st": status,
            ":as_val": _to_decimal(audio_score),
            ":ar": _to_decimal(audio_data),
            ":aca": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
    )
    logger.info(f"[{analysis_id}] DynamoDB updated: audio_score={audio_score}")


# ── Job Processor ────────────────────────────────────────────────


def process_job(message: dict):
    body = json.loads(message["Body"])
    analysis_id = body.get("analysis_id", "unknown")
    created_at = body.get("created_at", "")
    s3_audio = body.get("s3_audio", "")
    language = body.get("language", "en")

    if not s3_audio:
        logger.warning(f"[{analysis_id}] No s3_audio in message — skipping")
        return

    logger.info(f"[{analysis_id}] Processing audio job | lang={language}")
    settings = get_settings()
    session = get_boto3_session()
    s3 = session.client("s3")

    work_dir = tempfile.mkdtemp(prefix=f"satya-audio-{analysis_id[:8]}-")

    try:
        # ── Step 1: Download audio from S3 ──
        local_audio = os.path.join(work_dir, "audio.wav")
        # Parse s3://bucket/key
        s3_parts = s3_audio.replace("s3://", "").split("/", 1)
        bucket, key = s3_parts[0], s3_parts[1]
        s3.download_file(bucket, key, local_audio)
        logger.info(f"[{analysis_id}] Downloaded audio: {os.path.getsize(local_audio):,} bytes")

        # ── Step 2: Whisper transcription (local, CPU) ──
        transcribe_result = {"transcript": "", "confidence": 0.0, "word_count": 0, "speaker_count": 1}
        try:
            transcribe_result = run_transcription(
                analysis_id=analysis_id,
                local_audio_path=local_audio,
                language=language,
            )
        except Exception as e:
            logger.warning(f"[{analysis_id}] Transcription failed (non-fatal): {e}")

        # ── Step 3: Prosody analysis ──
        prosody_result = analyze_prosody(local_audio)

        # ── Step 4: Voice clone detection ──
        voice_clone_result = detect_voice_clone(local_audio)

        # ── Step 5: Score ──
        audio_data = compute_audio_score(voice_clone_result, prosody_result, transcribe_result)
        audio_data["transcript"] = transcribe_result.get("transcript", "")[:1000]  # cap at 1KB

        # ── Step 6: DynamoDB ──
        update_dynamodb(analysis_id, created_at, "processing", audio_data)

        logger.info(f"[{analysis_id}] ✅ Audio complete: score={audio_data['audio_score']}")

    except Exception as e:
        logger.error(f"[{analysis_id}] ❌ Audio job failed: {e}", exc_info=True)
        try:
            settings2 = get_settings()
            session2 = get_boto3_session()
            db = session2.resource("dynamodb")
            table = db.Table(settings2.analyses_table_name)
            table.update_item(
                Key={"analysis_id": analysis_id, "created_at": created_at},
                UpdateExpression="SET audio_error = :e",
                ExpressionAttributeValues={":e": str(e)[:500]},
            )
        except Exception:
            pass
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


# ── SQS Poll Loop ────────────────────────────────────────────────


def main():
    settings = get_settings()
    session = get_boto3_session()
    sqs = session.client("sqs")

    queue_url = settings.audio_queue_url
    if not queue_url:
        logger.error("AUDIO_QUEUE_URL not set")
        sys.exit(1)

    logger.info(f"Audio worker started — polling {queue_url}")

    while True:
        try:
            response = sqs.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=20,
                VisibilityTimeout=300,   # 5 min — Whisper runs locally, much faster than Transcribe
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
            logger.info("Audio worker shutting down")
            break
        except Exception as e:
            logger.error(f"SQS poll error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
