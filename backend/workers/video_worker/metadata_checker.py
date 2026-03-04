"""
Metadata forensics using ffprobe.
AI-generated videos lack authentic camera metadata and show
specific encoder fingerprints from generation tools.
"""
import subprocess
import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Encoders commonly used by AI video generation tools
AI_ENCODER_FINGERPRINTS = [
    "lavf", "libx264", "libopenh264",  # default ffmpeg — used by Runway, Sora exports
    "h264_nvenc",  # Nvidia GPU encoder — common in AI pipelines
]

# Real camera devices leave these maker notes
CAMERA_METADATA_KEYS = [
    "com.android.capture.fps",
    "com.apple.quicktime.camera",
    "encoder",
    "creation_time",
]


def check_metadata(video_path: str) -> Dict[str, Any]:
    """
    Run ffprobe on the video file and extract forensic signals.
    Returns a dict with anomaly flags and a metadata_anomaly_score.
    """
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_format", "-show_streams",
                video_path,
            ],
            capture_output=True, text=True, timeout=30,
        )
        data = json.loads(result.stdout)
    except Exception as e:
        logger.warning(f"ffprobe failed for {video_path}: {e}")
        return {"metadata_anomaly_score": 0.3, "flags": ["ffprobe_failed"]}

    flags = []
    anomaly_signals = 0
    total_signals = 4

    fmt = data.get("format", {})
    tags = fmt.get("tags", {})

    # Signal 1: Missing creation time (cameras always write this)
    if "creation_time" not in tags:
        flags.append("no_creation_time")
        anomaly_signals += 1

    # Signal 2: AI encoder fingerprint
    encoder = tags.get("encoder", "") or ""
    for fp in AI_ENCODER_FINGERPRINTS:
        if fp.lower() in encoder.lower():
            flags.append(f"ai_encoder_fingerprint:{fp}")
            anomaly_signals += 0.5  # partial signal
            break

    # Signal 3: No video stream rotation/orientation metadata (cameras set this)
    streams = data.get("streams", [])
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    if video_stream:
        side_data = video_stream.get("side_data_list", [])
        has_rotation = any(s.get("side_data_type") == "Display Matrix" for s in side_data)
        if not has_rotation:
            flags.append("no_rotation_metadata")
            anomaly_signals += 0.5

    # Signal 4: Duration mismatch (some AI tools produce imprecise durations)
    try:
        fmt_duration = float(fmt.get("duration", 0))
        if video_stream:
            stream_duration = float(video_stream.get("duration", fmt_duration))
            if abs(fmt_duration - stream_duration) > 1.0:
                flags.append("duration_mismatch")
                anomaly_signals += 1
    except (ValueError, TypeError):
        pass

    score = min(1.0, anomaly_signals / total_signals)

    return {
        "metadata_anomaly_score": round(score, 3),
        "flags": flags,
        "encoder": encoder or "unknown",
        "format": fmt.get("format_name", "unknown"),
    }
