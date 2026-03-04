"""S3 storage operations for media files."""

import os
import json
import logging
from typing import List, Dict, Any

import botocore.config
from boto3.s3.transfer import TransferConfig
from api.config import get_settings, get_boto3_session

logger = logging.getLogger(__name__)

# Longer timeouts + retries for unreliable network conditions
_BOTO_CONFIG = botocore.config.Config(
    connect_timeout=60,
    read_timeout=300,
    retries={"max_attempts": 3, "mode": "adaptive"},
)

# Use single-part uploads for files < 50 MB to avoid multipart drop issues;
# sequential (max_concurrency=1) avoids connection pool exhaustion in containers
_TRANSFER_CONFIG = TransferConfig(
    multipart_threshold=50 * 1024 * 1024,   # 50 MB
    max_concurrency=1,
    multipart_chunksize=10 * 1024 * 1024,   # 10 MB chunks
    use_threads=False,
)


def get_s3_client():
    session = get_boto3_session()
    return session.client("s3", config=_BOTO_CONFIG)


def upload_file(local_path: str, s3_key: str, content_type: str = None) -> str:
    """Upload a single file to S3. Returns S3 URI."""
    settings = get_settings()
    s3 = get_s3_client()

    extra_args = {}
    if content_type:
        extra_args["ContentType"] = content_type

    s3.upload_file(
        local_path,
        settings.media_bucket_name,
        s3_key,
        ExtraArgs=extra_args if extra_args else None,
        Config=_TRANSFER_CONFIG,
    )

    s3_uri = f"s3://{settings.media_bucket_name}/{s3_key}"
    logger.info(f"Uploaded {os.path.basename(local_path)} → {s3_key}")
    return s3_uri


def upload_analysis_media(
    analysis_id: str,
    video_path: str,
    audio_path: str,
    frame_paths: List[str],
    metadata: Dict[str, Any],
) -> Dict[str, Any]:
    """Upload all media files for an analysis to S3.

    S3 structure:
        analyses/{analysis_id}/raw/video.mp4
        analyses/{analysis_id}/audio/audio.wav
        analyses/{analysis_id}/frames/frame_0001.jpg
        analyses/{analysis_id}/metadata.json

    Returns dict of S3 URIs.
    """
    prefix = f"analyses/{analysis_id}"
    s3_paths = {}

    # Upload video
    s3_paths["video"] = upload_file(
        video_path,
        f"{prefix}/raw/{os.path.basename(video_path)}",
        content_type="video/mp4",
    )

    # Upload audio
    if audio_path and os.path.exists(audio_path):
        s3_paths["audio"] = upload_file(
            audio_path,
            f"{prefix}/audio/audio.wav",
            content_type="audio/wav",
        )

    # Upload frames
    frame_uris = []
    for frame_path in frame_paths:
        frame_uri = upload_file(
            frame_path,
            f"{prefix}/frames/{os.path.basename(frame_path)}",
            content_type="image/jpeg",
        )
        frame_uris.append(frame_uri)
    s3_paths["frames"] = frame_uris

    # Upload metadata as JSON
    settings = get_settings()
    s3 = get_s3_client()
    metadata_key = f"{prefix}/metadata.json"
    s3.put_object(
        Bucket=settings.media_bucket_name,
        Key=metadata_key,
        Body=json.dumps(metadata, indent=2, default=str),
        ContentType="application/json",
    )
    s3_paths["metadata"] = f"s3://{settings.media_bucket_name}/{metadata_key}"
    s3_paths["s3_prefix"] = prefix

    logger.info(
        f"Uploaded all media for {analysis_id}: "
        f"video + audio + {len(frame_uris)} frames + metadata"
    )
    return s3_paths
