from fastapi import APIRouter, HTTPException, BackgroundTasks
from api.schemas import (
    AnalyzeRequest,
    AnalyzeSubmittedResponse,
    AnalysisResult,
    AnalysisStatus,
    Verdict,
)
from api.config import get_settings, get_boto3_session
from api.services.youtube import extract_video_id
from api.services.ingestion import run_ingestion
from boto3.dynamodb.conditions import Key
from decimal import Decimal
import uuid
import time
from datetime import datetime, timezone


def _to_float(v):
    """Convert DynamoDB Decimal to float, pass through None."""
    if v is None:
        return None
    return float(v) if isinstance(v, Decimal) else v

router = APIRouter(prefix="/api/v1", tags=["analysis"])


def get_dynamodb():
    session = get_boto3_session()
    return session.resource("dynamodb")


def detect_platform(url: str) -> str:
    url_lower = url.lower()
    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        return "youtube"
    if "instagram.com" in url_lower:
        return "instagram"
    if "sharechat" in url_lower:
        return "sharechat"
    if "x.com" in url_lower or "twitter.com" in url_lower:
        return "x"
    return "unknown"


@router.post("/analyze", response_model=AnalyzeSubmittedResponse, status_code=202)
async def submit_analysis(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    settings = get_settings()
    url = request.url.strip()

    # Validate URL has a supported platform
    platform = detect_platform(url)
    if platform == "unknown":
        raise HTTPException(
            status_code=400,
            detail={
                "code": "UNSUPPORTED_PLATFORM",
                "message": "URL is not from a supported platform",
                "supported_platforms": ["youtube.com", "instagram.com", "sharechat.in", "x.com"],
            },
        )

    # Prototype scope: YouTube only
    if platform != "youtube":
        raise HTTPException(
            status_code=400,
            detail={
                "code": "PLATFORM_NOT_YET_SUPPORTED",
                "message": f"Platform '{platform}' is on the roadmap. Currently supporting YouTube only in the prototype.",
            },
        )

    # Validate video ID extractable
    video_id = extract_video_id(url)
    if not video_id:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_URL",
                "message": "Could not extract a valid YouTube video ID from the URL.",
            },
        )

    analysis_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    ttl = int(time.time()) + (90 * 24 * 60 * 60)  # 90 days

    # Write initial record to DynamoDB
    db = get_dynamodb()
    table = db.Table(settings.analyses_table_name)
    table.put_item(Item={
        "analysis_id": analysis_id,
        "created_at": created_at,
        "user_id": "anonymous",
        "platform": platform,
        "content_url": url,
        "language": request.language or "auto",
        "status": AnalysisStatus.QUEUED.value,
        "ttl": ttl,
    })

    # Run full ingestion in background — API returns 202 immediately
    background_tasks.add_task(
        run_ingestion,
        analysis_id=analysis_id,
        content_url=url,
        platform=platform,
        created_at=created_at,
        language_override=request.language,
    )

    return AnalyzeSubmittedResponse(
        analysis_id=analysis_id,
        status=AnalysisStatus.QUEUED,
        message="Analysis queued. Ingestion starting. Poll GET /api/v1/analyze/{analysis_id} for results.",
    )


@router.get("/analyze/{analysis_id}", response_model=AnalysisResult)
async def get_analysis(analysis_id: str):
    settings = get_settings()
    db = get_dynamodb()
    table = db.Table(settings.analyses_table_name)

    # Query by analysis_id using proper Key condition
    response = table.query(
        KeyConditionExpression=Key("analysis_id").eq(analysis_id),
        Limit=1,
    )

    items = response.get("Items", [])
    if not items:
        raise HTTPException(status_code=404, detail={
            "code": "ANALYSIS_NOT_FOUND",
            "message": f"No analysis found with ID: {analysis_id}",
        })

    item = items[0]

    # Normalise findings — stored as list of dicts, schema expects List[Finding]
    raw_findings = item.get("findings") or []
    findings = [
        {"module": f.get("module", ""), "signal": f.get("signal", ""),
         "severity": f.get("severity", "INFO"), "detail": f.get("detail", "")}
        for f in raw_findings
    ] if raw_findings else None

    return AnalysisResult(
        analysis_id=item["analysis_id"],
        status=AnalysisStatus(item.get("status", "processing")),
        content_url=item.get("content_url"),
        platform=item.get("platform"),
        language=item.get("language"),
        satya_score=_to_float(item.get("satya_score")),
        video_score=_to_float(item.get("video_score")),
        audio_score=_to_float(item.get("audio_score")),
        text_score=_to_float(item.get("text_score")),
        verdict=Verdict(item["verdict"]) if item.get("verdict") else None,
        confidence=item.get("confidence"),
        summary=item.get("summary"),
        findings=findings,
        recommendations=item.get("recommendations"),
        processing_time_ms=int(item["processing_time_ms"]) if item.get("processing_time_ms") else None,
        error_message=item.get("error_message"),
        created_at=item.get("created_at"),
    )
