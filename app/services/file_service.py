import asyncio
import logging
import os
import shutil
import time
from pathlib import Path
from typing import Any, Dict, Tuple

import aiofiles

from app.config import settings

logger = logging.getLogger(__name__)

MAX_WHISPER_FILE_BYTES = 24 * 1024 * 1024


class FileService:
    """Service for handling file operations and media processing."""

    def __init__(self):
        self.upload_dir = Path(settings.upload_dir)
        self.temp_dir = Path(settings.temp_dir)
        self.upload_dir.mkdir(exist_ok=True, parents=True)
        self.temp_dir.mkdir(exist_ok=True, parents=True)
        self.ffmpeg_path = shutil.which("ffmpeg")
        self.ffprobe_path = shutil.which("ffprobe")
        if not self.ffmpeg_path:
            logger.error("ffmpeg not found in PATH - audio/video processing will fail")

    async def _run_command(self, cmd: list[str], error_prefix: str) -> None:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()
        if process.returncode != 0:
            detail = stderr.decode(errors="replace").strip() or "unknown ffmpeg error"
            raise RuntimeError(f"{error_prefix}: {detail}")

    def _require_ffmpeg(self) -> None:
        if not self.ffmpeg_path:
            raise RuntimeError(
                "ffmpeg is not installed. Railway/Docker must include the ffmpeg package."
            )

    async def save_upload_file(self, file_content: bytes, filename: str, job_id: str) -> str:
        try:
            job_dir = self.upload_dir / job_id
            job_dir.mkdir(exist_ok=True, parents=True)

            file_extension = Path(filename).suffix
            file_path = job_dir / f"original{file_extension}"

            async with aiofiles.open(file_path, "wb") as f:
                await f.write(file_content)

            logger.info(f"File saved: {file_path}")
            return str(file_path)
        except Exception as e:
            logger.error(f"Error saving file: {str(e)}")
            raise

    async def get_video_info(self, video_path: str) -> Dict[str, Any]:
        try:
            if not self.ffprobe_path:
                raise RuntimeError("ffprobe is not installed")
            cmd = [
                self.ffprobe_path,
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                video_path,
            ]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
            if process.returncode != 0:
                raise RuntimeError(f"FFprobe error: {stderr.decode()}")

            import json

            probe = json.loads(stdout.decode())
            video_stream = next(
                (stream for stream in probe.get("streams", []) if stream.get("codec_type") == "video"),
                None,
            )
            audio_stream = next(
                (stream for stream in probe.get("streams", []) if stream.get("codec_type") == "audio"),
                None,
            )

            return {
                "duration": float(probe.get("format", {}).get("duration", 0)),
                "size": int(probe.get("format", {}).get("size", 0)),
                "bitrate": int(probe.get("format", {}).get("bit_rate", 2000000)),
                "video": {
                    "codec": video_stream.get("codec_name") if video_stream else None,
                    "width": int(video_stream.get("width", 0)) if video_stream else 0,
                    "height": int(video_stream.get("height", 0)) if video_stream else 0,
                    "fps": 0,
                },
                "audio": {
                    "codec": audio_stream.get("codec_name") if audio_stream else None,
                    "channels": int(audio_stream.get("channels", 0)) if audio_stream else 0,
                    "sample_rate": int(audio_stream.get("sample_rate", 0)) if audio_stream else 0,
                },
            }
        except Exception as e:
            logger.error(f"Error getting video info: {str(e)}")
            raise

    async def extract_audio(self, video_path: str, job_id: str) -> Tuple[str, float]:
        try:
            self._require_ffmpeg()
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"Video file not found: {video_path}")

            job_dir = Path(video_path).parent
            audio_path = job_dir / "extracted_audio.mp3"

            # MP3 keeps files small enough for GROQ Whisper (25MB limit)
            await self._run_command(
                [
                    self.ffmpeg_path,
                    "-i",
                    video_path,
                    "-vn",
                    "-acodec",
                    "libmp3lame",
                    "-ar",
                    "16000",
                    "-ac",
                    "1",
                    "-b:a",
                    "64k",
                    "-y",
                    str(audio_path),
                ],
                "FFmpeg audio extraction failed",
            )

            audio_path = await self._ensure_whisper_compatible(audio_path)
            duration = await self._get_audio_duration(str(audio_path))

            size = os.path.getsize(audio_path)
            if size == 0:
                raise RuntimeError("Extracted audio file is empty")

            logger.info(
                f"Audio extracted: {audio_path} (duration: {duration}s, size: {size} bytes)"
            )
            return str(audio_path), duration
        except Exception as e:
            logger.error(f"Error extracting audio: {str(e)}")
            raise

    async def _ensure_whisper_compatible(self, audio_path: Path) -> Path:
        """Re-compress audio if it exceeds the Whisper API size limit."""
        size = os.path.getsize(audio_path)
        if size <= MAX_WHISPER_FILE_BYTES:
            return audio_path

        compressed_path = audio_path.with_name("extracted_audio_compressed.mp3")
        logger.info(
            f"Audio file is {size} bytes; re-compressing for Whisper ({MAX_WHISPER_FILE_BYTES} byte limit)"
        )
        await self._run_command(
            [
                self.ffmpeg_path,
                "-i",
                str(audio_path),
                "-acodec",
                "libmp3lame",
                "-ar",
                "16000",
                "-ac",
                "1",
                "-b:a",
                "32k",
                "-y",
                str(compressed_path),
            ],
            "FFmpeg audio compression failed",
        )

        compressed_size = os.path.getsize(compressed_path)
        if compressed_size > MAX_WHISPER_FILE_BYTES:
            raise RuntimeError(
                f"Audio still too large after compression ({compressed_size} bytes). "
                "Try a shorter video."
            )
        return compressed_path

    async def merge_audio_video(
        self, original_video_path: str, new_audio_path: str, job_id: str
    ) -> str:
        try:
            job_dir = Path(original_video_path).parent
            output_path = job_dir / "final_dubbed_video.mp4"

            await self._run_command(
                [
                    self.ffmpeg_path,
                    "-i",
                    original_video_path,
                    "-i",
                    new_audio_path,
                    "-map",
                    "0:v:0",
                    "-map",
                    "1:a:0",
                    "-c:v",
                    "copy",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "128k",
                    "-shortest",
                    "-y",
                    str(output_path),
                ],
                "FFmpeg merge failed",
            )

            logger.info(f"Audio and video merged: {output_path}")
            return str(output_path)
        except Exception as e:
            logger.error(f"Error merging audio and video: {str(e)}")
            raise

    async def _get_audio_duration(self, audio_path: str) -> float:
        try:
            if not self.ffprobe_path:
                return 0.0
            cmd = [
                self.ffprobe_path,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                audio_path,
            ]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await process.communicate()
            if process.returncode != 0:
                return 0.0
            return float(stdout.decode().strip())
        except Exception:
            return 0.0

    async def get_file_size(self, file_path: str) -> int:
        try:
            return os.path.getsize(file_path)
        except Exception:
            return 0

    async def save_text_file(self, content: str, filename: str, job_id: str) -> str:
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
        try:
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                return await f.read()
        except Exception as e:
            logger.error(f"Error reading text file: {str(e)}")
            raise

    async def cleanup_job_files(self, job_id: str, keep_final: bool = True):
        try:
            job_dir = self.upload_dir / job_id
            if not job_dir.exists():
                return

            files_to_remove = []
            for file_path in job_dir.iterdir():
                if not file_path.is_file():
                    continue
                if keep_final and "final" in file_path.name:
                    continue
                if "original" in file_path.name:
                    continue
                files_to_remove.append(file_path)

            for file_path in files_to_remove:
                try:
                    file_path.unlink()
                except Exception as e:
                    logger.warning(f"Could not remove {file_path}: {e}")

            logger.info(f"Cleaned up {len(files_to_remove)} files for job {job_id}")
        except Exception as e:
            logger.error(f"Error cleaning up files: {str(e)}")

    async def cleanup_temp_files(self):
        try:
            for file_path in self.temp_dir.iterdir():
                if file_path.is_file() and time.time() - file_path.stat().st_mtime > 3600:
                    try:
                        file_path.unlink()
                    except Exception as e:
                        logger.warning(f"Could not remove temp file {file_path}: {e}")
        except Exception as e:
            logger.error(f"Error cleaning temp files: {str(e)}")

    def get_job_directory(self, job_id: str) -> Path:
        return self.upload_dir / job_id

    def validate_video_file(self, filename: str, content: bytes) -> bool:
        try:
            allowed_extensions = [".mp4", ".avi", ".mov", ".mkv", ".webm"]
            if not any(filename.lower().endswith(ext) for ext in allowed_extensions):
                return False
            if len(content) > settings.max_file_size:
                return False
            return True
        except Exception as e:
            logger.error(f"Error validating video file: {str(e)}")
            return False
