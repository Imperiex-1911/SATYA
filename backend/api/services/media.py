"""Media extraction — FFmpeg audio and frame extraction + ffprobe metadata."""

import os
import subprocess
import json
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def _parse_frame_rate(rate_str: str) -> float:
    """Parse ffprobe frame rate string like '30/1' or '29.97'."""
    try:
        if "/" in str(rate_str):
            parts = str(rate_str).split("/")
            num, den = float(parts[0]), float(parts[1])
            return round(num / den, 2) if den != 0 else 0.0
        return round(float(rate_str), 2)
    except (ValueError, ZeroDivisionError, IndexError):
        return 0.0


def extract_audio(video_path: str, output_dir: str) -> str:
    """Extract audio from video as WAV 16kHz mono.

    Returns path to the extracted audio file.
    """
    audio_path = os.path.join(output_dir, "audio.wav")

    cmd = [
        "ffmpeg",
        "-i", video_path,
        "-vn",                      # no video
        "-acodec", "pcm_s16le",     # WAV PCM 16-bit
        "-ar", "16000",             # 16kHz sample rate
        "-ac", "1",                 # mono
        "-y",                       # overwrite
        audio_path,
    ]

    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=120
    )

    if result.returncode != 0:
        logger.warning(f"FFmpeg audio stderr: {result.stderr[:500]}")

    if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
        raise RuntimeError(f"Audio extraction failed: {result.stderr[:200]}")

    logger.info(
        f"Extracted audio: {audio_path} ({os.path.getsize(audio_path)} bytes)"
    )
    return audio_path


def extract_frames(
    video_path: str, output_dir: str, fps: int = 1, max_frames: int = 30
) -> List[str]:
    """Extract video frames at specified FPS as JPEGs, capped at max_frames.

    Samples evenly across the full video duration so forensic coverage
    is maintained regardless of video length.
    Returns list of paths to extracted frame files.
    """
    frames_dir = os.path.join(output_dir, "frames")
    os.makedirs(frames_dir, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-i", video_path,
        "-vf", f"fps={fps}",
        "-q:v", "2",               # JPEG quality (2=high)
        "-y",
        os.path.join(frames_dir, "frame_%04d.jpg"),
    ]

    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=180
    )

    if result.returncode != 0:
        logger.warning(f"FFmpeg frame extraction stderr: {result.stderr[:500]}")

    frame_files = sorted([
        os.path.join(frames_dir, f)
        for f in os.listdir(frames_dir)
        if f.endswith(".jpg")
    ])

    if not frame_files:
        raise RuntimeError("Frame extraction produced no frames")

    # Evenly sample down to max_frames — preserves temporal spread
    if len(frame_files) > max_frames:
        step = len(frame_files) / max_frames
        frame_files = [frame_files[int(i * step)] for i in range(max_frames)]
        logger.info(f"Sampled {max_frames} frames from {len(frame_files)} total")

    logger.info(f"Extracted {len(frame_files)} frames at {fps}fps")
    return frame_files


def get_video_info(video_path: str) -> Dict[str, Any]:
    """Get video metadata using ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        video_path,
    ]

    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=30
    )

    if result.returncode != 0:
        logger.warning(f"ffprobe failed: {result.stderr[:200]}")
        return {"has_audio": True, "duration_seconds": 0}

    try:
        probe_data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"has_audio": True, "duration_seconds": 0}

    format_info = probe_data.get("format", {})
    streams = probe_data.get("streams", [])

    video_stream = next(
        (s for s in streams if s.get("codec_type") == "video"), {}
    )
    audio_stream = next(
        (s for s in streams if s.get("codec_type") == "audio"), {}
    )

    return {
        "duration_seconds": float(format_info.get("duration", 0)),
        "file_size_bytes": int(format_info.get("size", 0)),
        "format_name": format_info.get("format_name", ""),
        "video_codec": video_stream.get("codec_name", ""),
        "video_width": int(video_stream.get("width", 0)),
        "video_height": int(video_stream.get("height", 0)),
        "video_fps": _parse_frame_rate(
            video_stream.get("r_frame_rate", "0")
        ),
        "has_audio": bool(audio_stream),
        "audio_codec": audio_stream.get("codec_name", ""),
        "audio_sample_rate": int(audio_stream.get("sample_rate", 0)),
    }
