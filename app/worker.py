import asyncio
import logging
import uuid
from pathlib import Path
import json
import os

# Try to import Celery - optional for serverless deployments
try:
    from celery import Celery
    CELERY_INSTALLED = True
except ImportError:
    CELERY_INSTALLED = False
    Celery = None
    logger = logging.getLogger(__name__)
    logger.warning("Celery not installed - background workers unavailable")

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import JobStatus, JobStep
from app.schemas import JobProgressUpdate
from app.services.job_service import JobService
from app.services.file_service import FileService
from app.services.ai_providers import AIProviderFactory
from app.services.redis_service import redis_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Celery app (optional for development)
celery_app = None
CELERY_AVAILABLE = False

if CELERY_INSTALLED and Celery is not None:
    try:
        celery_app = Celery(
            "dubbing_worker",
            broker=settings.redis_url,
            backend=settings.redis_url
        )

        # Celery configuration
        celery_app.conf.update(
            task_serializer="json",
            accept_content=["json"],
            result_serializer="json",
            timezone="UTC",
            enable_utc=True,
            task_track_started=True,
            task_time_limit=1800,  # 30 minutes
            task_soft_time_limit=1500,  # 25 minutes
            worker_prefetch_multiplier=1,
        )
        CELERY_AVAILABLE = True
    except Exception as e:
        logger.warning(f"Celery not available: {e}")
        celery_app = None
        CELERY_AVAILABLE = False
else:
    logger.info("Celery disabled - using async processing only")

# Services
job_service = JobService(redis_service)
file_service = FileService()

# Celery task (if available)
if CELERY_AVAILABLE:
    @celery_app.task(bind=True, name="process_dubbing_job")
    def process_dubbing_job(self, job_id_str: str):
        """Main task to process a dubbing job"""
        job_id = uuid.UUID(job_id_str)
        
        # Run the async processing function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(_process_dubbing_job_async(job_id))
            return result
        finally:
            loop.close()
else:
    # Fallback for when Celery is not available
    class ProcessDubbingJobFallback:
        """Fallback class that mimics Celery task interface"""
        def delay(self, job_id_str: str):
            """Fallback for Celery's delay method - just logs"""
            logger.info(f"Would process job {job_id_str} (Celery unavailable - use async)")
            return None
    
    process_dubbing_job = ProcessDubbingJobFallback()

# Sync processing for development
async def process_dubbing_job_sync(job_id_str: str):
    """In-process async job processing (used on Railway / single-container deploys)."""
    try:
        return await _process_dubbing_job_async(job_id_str)
    except Exception as e:
        logger.error(f"Error in sync job processing: {e}")
        raise

async def _schedule_job_retry(job_id: str, countdown: int = 60):
    """Retry a failed job using Celery or in-process async."""
    if settings.use_celery_worker and CELERY_AVAILABLE:
        process_dubbing_job.apply_async(args=[str(job_id)], countdown=countdown)
    else:
        await asyncio.sleep(countdown)
        await process_dubbing_job_sync(str(job_id))

