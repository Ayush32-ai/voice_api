from sqlalchemy import Column, Integer, String, DateTime, Text, Enum, Float, Boolean
from sqlalchemy.sql import func
from app.database import Base
import uuid
import enum

class JobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class JobStep(str, enum.Enum):
    UPLOADED = "uploaded"
    AUDIO_EXTRACTED = "audio_extracted"
    SPEECH_TO_TEXT = "speech_to_text"
    TRANSLATED = "translated"
    VOICE_GENERATED = "voice_generated"
    AUDIO_MERGED = "audio_merged"

class Language(str, enum.Enum):
    ENGLISH = "en"
    HINDI = "hi"
    TAMIL = "ta"

class DubbingJob(Base):
    __tablename__ = "dubbing_jobs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    
    # Language settings
    source_language = Column(Enum(Language), nullable=False)
    target_language = Column(Enum(Language), nullable=False)
    
    # Job status and progress
    status = Column(Enum(JobStatus), default=JobStatus.PENDING)
    current_step = Column(Enum(JobStep), default=JobStep.UPLOADED)
    progress_percentage = Column(Float, default=0.0)
    
    # File paths for different stages
    audio_file_path = Column(String(500))
    transcript_file_path = Column(String(500))
    translated_text_path = Column(String(500))
    dubbed_audio_path = Column(String(500))
    final_video_path = Column(String(500))
    
    # Processing details
    duration_seconds = Column(Float)
    file_size_bytes = Column(Integer)
    
    # Error handling
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True))

class JobLog(Base):
    __tablename__ = "job_logs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String(36), nullable=False)
    step = Column(Enum(JobStep), nullable=False)
    message = Column(Text, nullable=False)
    level = Column(String(10), default="INFO")  # INFO, WARNING, ERROR
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    metadata_json = Column(Text)  # JSON string for additional data