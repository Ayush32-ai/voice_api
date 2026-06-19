from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Database - Use PostgreSQL for Vercel (Railway, Neon, or Supabase)
    database_url: str = "sqlite:///./dubbing_studio.db"
    redis_url: str = "redis://localhost:6379"
    secret_key: str = "ai-dubbing-studio-secret-key-2024"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # AI Service API Keys
    openai_api_key: str = "your-openai-key-here"
    elevenlabs_api_key: str = "your-elevenlabs-key-here"
    gemini_api_key: str = "your-gemini-key-here"
    groq_api_key: str = "your-groq-key-here"
    
    # File Storage - Use Vercel blob storage or external service
    upload_dir: str = "/tmp"  # Vercel temp directory
    max_file_size: int = 50 * 1024 * 1024  # 50MB for serverless
    temp_dir: str = "/tmp"
    
    # Processing Settings 
    chunk_size: int = 8192
    max_workers: int = 2  # Limited for serverless
    
    class Config:
        env_file = ".env"
        # Override with environment variables in Vercel
        case_sensitive = False

# Create settings instance
settings = Settings()