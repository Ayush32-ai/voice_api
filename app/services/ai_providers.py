from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import asyncio
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from app.config import settings
import logging
import json
import os
from groq import Groq

logger = logging.getLogger(__name__)

MAX_WHISPER_FILE_BYTES = 24 * 1024 * 1024

class AIProvider(ABC):
    """Abstract base class for AI service providers"""
    
    @abstractmethod
    async def process(self, *args, **kwargs) -> Dict[str, Any]:
        pass

class GroqWhisperProvider(AIProvider):
    """GROQ Whisper API for speech-to-text (faster and cheaper alternative)"""
    
    def __init__(self):
        self.client = Groq(api_key=settings.groq_api_key)

    def _validate_audio_file(self, audio_file_path: str) -> None:
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

        size = os.path.getsize(audio_file_path)
        if size == 0:
            raise ValueError("Audio file is empty after extraction")
        if size > MAX_WHISPER_FILE_BYTES:
            raise ValueError(
                f"Audio file too large for GROQ Whisper ({size} bytes, max {MAX_WHISPER_FILE_BYTES})"
            )

    def _transcribe_sync(self, audio_file_path: str, language: str | None):
        with open(audio_file_path, "rb") as audio_file:
            kwargs = {
                "file": audio_file,
                "model": "whisper-large-v3",
                "response_format": "verbose_json",
            }
            if language:
                kwargs["language"] = language
            return self.client.audio.transcriptions.create(**kwargs)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8)
    )
    async def process(self, audio_file_path: str, language: str = None) -> Dict[str, Any]:
        """Convert audio to text using GROQ Whisper"""
        try:
            if settings.groq_api_key in ("", "not-set"):
                raise ValueError("GROQ_API_KEY is not configured")

            self._validate_audio_file(audio_file_path)
            transcription = await asyncio.to_thread(
                self._transcribe_sync,
                audio_file_path,
                language,
            )
                
            logger.info(f"GROQ Whisper transcription completed for {audio_file_path}")
                
            return {
                "text": transcription.text,
                "segments": getattr(transcription, 'segments', []),
                "duration": getattr(transcription, 'duration', 0)
            }
        
        except Exception as e:
            logger.error(f"GROQ Whisper API error: {str(e)}")
            raise

class WhisperProvider(AIProvider):
    """OpenAI Whisper API for speech-to-text"""
    
    def __init__(self):
        self.api_key = settings.openai_api_key
        self.base_url = "https://api.openai.com/v1"
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def process(self, audio_file_path: str, language: str = None) -> Dict[str, Any]:
        """Convert audio to text using Whisper"""
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                with open(audio_file_path, "rb") as audio_file:
                    files = {
                        "file": (os.path.basename(audio_file_path), audio_file, "audio/mpeg"),
                        "model": (None, "whisper-1"),
                        "response_format": (None, "verbose_json")
                    }
                    
                    if language:
                        files["language"] = (None, language)
                    
                    headers = {"Authorization": f"Bearer {self.api_key}"}
                    
                    response = await client.post(
                        f"{self.base_url}/audio/transcriptions",
                        headers=headers,
                        files=files
                    )
                    response.raise_for_status()
                    
                    result = response.json()
                    logger.info(f"Whisper transcription completed for {audio_file_path}")
                    
                    return {
                        "text": result.get("text", ""),
                        "segments": result.get("segments", []),
                        "duration": result.get("duration", 0)
                    }
        
        except Exception as e:
            logger.error(f"Whisper API error: {str(e)}")
            raise

