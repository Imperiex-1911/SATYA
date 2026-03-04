from pydantic import BaseModel, HttpUrl
from typing import Optional, List, Any
from enum import Enum


class AnalysisStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Verdict(str, Enum):
    HIGH_RISK = "HIGH_RISK"
    SUSPICIOUS = "SUSPICIOUS"
    UNCERTAIN = "UNCERTAIN"
    AUTHENTIC = "AUTHENTIC"


class Confidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# ── Request Models ──────────────────────────────────────────
class AnalyzeRequest(BaseModel):
    url: str
    language: Optional[str] = None  # optional language override


# ── Response Models ─────────────────────────────────────────
class AnalyzeSubmittedResponse(BaseModel):
    analysis_id: str
    status: AnalysisStatus
    message: str


class Finding(BaseModel):
    module: str
    signal: str
    severity: str
    detail: str
    evidence_timestamp: Optional[str] = None
    evidence_frames: Optional[List[str]] = None


class AnalysisResult(BaseModel):
    analysis_id: str
    status: AnalysisStatus
    content_url: Optional[str] = None
    platform: Optional[str] = None
    language: Optional[str] = None
    satya_score: Optional[float] = None
    video_score: Optional[float] = None
    audio_score: Optional[float] = None
    text_score: Optional[float] = None
    verdict: Optional[Verdict] = None
    confidence: Optional[Confidence] = None
    summary: Optional[str] = None
    findings: Optional[List[Finding]] = None
    recommendations: Optional[List[str]] = None
    processing_time_ms: Optional[int] = None
    error_message: Optional[str] = None
    created_at: Optional[str] = None


class ErrorResponse(BaseModel):
    error: dict


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    region: str
