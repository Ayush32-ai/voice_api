"""
Vercel deployment entry point for AI Dubbing Studio
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import os
from contextlib import asynccontextmanager

# Set up path for imports
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
    logger.info("Starting AI Dubbing Studio Backend on Vercel")
    
    # Test Redis connection (optional for serverless)
    if await redis_service.health_check():
        logger.info("Redis connection established")
    else:
        logger.warning("Redis connection failed - running without cache")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Dubbing Studio Backend")

# Create FastAPI app
app = FastAPI(
    title="AI Dubbing Studio API",
    description="Asynchronous AI dubbing pipeline using FastAPI, external AI APIs",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware for Vercel
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
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
        "message": "AI Dubbing Studio API - Deployed on Vercel",
        "version": "1.0.0",
        "description": "Asynchronous AI dubbing pipeline",
        "docs": "/docs",
        "status": "running",
        "environment": "production"
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """Comprehensive health check for Vercel"""
    from datetime import datetime
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "version": "1.0.0",
        "platform": "vercel",
        "services": {}
    }
    
    # Check Redis (optional)
    redis_healthy = await redis_service.health_check()
    health_status["services"]["redis"] = {
        "status": "healthy" if redis_healthy else "unavailable",
        "note": "Redis is optional for Vercel deployment"
    }
    
    # Database check (simplified for serverless)
    health_status["services"]["database"] = {
        "status": "configured",
        "type": "external"
    }
    
    return health_status

@app.get("/api/info", tags=["API"])
async def api_info():
    """API capabilities and endpoints"""
    return {
        "name": "AI Dubbing Studio API",
        "version": "1.0.0",
        "platform": "Vercel Serverless",
        "features": [
            "📹 Video Upload & Processing",
            "🎙️ Audio Extraction", 
            "📝 Speech-to-Text (GROQ Whisper)",
            "🌐 Translation (Google Gemini)",
            "🔊 Text-to-Speech (ElevenLabs)",
            "🎬 Audio-Video Merging",
            "📊 Job Progress Tracking",
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
        },
        "deployment": {
            "platform": "Vercel",
            "region": "auto",
            "serverless": true
        }
    }

# Vercel handler
handler = app