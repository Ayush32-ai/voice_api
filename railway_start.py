"""
Production server for Railway deployment
"""

import os
import uvicorn
from pathlib import Path

def setup_directories():
    """Create necessary directories"""
    dirs = ['uploads', 'temp', 'logs']
    for dir_name in dirs:
        Path(dir_name).mkdir(exist_ok=True)

def main():
    """Start the production server"""
    # Setup directories
    setup_directories()
    
    # Get port from environment (Railway provides this)
    port = int(os.environ.get("PORT", 8000))
    
    # Start the server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    )

if __name__ == "__main__":
    main()