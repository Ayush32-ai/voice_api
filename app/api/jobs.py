from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import uuid
import logging

from app.database import get_db
from app.models import JobStatus, Language
from app.schemas import JobCreate, JobResponse, JobListResponse, JobLogResponse, HealthCheck
from app.services.job_service import JobService
from app.services.file_service import FileService
from app.services.redis_service import redis_service
from app.worker import process_dubbing_job
from app.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# Service instances
job_service = JobService(redis_service)
file_service = FileService()

@router.post("/jobs", response_model=JobResponse, status_code=201)
async def create_dubbing_job(
    file: UploadFile = File(...),
    title: str = Form(...),
    source_language: Language = Form(...),
    target_language: Language = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new dubbing job by uploading a video file
    
    - **file**: Video file to process (MP4, AVI, MOV supported)
    - **title**: Job title/name
    - **source_language**: Language of the original video (en, hi, ta)
    - **target_language**: Target language for dubbing (en, hi, ta)
    """
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file uploaded")
        
        # Check file size
        content = await file.read()
        if len(content) > settings.max_file_size:
            raise HTTPException(
                status_code=413, 
                detail=f"File too large. Maximum size: {settings.max_file_size} bytes"
            )
        
        # Validate file type
        allowed_extensions = ['.mp4', '.avi', '.mov', '.mkv']
        if not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type. Allowed: MP4, AVI, MOV, MKV"
            )
        
        # Create job data
        job_data = JobCreate(
            title=title,
            source_language=source_language,
            target_language=target_language
        )
        
        # Create job in database
        job = await job_service.create_job(db, job_data, "", file.filename)
        
        # Save uploaded file
        file_path = await file_service.save_upload_file(content, file.filename, job.id)
        
        # Update job with file path and size
        job.file_path = file_path
        job.file_size_bytes = len(content)
        await db.commit()
        await db.refresh(job)
        
        # Start background processing in-process (Railway runs a single web container)
        try:
            import asyncio
            from app.worker import process_dubbing_job_sync, CELERY_AVAILABLE, process_dubbing_job

            if settings.use_celery_worker and CELERY_AVAILABLE:
                process_dubbing_job.delay(str(job.id))
                logger.info(f"Queued job {job.id} to Celery worker")
            else:
                asyncio.create_task(process_dubbing_job_sync(str(job.id)))
                logger.info(f"Started in-process dubbing for job {job.id}")
        except Exception as e:
            logger.error(f"Failed to start job processing: {e}")
            # Job will remain in PENDING state
        
        logger.info(f"Created dubbing job {job.id}: {title}")
        
        return JobResponse.model_validate(job)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating job: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create job")

@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    skip: int = Query(0, ge=0, description="Number of jobs to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of jobs to return"),
    status: Optional[JobStatus] = Query(None, description="Filter by job status"),
    db: AsyncSession = Depends(get_db)
):
    """
    List dubbing jobs with pagination and optional status filtering
    """
    try:
        jobs, total = await job_service.list_jobs(db, skip, limit)
        
        # Filter by status if provided
        if status:
            jobs = [job for job in jobs if job.status == status]
            total = len(jobs)
        
        job_responses = [JobResponse.model_validate(job) for job in jobs]
        
        return JobListResponse(
            jobs=job_responses,
            total=total,
            page=skip // limit + 1,
            size=len(job_responses)
        )
    
    except Exception as e:
        logger.error(f"Error listing jobs: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list jobs")

@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed information about a specific job
    """
    try:
        job = await job_service.get_job(db, job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return JobResponse.model_validate(job)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get job")

@router.get("/jobs/{job_id}/logs", response_model=List[JobLogResponse])
async def get_job_logs(
    job_id: str,
    limit: int = Query(50, ge=1, le=200, description="Number of logs to return"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get processing logs for a specific job
    """
    try:
        # Check if job exists
        job = await job_service.get_job(db, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Get logs from database
        logs = await job_service.get_job_logs(db, job_id, limit)
        
        return [JobLogResponse.model_validate(log) for log in logs]
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job logs {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get job logs")

@router.get("/jobs/{job_id}/progress")
async def get_job_progress(job_id: str, db: AsyncSession = Depends(get_db)):
    """
    Get real-time progress for a job from Redis cache
    """
    try:
        progress = await redis_service.get_job_progress(job_id)
        
        if not progress:
            # Fallback to database
            job = await job_service.get_job(db, job_id)
            if not job:
                raise HTTPException(status_code=404, detail="Job not found")
            
            progress = {
                "progress": job.progress_percentage,
                "step": job.current_step.value,
                "status": job.status.value,
                "timestamp": job.updated_at.isoformat() if job.updated_at else None
            }
        
        return progress
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job progress {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get job progress")

@router.post("/jobs/{job_id}/cancel", response_model=JobResponse)
async def cancel_job(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel a running or pending job
    """
    try:
        job = await job_service.cancel_job(db, job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        logger.info(f"Cancelled job {job_id}")
        return JobResponse.model_validate(job)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to cancel job")

@router.delete("/jobs/{job_id}")
async def delete_job(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a job and its associated files
    """
    try:
        job = await job_service.get_job(db, job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Only allow deletion of completed, failed, or cancelled jobs
        if job.status == JobStatus.PROCESSING:
            raise HTTPException(
                status_code=400, 
                detail="Cannot delete a job that is currently processing"
            )
        
        # Clean up files
        await file_service.cleanup_job_files(job_id, keep_final=False)
        
        # Remove from Redis cache
        await redis_service.invalidate_job_cache(job_id)
        
        # Delete from database
        await db.delete(job)
        await db.commit()
        
        logger.info(f"Deleted job {job_id}")
        return {"message": "Job deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete job")

@router.get("/health", response_model=HealthCheck)
async def health_check():
    """
    Health check endpoint for the jobs API
    """
    from datetime import datetime
    
    # Check Redis connection
    redis_healthy = await redis_service.health_check()
    
    status = "healthy" if redis_healthy else "degraded"
    
    return HealthCheck(
        status=status,
        timestamp=datetime.utcnow()
    )