class GeminiProvider(AIProvider):
    """Google Gemini API for translation"""
    
    def __init__(self):
        self.api_key = settings.gemini_api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def process(self, text: str, source_lang: str, target_lang: str) -> Dict[str, Any]:
        """Translate text using Gemini"""
        try:
            language_map = {
                "en": "English",
                "hi": "Hindi", 
                "ta": "Tamil"
            }
            
            source_language = language_map.get(source_lang, source_lang)
            target_language = language_map.get(target_lang, target_lang)
            
            prompt = f"""Translate the following text from {source_language} to {target_language}. 
            Maintain the original tone, emotion, and timing cues. Keep the natural flow and conversational style.
            Return only the translated text without any additional commentary.

            Text to translate:
            {text}"""
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                payload = {
                    "contents": [
                        {
                            "parts": [
                                {"text": prompt}
                            ]
                        }
                    ],
                    "generationConfig": {
                        "temperature": 0.3,
                        "topK": 1,
                        "topP": 1,
                        "maxOutputTokens": 2048
                    }
                }
                
                response = await client.post(
                    f"{self.base_url}/models/gemini-1.5-flash:generateContent?key={self.api_key}",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                
                result = response.json()
                translated_text = result["candidates"][0]["content"]["parts"][0]["text"]
                
                logger.info(f"Gemini translation completed: {source_lang} -> {target_lang}")
                
                return {
                    "translated_text": translated_text.strip(),
                    "source_language": source_lang,
                    "target_language": target_lang
                }
        
        except Exception as e:
            logger.error(f"Gemini API error: {str(e)}")
            raise

class ElevenLabsProvider(AIProvider):
    """ElevenLabs API for text-to-speech"""
    
    def __init__(self):
        self.api_key = settings.elevenlabs_api_key
        self.base_url = "https://api.elevenlabs.io/v1"
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def process(self, text: str, language: str, output_path: str) -> Dict[str, Any]:
        """Convert text to speech using ElevenLabs"""
        try:
            # Voice selection based on language - Updated with better voice IDs
            voice_map = {
                "en": "21m00Tcm4TlvDq8ikWAM",  # Rachel - Natural English voice
                "hi": "pNInz6obpgDQGcFmaJgB",  # Adam - Works well for Hindi
                "ta": "ErXwobaYiN019PkySvjV"   # Antoni - Works well for Tamil
            }
            
            voice_id = voice_map.get(language, voice_map["en"])
            
            async with httpx.AsyncClient(timeout=300.0) as client:
                payload = {
                    "text": text,
                    "model_id": "eleven_multilingual_v2",
                    "voice_settings": {
                        "stability": 0.6,
                        "similarity_boost": 0.8,
                        "style": 0.4,
                        "use_speaker_boost": True
                    }
                }
                
                headers = {
                    "Accept": "audio/mpeg",
                    "Content-Type": "application/json",
                    "xi-api-key": self.api_key
                }
                
                response = await client.post(
                    f"{self.base_url}/text-to-speech/{voice_id}",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                
                # Save audio file
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(response.content)
                
                logger.info(f"ElevenLabs TTS completed: {output_path}")
                
                return {
                    "audio_file_path": output_path,
                    "voice_id": voice_id,
                    "language": language,
                    "text_length": len(text),
                    "audio_size_bytes": len(response.content)
                }
        
        except Exception as e:
            logger.error(f"ElevenLabs API error: {str(e)}")
            raise


class GoogleTranslateProvider(AIProvider):
    """Free translation via Google Translate (no API key required)."""

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8)
    )
    async def process(self, text: str, source_lang: str, target_lang: str) -> Dict[str, Any]:
        try:
            from deep_translator import GoogleTranslator

            def translate_sync() -> str:
                translator = GoogleTranslator(source=source_lang, target=target_lang)
                # deep-translator handles chunking for long text
                return translator.translate(text)

            translated_text = await asyncio.to_thread(translate_sync)
            if not translated_text:
                raise ValueError("Translation returned empty text")

            logger.info(f"Google Translate completed: {source_lang} -> {target_lang}")
            return {
                "translated_text": translated_text.strip(),
                "source_language": source_lang,
                "target_language": target_lang,
            }
        except Exception as e:
            logger.error(f"Google Translate error: {str(e)}")
            raise


