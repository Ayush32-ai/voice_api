"""
AI Dubbing Studio - FastAPI Backend
Main application entry point
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import shutil
import uvicorn
from contextlib import asynccontextmanager

from app.database import create_tables, AsyncSessionLocal
from app.api import jobs, download
from app.services.redis_service import redis_service
from app.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown"""
    # Startup
    logger.info("Starting AI Dubbing Studio Backend")
    
    # Initialize database tables
    await create_tables()
    logger.info("Database tables created")
    
    # Test Redis connection
    if await redis_service.health_check():
        logger.info("Redis connection established")
    else:
        logger.warning("Redis connection failed")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Dubbing Studio Backend")

# Create FastAPI app
app = FastAPI(
    title="AI Dubbing Studio API",
    description="Asynchronous AI dubbing pipeline using FastAPI, AsyncIO, Redis, PostgreSQL and external AI APIs",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(jobs.router, prefix="/api", tags=["Jobs"])
app.include_router(download.router, prefix="/api", tags=["Download"])

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# Health check endpoints
@app.get("/", tags=["Health"])
async def root():
    """Root endpoint - API information"""
    return {
        "message": "AI Dubbing Studio API",
        "version": "1.0.0",
        "description": "Asynchronous AI dubbing pipeline",
        "docs": "/docs",
        "status": "running"
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """Comprehensive health check"""
    from datetime import datetime
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "version": "1.0.0",
        "services": {}
    }
    
    # Check Redis
    redis_healthy = await redis_service.health_check()
    health_status["services"]["redis"] = {
        "status": "healthy" if redis_healthy else "unhealthy",
        "url": settings.redis_url
    }

    ffmpeg_path = shutil.which("ffmpeg")
    health_status["services"]["ffmpeg"] = {
        "status": "healthy" if ffmpeg_path else "unhealthy",
        "path": ffmpeg_path
    }
    if not ffmpeg_path:
        health_status["status"] = "degraded"
    
    # Check Database
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute("SELECT 1")
            health_status["services"]["database"] = {
                "status": "healthy",
                "type": "SQLite"
            }
    except Exception as e:
        health_status["services"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Set overall status
    if health_status["status"] != "degraded" and not redis_healthy:
        health_status["status"] = "degraded"
    
    return health_status

@app.get("/api/info", tags=["API"])
async def api_info():
    """API capabilities and endpoints"""
    return {
        "name": "AI Dubbing Studio API",
        "version": "1.0.0",
        "features": [
            "📹 Video Upload & Processing",
            "🎙️ Audio Extraction",
            "📝 Speech-to-Text (GROQ Whisper)",
            "🌐 Translation (Google Gemini)",
            "🔊 Text-to-Speech (ElevenLabs)",
            "🎬 Audio-Video Merging",
            "📊 Real-time Progress Tracking",
            "🔄 Retry Mechanisms",
            "📜 Structured Logging"
        ],
        "supported_languages": {
            "en": "English",
            "hi": "Hindi",
            "ta": "Tamil"
        },
        "supported_formats": [
            "MP4", "AVI", "MOV", "MKV", "WebM"
        ],
        "ai_providers": {
            "speech_to_text": ["GROQ Whisper", "OpenAI Whisper"],
            "translation": ["Google Gemini"],
            "text_to_speech": ["ElevenLabs"]
        },
        "endpoints": {
            "jobs": "/api/jobs",
            "download": "/api/download/{job_id}",
            "health": "/health",
            "docs": "/docs"
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )