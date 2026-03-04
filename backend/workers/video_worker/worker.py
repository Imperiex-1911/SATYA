"""
Video Forensics Worker — SQS poller.

Polls satya-video-jobs queue, downloads frames from S3,
runs all forensic analysis modules, writes video_score to DynamoDB.
"""
import os
import json
import time
import tempfile
import logging
from pathlib import Path
from typing import List
from decimal import Decimal

import boto3
from dotenv import load_dotenv

from workers.video_worker.face_detector import FaceDetector
from workers.video_worker.frame_analyzer import FrameAnalyzer
from workers.video_worker.metadata_checker import check_metadata
from workers.video_worker.scorer import aggregate_video_score

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s [video-worker] %(message)s',
)
logger = logging.getLogger(__name__)

# ── Config ──────────────────────────────────────────────────────────────────
AWS_REGION        = os.getenv("AWS_REGION", "ap-south-1")
AWS_PROFILE       = os.getenv("AWS_PROFILE")
VIDEO_QUEUE_URL   = os.getenv("VIDEO_QUEUE_URL")
MEDIA_BUCKET      = os.getenv("MEDIA_BUCKET_NAME")
ANALYSES_TABLE    = os.getenv("ANALYSES_TABLE_NAME", "satya-analyses")
POLL_WAIT_SECONDS = 20   # SQS long-polling
MAX_MESSAGES      = 1    # process one at a time for memory safety


def _get_session():
    if AWS_PROFILE:
        return boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
    return boto3.Session(region_name=AWS_REGION)


def _float_to_decimal(obj):
    """Recursively convert floats to Decimal for DynamoDB."""
    if isinstance(obj, float):
        return Decimal(str(round(obj, 4)))
    if isinstance(obj, dict):
        return {k: _float_to_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_float_to_decimal(i) for i in obj]
    return obj


def download_frames(s3, analysis_id: str, tmp_dir: str) -> List[str]:
    """Download all frames for an analysis from S3. Returns sorted list of local paths."""
    prefix = f"analyses/{analysis_id}/frames/"
    paginator = s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=MEDIA_BUCKET, Prefix=prefix)

    frame_paths = []
    for page in pages:
        for obj in page.get("Contents", []):
            key = obj["Key"]
            local_path = os.path.join(tmp_dir, os.path.basename(key))
            s3.download_file(MEDIA_BUCKET, key, local_path)
            frame_paths.append(local_path)

    frame_paths.sort()  # ensure chronological order (frame_0001.jpg, frame_0002.jpg, ...)
    logger.info(f"Downloaded {len(frame_paths)} frames for {analysis_id}")
    return frame_paths


def download_video(s3, analysis_id: str, tmp_dir: str) -> str:
    """Download raw video for metadata analysis."""
    key = f"analyses/{analysis_id}/raw/video.mp4"
    local_path = os.path.join(tmp_dir, "video.mp4")
    try:
        s3.download_file(MEDIA_BUCKET, key, local_path)
        return local_path
    except Exception as e:
        logger.warning(f"Could not download video for metadata check: {e}")
        return ""