class GTTSProvider(AIProvider):
    """Free text-to-speech via Google TTS (no API key required)."""

    SUPPORTED_LANGS = {"en", "hi", "ta"}
    MAX_CHARS = 4000

    async def _synthesize_chunk(self, text: str, lang: str, output_path: str) -> None:
        from gtts import gTTS

        def synthesize_sync() -> None:
            tts = gTTS(text=text, lang=lang, slow=False)
            tts.save(output_path)

        await asyncio.to_thread(synthesize_sync)

    def _split_text(self, text: str, max_chars: int) -> list[str]:
        if len(text) <= max_chars:
            return [text]

        chunks: list[str] = []
        current = ""
        for sentence in text.replace("!", ".").replace("?", ".").split("."):
            sentence = sentence.strip()
            if not sentence:
                continue
            part = f"{sentence}."
            if len(current) + len(part) <= max_chars:
                current += part
            else:
                if current:
                    chunks.append(current.strip())
                current = part
        if current:
            chunks.append(current.strip())
        return chunks or [text[:max_chars]]

    async def _concat_mp3_files(self, input_paths: list[str], output_path: str) -> None:
        import shutil
        import subprocess

        if len(input_paths) == 1:
            shutil.copy2(input_paths[0], output_path)
            return

        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            shutil.copy2(input_paths[0], output_path)
            logger.warning("ffmpeg missing; using first TTS chunk only")
            return

        list_file = output_path + ".txt"
        with open(list_file, "w", encoding="utf-8") as f:
            for path in input_paths:
                f.write(f"file '{path}'\n")

        def concat_sync() -> None:
            subprocess.run(
                [ffmpeg, "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", "-y", output_path],
                check=True,
                capture_output=True,
            )

        await asyncio.to_thread(concat_sync)
        os.remove(list_file)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8)
    )
    async def process(self, text: str, language: str, output_path: str) -> Dict[str, Any]:
        try:
            lang = language if language in self.SUPPORTED_LANGS else "en"
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

            chunks = self._split_text(text, self.MAX_CHARS)
            chunk_paths: list[str] = []

            for index, chunk in enumerate(chunks):
                chunk_path = output_path if len(chunks) == 1 else output_path.replace(".mp3", f"_chunk{index}.mp3")
                await self._synthesize_chunk(chunk, lang, chunk_path)
                chunk_paths.append(chunk_path)

            if len(chunk_paths) > 1:
                await self._concat_mp3_files(chunk_paths, output_path)
                for path in chunk_paths:
                    if path != output_path and os.path.exists(path):
                        os.remove(path)

            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                raise ValueError("gTTS produced an empty audio file")

            size = os.path.getsize(output_path)
            logger.info(f"gTTS completed: {output_path} ({size} bytes, lang={lang})")
            return {
                "audio_file_path": output_path,
                "voice_id": f"gtts-{lang}",
                "language": language,
                "text_length": len(text),
                "audio_size_bytes": size,
                "provider": "gtts",
            }
        except Exception as e:
            logger.error(f"gTTS error: {str(e)}")
            raise


class EdgeTTSProvider(AIProvider):
    """Free text-to-speech via Microsoft Edge voices (no API key required)."""

    VOICE_MAP = {
        "en": "en-US-AriaNeural",
        "hi": "hi-IN-SwaraNeural",
        "ta": "ta-IN-PallaviNeural",
    }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8)
    )
    async def process(self, text: str, language: str, output_path: str) -> Dict[str, Any]:
        try:
            import edge_tts

            voice = self.VOICE_MAP.get(language, self.VOICE_MAP["en"])
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_path)

            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                raise ValueError("Edge TTS produced an empty audio file")

            size = os.path.getsize(output_path)
            logger.info(f"Edge TTS completed: {output_path} ({size} bytes, voice={voice})")
            return {
                "audio_file_path": output_path,
                "voice_id": voice,
                "language": language,
                "text_length": len(text),
                "audio_size_bytes": size,
                "provider": "edge-tts",
            }
        except Exception as e:
            logger.error(f"Edge TTS error: {str(e)}")
            raise

# Provider factory
class AIProviderFactory:
    """Factory for creating AI service providers"""
    
    @staticmethod
    def get_whisper_provider(use_groq: bool = True) -> AIProvider:
        """Get Whisper provider - defaults to GROQ for better performance"""
        if use_groq or settings.stt_provider == "groq":
            return GroqWhisperProvider()
        return WhisperProvider()
    
    @staticmethod
    def get_translation_provider() -> AIProvider:
        if settings.translation_provider == "gemini" and settings.gemini_api_key not in ("", "not-set"):
            return GeminiProvider()
        return GoogleTranslateProvider()

    @staticmethod
    def get_tts_provider() -> AIProvider:
        if settings.tts_provider == "elevenlabs" and settings.elevenlabs_api_key not in ("", "not-set"):
            return ElevenLabsProvider()
        if settings.tts_provider == "edge":
            return EdgeTTSProvider()
        return GTTSProvider()
    
    @staticmethod
    def get_gemini_provider() -> GeminiProvider:
        return GeminiProvider()
    
    @staticmethod
    def get_elevenlabs_provider() -> ElevenLabsProvider:
        return ElevenLabsProvider()

    @staticmethod
    def get_gtts_provider() -> GTTSProvider:
        return GTTSProvider()

    @staticmethod
    def get_edge_tts_provider() -> EdgeTTSProvider:
        return EdgeTTSProvider()