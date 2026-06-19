from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
import uuid
import logging
import json
from datetime import datetime

from app.models import DubbingJob, JobLog, JobStatus, JobStep, Language
from app.schemas import JobCreate, JobResponse, JobProgressUpdate
from app.services.redis_service import RedisService

logger = logging.getLogger(__name__)

class JobService:
    """Service for managing dubbing jobs"""
    
    def __init__(self, redis_service: RedisService):
        self.redis_service = redis_service
    
    async def create_job(self, db: AsyncSession, job_data: JobCreate, file_path: str, filename: str) -> DubbingJob:
        """Create a new dubbing job"""
        try:
            job = DubbingJob(
                title=job_data.title,
                original_filename=filename,
                file_path=file_path,
                source_language=job_data.source_language,
                target_language=job_data.target_language,
                status=JobStatus.PENDING,
                current_step=JobStep.UPLOADED,
                progress_percentage=5.0
            )
            
            db.add(job)
            await db.commit()
            await db.refresh(job)
            
            # Log job creation
            await self.add_job_log(
                db, job.id, JobStep.UPLOADED, 
                f"Job created: {job_data.title}", "INFO"
            )
            
            # Cache job in Redis
            try:
                await self.redis_service.cache_job(job.id, JobResponse.model_validate(job))
            except Exception as cache_err:
                logger.warning(f"Failed to cache job: {cache_err}")
            
            logger.info(f"Created job {job.id}: {job_data.title}")
            return job
        
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating job: {str(e)}")
            raise
    
    async def get_job(self, db: AsyncSession, job_id: str) -> Optional[DubbingJob]:
        """Get job by ID"""
        try:
            # Try Redis cache first
            cached_job = await self.redis_service.get_cached_job(job_id)
            if cached_job:
                return await self._get_job_from_db(db, job_id)
            
            # Fallback to database
            job = await self._get_job_from_db(db, job_id)
            if job:
                try:
                    await self.redis_service.cache_job(job_id, JobResponse.model_validate(job))
                except Exception as cache_err:
                    logger.warning(f"Failed to cache job: {cache_err}")
            
            return job
        
        except Exception as e:
            logger.error(f"Error getting job {job_id}: {str(e)}")
            raise
    
    async def _get_job_from_db(self, db: AsyncSession, job_id: str) -> Optional[DubbingJob]:
        """Get job from database"""
        result = await db.execute(select(DubbingJob).where(DubbingJob.id == job_id))
        return result.scalar_one_or_none()
    
    async def list_jobs(self, db: AsyncSession, skip: int = 0, limit: int = 10) -> tuple[List[DubbingJob], int]:
        """List jobs with pagination"""
        try:
            # Get total count
            count_result = await db.execute(select(func.count(DubbingJob.id)))
            total = count_result.scalar()
            
            # Get jobs with pagination
            result = await db.execute(
                select(DubbingJob)
                .order_by(DubbingJob.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            jobs = result.scalars().all()
            
            return list(jobs), total
        
        except Exception as e:
            logger.error(f"Error listing jobs: {str(e)}")
            raise
    
    async def update_job_progress(
        self, 
        db: AsyncSession, 
        job_id: str, 
        update: JobProgressUpdate,
        file_paths: Optional[dict] = None
    ) -> Optional[DubbingJob]:
        """Update job progress and status"""
        try:
            job = await self._get_job_from_db(db, job_id)
            if not job:
                return None
            
            # Update job fields
            job.status = update.status
            job.current_step = update.current_step
            job.progress_percentage = update.progress_percentage
            
            if update.error_message:
                job.error_message = update.error_message
            
            # Update file paths if provided
            if file_paths:
                for field, path in file_paths.items():
                    setattr(job, field, path)
            
            # Set completion timestamp
            if update.status == JobStatus.COMPLETED:
                job.completed_at = datetime.utcnow()
            
            job.updated_at = datetime.utcnow()
            
            await db.commit()
            await db.refresh(job)
            
            # Update Redis cache
            try:
                await self.redis_service.cache_job(job_id, JobResponse.model_validate(job))
            except Exception as cache_err:
                logger.warning(f"Failed to cache job progress: {cache_err}")
            
            # Log progress update
            await self.add_job_log(
                db, job_id, update.current_step,
                f"Progress updated: {update.progress_percentage}% - {update.status.value}",
                "ERROR" if update.error_message else "INFO",
                json.dumps(file_paths) if file_paths else None
            )
            
            logger.info(f"Updated job {job_id}: {update.status.value} - {update.progress_percentage}%")
            return job
        
        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating job progress {job_id}: {str(e)}")
            raise
    
    async def increment_retry_count(self, db: AsyncSession, job_id: str) -> Optional[DubbingJob]:
        """Increment job retry count"""
        try:
            job = await self._get_job_from_db(db, job_id)
            if not job:
                return None
            
            job.retry_count += 1
            job.updated_at = datetime.utcnow()
            
            await db.commit()
            await db.refresh(job)
            
            # Update Redis cache
            return job
        
        except Exception as e:
            await db.rollback()
            logger.error(f"Error incrementing retry count {job_id}: {str(e)}")
            raise
    
    async def add_job_log(
        self, 
        db: AsyncSession, 
        job_id: str, 
        step: JobStep, 
        message: str, 
        level: str = "INFO",
        metadata_json: Optional[str] = None
    ):
        """Add a log entry for a job"""
        try:
            log_entry = JobLog(
                job_id=job_id,
                step=step,
                message=message,
                level=level,
                metadata_json=metadata_json
            )
            
            db.add(log_entry)
            await db.commit()
            
            # Cache recent logs in Redis
            await self.redis_service.cache_job_log(job_id, log_entry)
            
        except Exception as e:
            logger.error(f"Error adding job log {job_id}: {str(e)}")
            # Don't raise exception for logging errors
    
    async def get_job_logs(self, db: AsyncSession, job_id: str, limit: int = 50) -> List[JobLog]:
        """Get logs for a job"""
        try:
            result = await db.execute(
                select(JobLog)
                .where(JobLog.job_id == job_id)
                .order_by(JobLog.timestamp.desc())
                .limit(limit)
            )
            return list(result.scalars().all())
        
        except Exception as e:
            logger.error(f"Error getting job logs {job_id}: {str(e)}")
            return []
    
    async def cancel_job(self, db: AsyncSession, job_id: str) -> Optional[DubbingJob]:
        """Cancel a job"""
        try:
            job = await self._get_job_from_db(db, job_id)
            if not job:
                return None
            
            if job.status in [JobStatus.COMPLETED, JobStatus.CANCELLED]:
                return job
            
            job.status = JobStatus.CANCELLED
            job.updated_at = datetime.utcnow()
            
            await db.commit()
            await db.refresh(job)
            
            # Update Redis cache
            try:
                await self.redis_service.cache_job(job_id, JobResponse.model_validate(job))
            except Exception as cache_err:
                logger.warning(f"Failed to cache cancelled job: {cache_err}")
            
            # Add cancellation log
            await self.add_job_log(
                db, job_id, job.current_step,
                "Job cancelled by user", "WARNING"
            )
            
            logger.info(f"Cancelled job {job_id}")
            return job
        
        except Exception as e:
            await db.rollback()
            logger.error(f"Error cancelling job {job_id}: {str(e)}")
            raise