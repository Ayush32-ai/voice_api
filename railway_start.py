"""
Production server for Railway deployment
"""

import logging
import os
import shutil
import uvicorn
from pathlib import Path

logger = logging.getLogger(__name__)

def setup_directories():
    """Create necessary directories"""
    dirs = ['uploads', 'temp', 'logs']
    for dir_name in dirs:
        Path(dir_name).mkdir(exist_ok=True)

def verify_ffmpeg():
    """Ensure ffmpeg is available before accepting dubbing jobs."""
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if ffmpeg and ffprobe:
        logger.info(f"ffmpeg ready: {ffmpeg}")
        return True
    logger.error(
        "ffmpeg/ffprobe not found in PATH. Dubbing jobs will fail at audio extraction."
    )
    return False

def main():
    """Start the production server"""
    setup_directories()
    verify_ffmpeg()
    
    port = int(os.environ.get("PORT", 8000))
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    )

if __name__ == "__main__":
    main()