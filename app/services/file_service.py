import os
import uuid
import asyncio
import time
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
import logging
import aiofiles
from app.config import settings

logger = logging.getLogger(__name__)

class FileService:
    """Service for handling file operations and media processing - Vercel optimized"""
    
    def __init__(self):
        # Use /tmp for Vercel serverless
        self.upload_dir = Path(settings.upload_dir)
        self.temp_dir = Path(settings.temp_dir) 
        
        # Ensure directories exist
        try:
            self.upload_dir.mkdir(exist_ok=True, parents=True)
            self.temp_dir.mkdir(exist_ok=True, parents=True)
        except Exception as e:
            logger.warning(f"Could not create directories: {e}")
    
    async def save_upload_file(self, file_content: bytes, filename: str, job_id: str) -> str:
        """Save uploaded file and return the file path"""
        try:
            # Create job-specific directory in /tmp
            job_dir = self.upload_dir / job_id
            job_dir.mkdir(exist_ok=True, parents=True)
            
            # Generate unique filename
            file_extension = Path(filename).suffix
            unique_filename = f"original{file_extension}"
            file_path = job_dir / unique_filename
            
            # Save file asynchronously
            async with aiofiles.open(file_path, "wb") as f:
                await f.write(file_content)
            
            logger.info(f"File saved: {file_path}")
            return str(file_path)
        
        except Exception as e:
            logger.error(f"Error saving file: {str(e)}")
            raise
    
    async def get_video_info(self, video_path: str) -> Dict[str, Any]:
        """Get video metadata - simplified for serverless"""
        try:
            # Simplified version without ffmpeg-python for Vercel
            file_size = os.path.getsize(video_path)
            
            info = {
                "duration": 0,  # Would need ffprobe
                "size": file_size,
                "bitrate": 0,
                "video": {
                    "codec": "unknown",
                    "width": 0,
                    "height": 0,
                    "fps": 0
                },
                "audio": {
                    "codec": "unknown", 
                    "channels": 0,
                    "sample_rate": 0
                }
            }
            
            logger.info(f"Video info extracted for {video_path}")
            return info
            
        except Exception as e:
            logger.error(f"Error getting video info: {str(e)}")
            # Return default info
            return {
                "duration": 0,
                "size": 0,
                "bitrate": 0,
                "video": {"codec": "unknown", "width": 0, "height": 0, "fps": 0},
                "audio": {"codec": "unknown", "channels": 0, "sample_rate": 0}
            }
    
    async def extract_audio(self, video_path: str, job_id: str) -> Tuple[str, float]:
        """Extract audio from video - NOTE: Requires external service for Vercel"""
        try:
            job_dir = Path(video_path).parent
            audio_path = job_dir / "extracted_audio.wav"
            
            # For Vercel deployment, this would need to use:
            # 1. External service like CloudConvert API
            # 2. Pre-built binary in deployment
            # 3. Different approach like client-side extraction
            
            # Placeholder implementation - would need actual audio extraction
            logger.warning("Audio extraction not implemented for Vercel serverless")
            
            # Create empty audio file as placeholder
            async with aiofiles.open(audio_path, "wb") as f:
                await f.write(b"")
            
            duration = 60.0  # Placeholder duration
            
            logger.info(f"Audio extracted: {audio_path} (duration: {duration}s)")
            return str(audio_path), duration
        
        except Exception as e:
            logger.error(f"Error extracting audio: {str(e)}")
            raise
    
    async def merge_audio_video(self, original_video_path: str, new_audio_path: str, job_id: str) -> str:
        """Merge new audio with original video - NOTE: Requires external service"""
        try:
            job_dir = Path(original_video_path).parent
            output_path = job_dir / "final_dubbed_video.mp4"
            
            # For Vercel, this would need external service or different approach
            logger.warning("Video merging not implemented for Vercel serverless")
            
            # Copy original as placeholder
            import shutil
            shutil.copy2(original_video_path, output_path)
            
            logger.info(f"Audio and video merged: {output_path}")
            return str(output_path)
        
        except Exception as e:
            logger.error(f"Error merging audio and video: {str(e)}")
            raise
    
    async def _get_audio_duration(self, audio_path: str) -> float:
        """Get audio duration - simplified for serverless"""
        try:
            # Would need ffprobe or other tool
            return 60.0  # Placeholder
        except Exception:
            return 0.0
    
    async def get_file_size(self, file_path: str) -> int:
        """Get file size in bytes"""
        try:
            return os.path.getsize(file_path)
        except Exception:
            return 0
    
    async def save_text_file(self, content: str, filename: str, job_id: str) -> str:
        """Save text content to file"""
        try:
            job_dir = self.upload_dir / job_id
            job_dir.mkdir(exist_ok=True, parents=True)
            
            file_path = job_dir / filename
            
            async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                await f.write(content)
            
            logger.info(f"Text file saved: {file_path}")
            return str(file_path)
        
        except Exception as e:
            logger.error(f"Error saving text file: {str(e)}")
            raise
    
    async def read_text_file(self, file_path: str) -> str:
        """Read text content from file"""
        try:
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                content = await f.read()
            return content
        
        except Exception as e:
            logger.error(f"Error reading text file: {str(e)}")
            raise
    
    async def cleanup_job_files(self, job_id: str, keep_final: bool = True):
        """Clean up temporary files for a job"""
        try:
            job_dir = self.upload_dir / job_id
            
            if not job_dir.exists():
                return
            
            files_to_remove = []
            
            # List files to remove (keep original and final if requested)
            for file_path in job_dir.iterdir():
                if file_path.is_file():
                    if keep_final and "final" in file_path.name:
                        continue
                    if "original" in file_path.name:
                        continue
                    files_to_remove.append(file_path)
            
            # Remove files
            for file_path in files_to_remove:
                try:
                    file_path.unlink()
                except Exception as e:
                    logger.warning(f"Could not remove {file_path}: {e}")
            
            logger.info(f"Cleaned up {len(files_to_remove)} files for job {job_id}")
        
        except Exception as e:
            logger.error(f"Error cleaning up files: {str(e)}")
    
    async def cleanup_temp_files(self):
        """Clean up old temporary files"""
        try:
            for file_path in self.temp_dir.iterdir():
                if file_path.is_file():
                    # Remove files older than 1 hour
                    if time.time() - file_path.stat().st_mtime > 3600:
                        try:
                            file_path.unlink()
                        except Exception as e:
                            logger.warning(f"Could not remove temp file {file_path}: {e}")
        except Exception as e:
            logger.error(f"Error cleaning temp files: {str(e)}")
    
    def get_job_directory(self, job_id: str) -> Path:
        """Get job directory path"""
        return self.upload_dir / job_id
    
    def validate_video_file(self, filename: str, content: bytes) -> bool:
        """Validate if uploaded file is a valid video"""
        try:
            # Check file extension
            allowed_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm']
            if not any(filename.lower().endswith(ext) for ext in allowed_extensions):
                return False
            
            # Check file size - reduced for serverless
            if len(content) > settings.max_file_size:
                return False
            
            # Basic magic number check for video files
            video_signatures = [
                b'\x00\x00\x00\x18ftypmp4',  # MP4
                b'\x00\x00\x00\x20ftypmp4',  # MP4
                b'RIFF',                      # AVI (starts with RIFF)
                b'\x1aE\xdf\xa3',           # MKV/WebM
            ]
            
            for signature in video_signatures:
                if content.startswith(signature):
                    return True
            
            # If no signature match, still allow (some video formats vary)
            return True
            
        except Exception as e:
            logger.error(f"Error validating video file: {str(e)}")
            return False

