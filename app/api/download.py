from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import os
import logging
from pathlib import Path

from app.database import get_db
from app.models import JobStatus
from app.services.job_service import JobService
from app.services.redis_service import redis_service

router = APIRouter()
logger = logging.getLogger(__name__)

job_service = JobService(redis_service)


def _resolve_final_video_path(job) -> str | None:
    """Find dubbed video on disk even if stored path is stale."""
    if job.final_video_path and os.path.exists(job.final_video_path):
        return job.final_video_path

    if job.file_path:
        candidate = Path(job.file_path).parent / "final_dubbed_video.mp4"
        if candidate.exists():
            return str(candidate)

    return None


@router.get("/download/{job_id}")
async def download_dubbed_video_default(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Download dubbed video (shorthand - used by mobile app)."""
    return await download_dubbed_video(job_id, db)


@router.get("/download/{job_id}/original")
async def download_original_video(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Download the original uploaded video file
    """
    try:
        job = await job_service.get_job(db, job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if not os.path.exists(job.file_path):
            raise HTTPException(status_code=404, detail="Original file not found")
        
        filename = f"original_{job.original_filename}"
        
        return FileResponse(
            path=job.file_path,
            filename=filename,
            media_type="video/mp4"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading original video {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to download file")

@router.get("/download/{job_id}/dubbed")
async def download_dubbed_video(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Download the final dubbed video file
    """
    try:
        job = await job_service.get_job(db, job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job.status != JobStatus.COMPLETED:
            raise HTTPException(
                status_code=400, 
                detail="Job not completed yet. Cannot download dubbed video."
            )
        
        final_path = _resolve_final_video_path(job)
        if not final_path:
            raise HTTPException(
                status_code=404,
                detail="Dubbed video file not found on server. It may have been removed after a redeploy — please re-run the job."
            )
        
        # Generate filename with language info
        base_name = Path(job.original_filename).stem
        filename = f"{base_name}_dubbed_{job.source_language.value}_to_{job.target_language.value}.mp4"
        
        return FileResponse(
            path=final_path,
            filename=filename,
            media_type="video/mp4"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading dubbed video {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to download file")

@router.get("/download/{job_id}/transcript")
async def download_transcript(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Download the transcript JSON file
    """
    try:
        job = await job_service.get_job(db, job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if not job.transcript_file_path or not os.path.exists(job.transcript_file_path):
            raise HTTPException(status_code=404, detail="Transcript file not found")
        
        filename = f"transcript_{job.title}_{job.source_language.value}.json"
        
        return FileResponse(
            path=job.transcript_file_path,
            filename=filename,
            media_type="application/json"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading transcript {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to download file")

@router.get("/download/{job_id}/translation")
async def download_translation(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Download the translation JSON file
    """
    try:
        job = await job_service.get_job(db, job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if not job.translated_text_path or not os.path.exists(job.translated_text_path):
            raise HTTPException(status_code=404, detail="Translation file not found")
        
        filename = f"translation_{job.title}_{job.source_language.value}_to_{job.target_language.value}.json"
        
        return FileResponse(
            path=job.translated_text_path,
            filename=filename,
            media_type="application/json"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading translation {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to download file")

@router.get("/download/{job_id}/dubbed-audio")
async def download_dubbed_audio(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Download the generated dubbed audio file
    """
    try:
        job = await job_service.get_job(db, job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if not job.dubbed_audio_path or not os.path.exists(job.dubbed_audio_path):
            raise HTTPException(status_code=404, detail="Dubbed audio file not found")
        
        filename = f"dubbed_audio_{job.title}_{job.target_language.value}.mp3"
        
        return FileResponse(
            path=job.dubbed_audio_path,
            filename=filename,
            media_type="audio/mpeg"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading dubbed audio {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to download file")

@router.get("/download/{job_id}/all")
async def get_download_links(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all available download links for a job
    """
    try:
        job = await job_service.get_job(db, job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        base_url = f"/api/download/{job_id}"
        
        downloads = {
            "original_video": {
                "url": f"{base_url}/original",
                "available": os.path.exists(job.file_path) if job.file_path else False,
                "filename": f"original_{job.original_filename}"
            }
        }
        
        # Add other downloads if they exist
        if job.transcript_file_path and os.path.exists(job.transcript_file_path):
            downloads["transcript"] = {
                "url": f"{base_url}/transcript",
                "available": True,
                "filename": f"transcript_{job.title}_{job.source_language.value}.json"
            }
        
        if job.translated_text_path and os.path.exists(job.translated_text_path):
            downloads["translation"] = {
                "url": f"{base_url}/translation",
                "available": True,
                "filename": f"translation_{job.title}_{job.source_language.value}_to_{job.target_language.value}.json"
            }
        
        if job.dubbed_audio_path and os.path.exists(job.dubbed_audio_path):
            downloads["dubbed_audio"] = {
                "url": f"{base_url}/dubbed-audio",
                "available": True,
                "filename": f"dubbed_audio_{job.title}_{job.target_language.value}.mp3"
            }
        
        if job.final_video_path and os.path.exists(job.final_video_path) and job.status == JobStatus.COMPLETED:
            base_name = Path(job.original_filename).stem
            downloads["dubbed_video"] = {
                "url": f"{base_url}/dubbed",
                "available": True,
                "filename": f"{base_name}_dubbed_{job.source_language.value}_to_{job.target_language.value}.mp4"
            }
        elif job.status == JobStatus.COMPLETED:
            resolved = _resolve_final_video_path(job)
            if resolved:
                base_name = Path(job.original_filename).stem
                downloads["dubbed_video"] = {
                    "url": f"{base_url}/dubbed",
                    "available": True,
                    "filename": f"{base_name}_dubbed_{job.source_language.value}_to_{job.target_language.value}.mp4"
                }
        
        return {
            "job_id": str(job_id),
            "job_title": job.title,
            "status": job.status.value,
            "downloads": downloads
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting download links {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get download links")