def process_job(message: dict, s3, dynamodb):
    """Process a single video forensic job."""
    body = json.loads(message["Body"])
    analysis_id = body["analysis_id"]
    created_at  = body.get("created_at", "")

    logger.info(f"Processing video job for analysis_id={analysis_id}")

    # Update DynamoDB status → processing
    table = dynamodb.Table(ANALYSES_TABLE)
    table.update_item(
        Key={"analysis_id": analysis_id, "created_at": created_at},
        UpdateExpression="SET #s = :s",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":s": "processing"},
    )

    with tempfile.TemporaryDirectory() as tmp_dir:
        # ── Download assets ──────────────────────────────────────────────────
        frame_paths = download_frames(s3, analysis_id, tmp_dir)
        video_path  = download_video(s3, analysis_id, tmp_dir)

        if not frame_paths:
            logger.warning(f"No frames found for {analysis_id} — skipping video analysis")
            _write_skipped(table, analysis_id, created_at)
            return

        # ── Face Detection ───────────────────────────────────────────────────
        detector  = FaceDetector(min_detection_confidence=0.4)
        analyzer  = FrameAnalyzer()

        dct_scores      = []
        boundary_scores = []

        for idx, frame_path in enumerate(frame_paths):
            faces = detector.detect_faces(frame_path, idx)
            for face in faces:
                dct_score      = analyzer.analyze_dct(face.face_crop)
                boundary_score = analyzer.analyze_face_boundary(face.face_crop)
                dct_scores.append(dct_score)
                boundary_scores.append(boundary_score)

        detector.close()

        # ── Temporal Consistency ─────────────────────────────────────────────
        temporal_score, _ = analyzer.analyze_temporal_consistency(frame_paths)

        # ── Metadata Forensics ───────────────────────────────────────────────
        metadata_result = check_metadata(video_path) if video_path else {
            "metadata_anomaly_score": 0.2, "flags": ["video_unavailable"]
        }

        # ── Score Aggregation ────────────────────────────────────────────────
        result = aggregate_video_score(
            dct_scores=dct_scores,
            boundary_scores=boundary_scores,
            temporal_score=temporal_score,
            metadata_result=metadata_result,
            frames_analyzed=len(frame_paths),
        )

        logger.info(
            f"Video analysis complete for {analysis_id}: "
            f"score={result.video_score}, faces={result.faces_detected}"
        )

        # ── Write to DynamoDB ────────────────────────────────────────────────
        update_data = {
            "video_score":        Decimal(str(result.video_score)),
            "video_findings":     _float_to_decimal(result.findings),
            "video_faces_found":  result.faces_detected,
            "video_frames_analyzed": result.frames_analyzed,
            "video_deepfake_score":  Decimal(str(result.deepfake_score)),
            "video_temporal_score":  Decimal(str(result.temporal_score)),
            "video_metadata_score":  Decimal(str(result.metadata_score)),
            "video_complete":     True,
        }

        update_expr = "SET " + ", ".join(f"#{k} = :{k}" for k in update_data)
        attr_names  = {f"#{k}": k for k in update_data}
        attr_values = {f":{k}": v for k, v in update_data.items()}

        table.update_item(
            Key={"analysis_id": analysis_id, "created_at": created_at},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=attr_names,
            ExpressionAttributeValues=attr_values,
        )
        logger.info(f"DynamoDB updated for {analysis_id}")


def _write_skipped(table, analysis_id: str, created_at: str):
    table.update_item(
        Key={"analysis_id": analysis_id, "created_at": created_at},
        UpdateExpression="SET video_score = :s, video_complete = :c",
        ExpressionAttributeValues={":s": Decimal("50"), ":c": True},
    )


def run():
    """Main polling loop."""
    if not VIDEO_QUEUE_URL:
        raise RuntimeError("VIDEO_QUEUE_URL not set")

    session   = _get_session()
    sqs       = session.client("sqs")
    s3        = session.client("s3")
    dynamodb  = session.resource("dynamodb")

    logger.info(f"Video worker started. Polling {VIDEO_QUEUE_URL}")

    while True:
        try:
            response = sqs.receive_message(
                QueueUrl=VIDEO_QUEUE_URL,
                MaxNumberOfMessages=MAX_MESSAGES,
                WaitTimeSeconds=POLL_WAIT_SECONDS,
                AttributeNames=["ApproximateReceiveCount"],
            )

            messages = response.get("Messages", [])
            if not messages:
                continue

            for message in messages:
                receipt = message["ReceiptHandle"]
                try:
                    process_job(message, s3, dynamodb)
                    # Delete message only on success
                    sqs.delete_message(
                        QueueUrl=VIDEO_QUEUE_URL,
                        ReceiptHandle=receipt,
                    )
                    logger.info("Message deleted from queue")
                except Exception as e:
                    logger.error(f"Job processing failed: {e}", exc_info=True)
                    # Leave message in queue — DLQ will catch it after 3 attempts

        except KeyboardInterrupt:
            logger.info("Video worker shutting down")
            break
        except Exception as e:
            logger.error(f"Polling error: {e}", exc_info=True)
            time.sleep(5)


if __name__ == "__main__":
    run()
