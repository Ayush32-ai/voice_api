from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from app.models import JobStatus, JobStep, Language
import uuid

class JobCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    source_language: Language
    target_language: Language

class JobResponse(BaseModel):
    id: str
    title: str
    original_filename: str
    source_language: Language
    target_language: Language
    status: JobStatus
    current_step: JobStep
    progress_percentage: float
    duration_seconds: Optional[float] = None
    file_size_bytes: Optional[int] = None
    error_message: Optional[str] = None
    retry_count: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class JobListResponse(BaseModel):
    jobs: List[JobResponse]
    total: int
    page: int
    size: int

class JobLogResponse(BaseModel):
    id: str
    job_id: str
    step: JobStep
    message: str
    level: str
    timestamp: datetime
    metadata_json: Optional[str] = None
    
    class Config:
        from_attributes = True

class JobProgressUpdate(BaseModel):
    status: JobStatus
    current_step: JobStep
    progress_percentage: float
    error_message: Optional[str] = None

class HealthCheck(BaseModel):
    status: str
    timestamp: datetime
    version: str = "1.0.0"