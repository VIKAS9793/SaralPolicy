"""
TTS (Text-to-Speech) endpoints for SaralPolicy.
"""

import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import structlog

from app.services.tts_service import TTSService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/tts", tags=["tts"])

# Initialize service
tts_service = TTSService()


@router.post("/speak")
async def speak_text(request: dict):
    """Convert text to speech (server-side playback)."""
    try:
        text = request.get("text", "")
        language = request.get("language", "en")

        if not text.strip():
            raise HTTPException(status_code=400, detail="Text is required")

        if language not in ["en", "hi"]:
            raise HTTPException(status_code=400, detail="Language must be 'en' or 'hi'")

        success = tts_service.speak_text(text, language)

        if success:
            return {"status": "success", "message": "Text spoken successfully"}
        else:
            raise HTTPException(status_code=500, detail="TTS failed")

    except HTTPException:
        raise
    except Exception as e:
        logger.error("TTS endpoint error", error=str(e))
        raise HTTPException(status_code=500, detail="Text-to-speech failed. Please try again.")


@router.get("/status")
async def get_tts_status():
    """Get TTS service status and available languages."""
    return tts_service.get_status()


@router.post("/generate")
async def generate_tts_audio(request: dict):
    """Generate TTS audio file and return URL for browser playback."""
    try:
        from app.dependencies import GlobalServices
        
        text = request.get("text", "")
        language = request.get("language", "en")

        if not text.strip():
            raise HTTPException(status_code=400, detail="Text is required")

        if language not in ["en", "hi"]:
            raise HTTPException(status_code=400, detail="Language must be 'en' or 'hi'")

        # CRITICAL FIX: Translate to Hindi if requested
        if language == "hi" and GlobalServices.translation_service:
            try:
                translated = GlobalServices.translation_service.translate_text(text, target_language="hi")
                logger.info(f"Hindi translation: {text[:30]}... → {translated[:30]}...")
                text = translated
            except Exception as e:
                logger.warning(f"Translation failed: {e}")

        audio_file = tts_service.generate_audio_file(text, language)

        if not audio_file:
            raise HTTPException(status_code=500, detail="TTS generation failed")

        filename = os.path.basename(audio_file)
        return {
            "status": "success",
            "audio_url": f"/tts/audio/{filename}",
            "message": "Audio generated successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("TTS generate endpoint error", error=str(e))
        raise HTTPException(status_code=500, detail="Audio generation failed. Please try again.")


@router.get("/audio/{filename}")
async def serve_tts_audio(filename: str):
    """Serve generated TTS audio files."""
    try:
        audio_path = tts_service.get_audio_file_path(filename)
        if audio_path:
            media_type = "audio/mpeg" if filename.lower().endswith(".mp3") else "audio/wav"
            return FileResponse(audio_path, media_type=media_type)
        else:
            raise HTTPException(status_code=404, detail="Audio file not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("TTS audio serve error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to serve audio file.")
