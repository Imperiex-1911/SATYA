from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from api.routers import analyze, dashboard
from api.config import get_settings
from api.schemas import HealthResponse
import logging

# Configure logging for all modules
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    handlers=[logging.StreamHandler()],
)

settings = get_settings()

app = FastAPI(
    title="SATYA API",
    description="Synthetic Audio & Video Authenticity — AI content verification for India",
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow all origins for prototype
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(analyze.router)
app.include_router(dashboard.router)


@app.get("/api/v1/health", response_model=HealthResponse, tags=["meta"])
async def health():
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        environment=settings.environment,
        region=settings.aws_region,
    )


@app.get("/api/v1/platforms", tags=["meta"])
async def platforms():
    return {
        "supported": ["youtube"],
        "coming_soon": ["instagram", "sharechat", "x"],
    }


@app.get("/api/v1/languages", tags=["meta"])
async def languages():
    return {
        "supported": [
            {"code": "en", "name": "English"},
            {"code": "hi", "name": "हिन्दी"},
            {"code": "ta", "name": "தமிழ்"},
            {"code": "te", "name": "తెలుగు"},
            {"code": "bn", "name": "বাংলা"},
            {"code": "mr", "name": "मराठी"},
            {"code": "gu", "name": "ગુજરાતી"},
            {"code": "kn", "name": "ಕನ್ನಡ"},
            {"code": "ml", "name": "മലയാളം"},
            {"code": "pa", "name": "ਪੰਜਾਬੀ"},
            {"code": "or", "name": "ଓଡ଼ିଆ"},
        ]
    }


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(status_code=404, content={
        "error": {"code": "NOT_FOUND", "message": "Resource not found"}
    })


@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    return JSONResponse(status_code=500, content={
        "error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred"}
    })
