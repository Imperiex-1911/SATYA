from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path
import boto3

# Resolve .env from project root (C:\AIB\.env) regardless of working directory
_ENV_FILE = Path(__file__).parent.parent.parent / ".env"


class Settings(BaseSettings):
    # App
    app_name: str = "SATYA API"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = True

    # AWS
    aws_region: str = "ap-south-1"
    aws_profile: str = ""  # Empty = use env vars / instance role

    # S3
    media_bucket_name: str = ""

    # DynamoDB
    analyses_table_name: str = "satya-analyses"
    trending_table_name: str = "satya-trending"

    # SQS
    video_queue_url: str = ""
    audio_queue_url: str = ""
    text_queue_url: str = ""

    # YouTube
    youtube_api_key: str = ""

    # Bedrock
    bedrock_model_id: str = "amazon.nova-micro-v1:0"

    class Config:
        env_file = str(_ENV_FILE)
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


def get_boto3_session() -> boto3.Session:
    """Create a boto3 session using profile if available, else default credentials."""
    settings = get_settings()
    kwargs = {"region_name": settings.aws_region}
    if settings.aws_profile:
        kwargs["profile_name"] = settings.aws_profile
    return boto3.Session(**kwargs)
