from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Database - Optional for Vercel deployment, defaults to SQLite
    database_url: str = "sqlite+aiosqlite:///tmp/dubbing_studio.db"
    redis_url: Optional[str] = None  # Optional for Vercel
    secret_key: str = "default-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # AI Service API Keys - Required
    openai_api_key: str = "not-set"
    elevenlabs_api_key: str = "not-set"
    gemini_api_key: str = "not-set"
    groq_api_key: str = "not-set"
    
    # File Storage - Use Vercel's temp directory
    upload_dir: str = "/tmp/uploads"  # Vercel temp directory
    max_file_size: int = 50 * 1024 * 1024  # 50MB for serverless
    temp_dir: str = "/tmp/temp"
    
    # Processing Settings - Limited for serverless
    chunk_size: int = 8192
    max_workers: int = 2  # Limited for serverless
    
    class Config:
        env_file = ".env"
        # Override with environment variables in Vercel
        case_sensitive = False

# Create settings instance
settings = Settings()