from fastapi import APIRouter
from api.config import get_settings, get_boto3_session
from boto3.dynamodb.conditions import Key
from datetime import datetime, timezone, timedelta

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


def get_dynamodb():
    session = get_boto3_session()
    return session.resource("dynamodb")


@router.get("/stats")
async def get_stats():
    """Overall platform statistics."""
    settings = get_settings()
    db = get_dynamodb()
    table = db.Table(settings.analyses_table_name)

    # Scan for counts — acceptable for prototype scale
    response = table.scan(
        Select="COUNT",
        FilterExpression="attribute_exists(satya_score)",
    )
    total = response.get("Count", 0)

    high_risk_response = table.scan(
        Select="COUNT",
        FilterExpression="#v = :v",
        ExpressionAttributeNames={"#v": "verdict"},
        ExpressionAttributeValues={":v": "HIGH_RISK"},
    )
    fakes_detected = high_risk_response.get("Count", 0)

    return {
        "total_analyses": total,
        "fakes_detected": fakes_detected,
        "authenticity_rate": round((total - fakes_detected) / total * 100, 1) if total > 0 else 0,
        "platforms_supported": ["youtube"],
        "languages_supported": ["en", "hi", "ta", "te", "bn", "mr", "gu", "kn", "ml", "pa", "or"],
    }


@router.get("/trending")
async def get_trending(platform: str = "youtube", period: str = "24h"):
    """Recently detected AI-generated content."""
    settings = get_settings()
    db = get_dynamodb()
    table = db.Table(settings.trending_table_name)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    response = table.query(
        KeyConditionExpression=Key("date").eq(today),
        ScanIndexForward=False,
        Limit=10,
    )

    items = response.get("Items", [])
    return {
        "period": period,
        "platform": platform,
        "trending_fakes": items,
        "total": len(items),
    }