async def _process_dubbing_job_async(job_id: str):
    """Async function to process dubbing job"""
    async with AsyncSessionLocal() as db:
        try:
            # Get job details
            job = await job_service.get_job(db, job_id)
            if not job:
                raise Exception(f"Job {job_id} not found")
            
            if job.status == JobStatus.CANCELLED:
                logger.info(f"Job {job_id} was cancelled, skipping processing")
                return {"status": "cancelled"}
            
            logger.info(f"Starting processing for job {job_id}: {job.title}")
            
            # Update job status to processing
            await job_service.update_job_progress(
                db, job_id,
                JobProgressUpdate(
                    status=JobStatus.PROCESSING,
                    current_step=JobStep.UPLOADED,
                    progress_percentage=10.0
                )
            )
            
            # Step 1: Extract Audio
            await _extract_audio_step(db, job, job_id)
            
            # Step 2: Speech to Text
            await _speech_to_text_step(db, job, job_id)
            
            # Step 3: Translation
            await _translation_step(db, job, job_id)
            
            # Step 4: Text to Speech
            await _text_to_speech_step(db, job, job_id)
            
            # Step 5: Merge Audio and Video
            await _merge_audio_video_step(db, job, job_id)
            
            # Mark job as completed
            await job_service.update_job_progress(
                db, job_id,
                JobProgressUpdate(
                    status=JobStatus.COMPLETED,
                    current_step=JobStep.AUDIO_MERGED,
                    progress_percentage=100.0
                )
            )
            
            logger.info(f"Completed processing for job {job_id}")
            return {"status": "completed", "job_id": str(job_id)}
        
        except Exception as e:
            logger.error(f"Error processing job {job_id}: {str(e)}")
            
            failed_job = await job_service.get_job(db, job_id)
            await job_service.update_job_progress(
                db, job_id,
                JobProgressUpdate(
                    status=JobStatus.FAILED,
                    current_step=failed_job.current_step if failed_job else job.current_step,
                    progress_percentage=failed_job.progress_percentage if failed_job else job.progress_percentage,
                    error_message=str(e)
                )
            )
            
            # Check if we should retry
            await job_service.increment_retry_count(db, job_id)
            
            updated_job = await job_service.get_job(db, job_id)
            if updated_job and updated_job.retry_count < updated_job.max_retries:
                logger.info(f"Retrying job {job_id} (attempt {updated_job.retry_count + 1})")
                await _schedule_job_retry(job_id, countdown=60)
            
            raise

async def _extract_audio_step(db, job, job_id):
    """Step 1: Extract audio from video"""
    logger.info(f"Job {job_id}: Extracting audio")
    
    try:
        # Extract audio
        audio_path, duration = await file_service.extract_audio(job.file_path, job_id)
        
        # Update job with audio details
        await job_service.update_job_progress(
            db, job_id,
            JobProgressUpdate(
                status=JobStatus.PROCESSING,
                current_step=JobStep.AUDIO_EXTRACTED,
                progress_percentage=25.0
            ),
            file_paths={"audio_file_path": audio_path, "duration_seconds": duration}
        )
        
        logger.info(f"Job {job_id}: Audio extracted successfully")
    
    except Exception as e:
        raise Exception(f"Audio extraction failed: {str(e)}")

