"""YouTube connector — metadata fetch via Data API v3 + video download via yt-dlp."""

import glob
import os
import re
import logging
from typing import Optional, Dict, Any

import httpx
import yt_dlp

from api.config import get_settings

logger = logging.getLogger(__name__)


def extract_video_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from various URL formats."""
    patterns = [
        r"(?:v=|/videos/|embed/|youtu\.be/|/v/|/e/|watch\?v=|&v=)([^#&?\n]{11})",
        r"(?:youtube\.com/shorts/)([^#&?\n]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


async def fetch_metadata(video_id: str) -> Dict[str, Any]:
    """Fetch video metadata from YouTube Data API v3."""
    settings = get_settings()

    if not settings.youtube_api_key:
        raise ValueError("YOUTUBE_API_KEY is not configured")

    api_url = (
        f"https://www.googleapis.com/youtube/v3/videos"
        f"?part=snippet,contentDetails,statistics"
        f"&id={video_id}"
        f"&key={settings.youtube_api_key}"
    )

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(api_url)
        response.raise_for_status()
        data = response.json()

    if not data.get("items"):
        raise ValueError(f"Video not found: {video_id}")

    item = data["items"][0]
    snippet = item["snippet"]
    content_details = item["contentDetails"]
    statistics = item.get("statistics", {})

    return {
        "video_id": video_id,
        "title": snippet.get("title", ""),
        "description": snippet.get("description", ""),
        "channel_title": snippet.get("channelTitle", ""),
        "channel_id": snippet.get("channelId", ""),
        "published_at": snippet.get("publishedAt", ""),
        "default_language": snippet.get("defaultLanguage", ""),
        "default_audio_language": snippet.get("defaultAudioLanguage", ""),
        "tags": snippet.get("tags", []),
        "category_id": snippet.get("categoryId", ""),
        "duration": content_details.get("duration", ""),
        "definition": content_details.get("definition", ""),
        "view_count": int(statistics.get("viewCount", 0)),
        "like_count": int(statistics.get("likeCount", 0)),
        "comment_count": int(statistics.get("commentCount", 0)),
        "thumbnail_url": (
            snippet.get("thumbnails", {}).get("high", {}).get("url", "")
        ),
    }


def download_video(url: str, output_dir: str, max_duration: int = 600) -> str:
    """Download video using yt-dlp. Returns path to downloaded file.

    Args:
        url: YouTube video URL
        output_dir: Directory to save the file
        max_duration: Maximum duration in seconds (default 10 minutes)
    """
    output_template = os.path.join(output_dir, "video.%(ext)s")

    class _YDLLogger:
        def debug(self, msg):
            if msg.startswith("[debug]"):
                return  # skip verbose debug lines
            logger.debug(f"yt-dlp: {msg}")
        def info(self, msg):   logger.info(f"yt-dlp: {msg}")
        def warning(self, msg): logger.warning(f"yt-dlp: {msg}")
        def error(self, msg):  logger.error(f"yt-dlp: {msg}")

    ydl_opts = {
        "format": "best[height<=720][ext=mp4]/best[ext=mp4]/best[height<=720]/best",
        "outtmpl": output_template,
        "logger": _YDLLogger(),
        "socket_timeout": 60,
        "retries": 3,
        "fragment_retries": 3,
        "merge_output_format": "mp4",
    }

    # Use cookies file if present — required on cloud IPs blocked by YouTube bot detection
    # youtube.py is at backend/api/services/ — 4x dirname reaches project root
    _cookies_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "cookies.txt"
    )
    if os.path.exists(_cookies_path):
        ydl_opts["cookiefile"] = _cookies_path
        logger.info("Using cookies.txt for yt-dlp authentication")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            ydl.download([url])
        except yt_dlp.utils.DownloadError as e:
            msg = str(e)
            if "images are available" in msg or "Requested format is not available" in msg:
                raise ValueError(
                    "No downloadable video stream found. This video may be audio-only, "
                    "a podcast, or a YouTube Short with restricted formats."
                ) from e
            raise

    # Find the downloaded file — yt-dlp may choose a different extension
    for ext in ["mp4", "webm", "mkv", "avi", "m4v", "mov"]:
        candidate = os.path.join(output_dir, f"video.{ext}")
        if os.path.exists(candidate) and os.path.getsize(candidate) > 0:
            logger.info(
                f"Downloaded video: {candidate} ({os.path.getsize(candidate)} bytes)"
            )
            return candidate

    # Fallback: find any non-partial video file yt-dlp wrote to the directory
    all_files = sorted(glob.glob(os.path.join(output_dir, "video.*")))
    logger.info(f"Extension search missed; files in {output_dir}: {all_files}")
    for f in all_files:
        if not f.endswith((".part", ".ytdl", ".json")) and os.path.getsize(f) > 0:
            logger.info(f"Downloaded video (glob fallback): {f} ({os.path.getsize(f)} bytes)")
            return f

    raise FileNotFoundError(f"Download failed — no video file found in {output_dir}")
