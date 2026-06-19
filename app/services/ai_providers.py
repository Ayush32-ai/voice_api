from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from app.config import settings
import logging
import json
import os
from groq import Groq

logger = logging.getLogger(__name__)

class AIProvider(ABC):
    """Abstract base class for AI service providers"""
    
    @abstractmethod
    async def process(self, *args, **kwargs) -> Dict[str, Any]:
        pass

class GroqWhisperProvider(AIProvider):
    """GROQ Whisper API for speech-to-text (faster and cheaper alternative)"""
    
    def __init__(self):
        self.client = Groq(api_key=settings.groq_api_key)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8)
    )
    async def process(self, audio_file_path: str, language: str = None) -> Dict[str, Any]:
        """Convert audio to text using GROQ Whisper"""
        try:
            with open(audio_file_path, "rb") as audio_file:
                # Use GROQ's whisper-large-v3 model
                transcription = self.client.audio.transcriptions.create(
                    file=audio_file,
                    model="whisper-large-v3",
                    language=language,
                    response_format="verbose_json"
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
                    f"{self.base_url}/models/gemini-pro:generateContent?key={self.api_key}",
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

# Provider factory
class AIProviderFactory:
    """Factory for creating AI service providers"""
    
    @staticmethod
    def get_whisper_provider(use_groq: bool = True) -> AIProvider:
        """Get Whisper provider - defaults to GROQ for better performance"""
        if use_groq:
            return GroqWhisperProvider()
        return WhisperProvider()
    
    @staticmethod
    def get_gemini_provider() -> GeminiProvider:
        return GeminiProvider()
    
    @staticmethod
    def get_elevenlabs_provider() -> ElevenLabsProvider:
        return ElevenLabsProvider()