async def _speech_to_text_step(db, job, job_id):
    """Step 2: Convert speech to text using Whisper"""
    logger.info(f"Job {job_id}: Converting speech to text")
    
    try:
        job = await job_service.get_job(db, job_id)
        if not job or not job.audio_file_path:
            raise ValueError("Audio file path missing after extraction step")

        if not os.path.exists(job.audio_file_path):
            raise FileNotFoundError(f"Extracted audio not found: {job.audio_file_path}")

        language_code = job.source_language.value if job.source_language.value != "en" else None
        result = None
        last_error = None

        try:
            groq_provider = AIProviderFactory.get_whisper_provider(use_groq=True)
            result = await groq_provider.process(job.audio_file_path, language_code)
        except Exception as groq_error:
            last_error = groq_error
            logger.warning(f"Job {job_id}: GROQ Whisper failed, trying OpenAI fallback: {groq_error}")
            if settings.openai_api_key not in ("", "not-set"):
                openai_provider = AIProviderFactory.get_whisper_provider(use_groq=False)
                result = await openai_provider.process(job.audio_file_path, language_code)
            else:
                raise groq_error

        if result is None:
            raise last_error or RuntimeError("Speech-to-text returned no result")
        
        # Save transcript
        job_dir = file_service.get_job_directory(job_id)
        transcript_path = job_dir / "transcript.json"
        
        with open(transcript_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        # Update job
        await job_service.update_job_progress(
            db, job_id,
            JobProgressUpdate(
                status=JobStatus.PROCESSING,
                current_step=JobStep.SPEECH_TO_TEXT,
                progress_percentage=50.0
            ),
            file_paths={"transcript_file_path": str(transcript_path)}
        )
        
        logger.info(f"Job {job_id}: Speech-to-text completed")
    
    except Exception as e:
        raise Exception(f"Speech-to-text failed: {str(e)}")

async def _translation_step(db, job, job_id):
    """Step 3: Translate text using Gemini"""
    logger.info(f"Job {job_id}: Translating text")
    
    try:
        # Get fresh job data
        job = await job_service.get_job(db, job_id)
        
        # Load transcript
        with open(job.transcript_file_path, "r", encoding="utf-8") as f:
            transcript_data = json.load(f)
        
        original_text = transcript_data["text"]
        
        # Skip translation if source and target languages are the same
        if job.source_language == job.target_language:
            translated_text = original_text
        else:
            # Use Gemini for translation
            gemini_provider = AIProviderFactory.get_gemini_provider()
            translation_result = await gemini_provider.process(
                original_text,
                job.source_language.value,
                job.target_language.value
            )
            translated_text = translation_result["translated_text"]
        
        # Save translation
        job_dir = file_service.get_job_directory(job_id)
        translation_path = job_dir / "translation.json"
        
        translation_data = {
            "original_text": original_text,
            "translated_text": translated_text,
            "source_language": job.source_language.value,
            "target_language": job.target_language.value
        }
        
        with open(translation_path, "w", encoding="utf-8") as f:
            json.dump(translation_data, f, ensure_ascii=False, indent=2)
        
        # Update job
        await job_service.update_job_progress(
            db, job_id,
            JobProgressUpdate(
                status=JobStatus.PROCESSING,
                current_step=JobStep.TRANSLATED,
                progress_percentage=70.0
            ),
            file_paths={"translated_text_path": str(translation_path)}
        )
        
        logger.info(f"Job {job_id}: Translation completed")
    
    except Exception as e:
        raise Exception(f"Translation failed: {str(e)}")

async def _text_to_speech_step(db, job, job_id):
    """Step 4: Generate speech using ElevenLabs"""
    logger.info(f"Job {job_id}: Generating speech")
    
    try:
        # Get fresh job data
        job = await job_service.get_job(db, job_id)
        
        # Load translation
        with open(job.translated_text_path, "r", encoding="utf-8") as f:
            translation_data = json.load(f)
        
        translated_text = translation_data["translated_text"]
        
        # Generate speech
        elevenlabs_provider = AIProviderFactory.get_elevenlabs_provider()
        
        job_dir = file_service.get_job_directory(job_id)
        dubbed_audio_path = job_dir / "dubbed_audio.mp3"
        
        tts_result = await elevenlabs_provider.process(
            translated_text,
            job.target_language.value,
            str(dubbed_audio_path)
        )
        
        # Update job
        await job_service.update_job_progress(
            db, job_id,
            JobProgressUpdate(
                status=JobStatus.PROCESSING,
                current_step=JobStep.VOICE_GENERATED,
                progress_percentage=90.0
            ),
            file_paths={"dubbed_audio_path": str(dubbed_audio_path)}
        )
        
        logger.info(f"Job {job_id}: Speech generation completed")
    
    except Exception as e:
        raise Exception(f"Speech generation failed: {str(e)}")

async def _merge_audio_video_step(db, job, job_id):
    """Step 5: Merge dubbed audio with original video"""
    logger.info(f"Job {job_id}: Merging audio and video")
    
    try:
        # Get fresh job data
        job = await job_service.get_job(db, job_id)
        
        # Merge audio and video
        final_video_path = await file_service.merge_audio_video(
            job.file_path,
            job.dubbed_audio_path,
            job_id
        )
        
        # Get final file size
        final_size = await file_service.get_file_size(final_video_path)
        
        # Update job
        await job_service.update_job_progress(
            db, job_id,
            JobProgressUpdate(
                status=JobStatus.PROCESSING,
                current_step=JobStep.AUDIO_MERGED,
                progress_percentage=95.0
            ),
            file_paths={
                "final_video_path": final_video_path,
                "file_size_bytes": final_size
            }
        )
        
        # Clean up temporary files
        await file_service.cleanup_job_files(job_id, keep_final=True)
        
        logger.info(f"Job {job_id}: Audio and video merged successfully")
    
    except Exception as e:
        raise Exception(f"Audio/video merge failed: {str(e)}")