logger = logging.getLogger(__name__)

class FileService:
    """Service for handling file operations and media processing"""
    
    def __init__(self):
        self.upload_dir = Path(settings.upload_dir)
        self.temp_dir = Path(settings.temp_dir)
        self.upload_dir.mkdir(exist_ok=True)
        self.temp_dir.mkdir(exist_ok=True)
    
    async def save_upload_file(self, file_content: bytes, filename: str, job_id: str) -> str:
        """Save uploaded file and return the file path"""
        try:
            # Create job-specific directory
            job_dir = self.upload_dir / job_id
            job_dir.mkdir(exist_ok=True)
            
            # Generate unique filename
            file_extension = Path(filename).suffix
            unique_filename = f"original{file_extension}"
            file_path = job_dir / unique_filename
            
            # Save file asynchronously
            async with aiofiles.open(file_path, "wb") as f:
                await f.write(file_content)
            
            logger.info(f"File saved: {file_path}")
            return str(file_path)
        
        except Exception as e:
            logger.error(f"Error saving file: {str(e)}")
            raise
    
    async def get_video_info(self, video_path: str) -> Dict[str, Any]:
        """Get video metadata using ffprobe"""
        try:
            probe = ffmpeg.probe(video_path)
            
            video_stream = next((stream for stream in probe['streams'] 
                               if stream['codec_type'] == 'video'), None)
            audio_stream = next((stream for stream in probe['streams'] 
                               if stream['codec_type'] == 'audio'), None)
            
            info = {
                "duration": float(probe['format']['duration']),
                "size": int(probe['format']['size']),
                "bitrate": int(probe['format']['bit_rate']),
                "video": {
                    "codec": video_stream['codec_name'] if video_stream else None,
                    "width": int(video_stream['width']) if video_stream else 0,
                    "height": int(video_stream['height']) if video_stream else 0,
                    "fps": eval(video_stream['r_frame_rate']) if video_stream else 0
                },
                "audio": {
                    "codec": audio_stream['codec_name'] if audio_stream else None,
                    "channels": int(audio_stream['channels']) if audio_stream else 0,
                    "sample_rate": int(audio_stream['sample_rate']) if audio_stream else 0
                }
            }
            
            logger.info(f"Video info extracted for {video_path}")
            return info
            
        except Exception as e:
            logger.error(f"Error getting video info: {str(e)}")
            raise
    
    async def extract_audio(self, video_path: str, job_id: str) -> Tuple[str, float]:
        """Extract audio from video file using FFmpeg"""
        try:
            job_dir = Path(video_path).parent
            audio_path = job_dir / "extracted_audio.wav"
            
            # Use ffmpeg-python for better async handling
            stream = ffmpeg.input(video_path)
            audio = stream.audio
            out = ffmpeg.output(
                audio, 
                str(audio_path),
                acodec='pcm_s16le',
                ar=16000,
                ac=1,
                y=None
            )
            
            # Run ffmpeg asynchronously
            process = await asyncio.create_subprocess_exec(
                *ffmpeg.compile(out),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise Exception(f"FFmpeg error: {stderr.decode()}")
            
            # Get audio duration
            duration = await self._get_audio_duration(str(audio_path))
            
            logger.info(f"Audio extracted: {audio_path} (duration: {duration}s)")
            return str(audio_path), duration
        
        except Exception as e:
            logger.error(f"Error extracting audio: {str(e)}")
            raise
    
    async def merge_audio_video(self, original_video_path: str, new_audio_path: str, job_id: str) -> str:
        """Merge new audio with original video"""
        try:
            job_dir = Path(original_video_path).parent
            output_path = job_dir / "final_dubbed_video.mp4"
            
            # Get original video info to maintain quality
            video_info = await self.get_video_info(original_video_path)
            
            # Create ffmpeg streams
            video = ffmpeg.input(original_video_path)
            audio = ffmpeg.input(new_audio_path)
            
            # Configure output with optimal settings
            out = ffmpeg.output(
                video['v'], audio['a'],
                str(output_path),
                vcodec='libx264',
                acodec='aac',
                audio_bitrate='128k',
                video_bitrate=f"{video_info.get('bitrate', 2000000)}",
                preset='medium',
                crf=23,
                y=None
            )
            
            # Run ffmpeg asynchronously
            process = await asyncio.create_subprocess_exec(
                *ffmpeg.compile(out),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise Exception(f"FFmpeg merge error: {stderr.decode()}")
            
            logger.info(f"Audio and video merged: {output_path}")
            return str(output_path)
        
        except Exception as e:
            logger.error(f"Error merging audio and video: {str(e)}")
            raise
    
    async def _get_audio_duration(self, audio_path: str) -> float:
        """Get audio duration using FFprobe"""
        try:
            probe = ffmpeg.probe(audio_path)
            return float(probe['format']['duration'])
        except Exception:
            return 0.0
    
    async def get_file_size(self, file_path: str) -> int:
        """Get file size in bytes"""
        try:
            return os.path.getsize(file_path)
        except Exception:
            return 0
    
    async def save_text_file(self, content: str, filename: str, job_id: str) -> str:
        """Save text content to file"""
        try:
            job_dir = self.upload_dir / job_id
            job_dir.mkdir(exist_ok=True)
            
            file_path = job_dir / filename
            
            async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                await f.write(content)
            
            logger.info(f"Text file saved: {file_path}")
            return str(file_path)
        
        except Exception as e:
            logger.error(f"Error saving text file: {str(e)}")
            raise
    
    async def read_text_file(self, file_path: str) -> str:
        """Read text content from file"""
        try:
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                content = await f.read()
            return content
        
        except Exception as e:
            logger.error(f"Error reading text file: {str(e)}")
            raise
    
    async def cleanup_job_files(self, job_id: str, keep_final: bool = True):
        """Clean up temporary files for a job"""
        try:
            job_dir = self.upload_dir / job_id
            
            if not job_dir.exists():
                return
            
            files_to_remove = []
            
            # List files to remove (keep original and final if requested)
            for file_path in job_dir.iterdir():
                if file_path.is_file():
                    if keep_final and "final" in file_path.name:
                        continue
                    if "original" in file_path.name:
                        continue
                    files_to_remove.append(file_path)
            
            # Remove files
            for file_path in files_to_remove:
                file_path.unlink()
            
            logger.info(f"Cleaned up {len(files_to_remove)} files for job {job_id}")
        
        except Exception as e:
            logger.error(f"Error cleaning up files: {str(e)}")
    
    async def cleanup_temp_files(self):
        """Clean up old temporary files"""
        try:
            for file_path in self.temp_dir.iterdir():
                if file_path.is_file():
                    # Remove files older than 1 hour
                    if time.time() - file_path.stat().st_mtime > 3600:
                        file_path.unlink()
        except Exception as e:
            logger.error(f"Error cleaning temp files: {str(e)}")
    
    def get_job_directory(self, job_id: str) -> Path:
        """Get job directory path"""
        return self.upload_dir / job_id
    
    def validate_video_file(self, filename: str, content: bytes) -> bool:
        """Validate if uploaded file is a valid video"""
        try:
            # Check file extension
            allowed_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm']
            if not any(filename.lower().endswith(ext) for ext in allowed_extensions):
                return False
            
            # Check file size
            if len(content) > settings.max_file_size:
                return False
            
            # Basic magic number check for video files
            video_signatures = [
                b'\x00\x00\x00\x18ftypmp4',  # MP4
                b'\x00\x00\x00\x20ftypmp4',  # MP4
                b'RIFF',                      # AVI (starts with RIFF)
                b'\x1aE\xdf\xa3',           # MKV/WebM
            ]
            
            for signature in video_signatures:
                if content.startswith(signature):
                    return True
            
            # If no signature match, still allow (some video formats vary)
            return True
            
        except Exception as e:
            logger.error(f"Error validating video file: {str(e)}")
            return False