"""
Translation endpoints for SaralPolicy.
"""

from fastapi import APIRouter, HTTPException
import structlog

from app.services.translation_service import TranslationService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/translate", tags=["translation"])

# Initialize service
translation_service = TranslationService()


@router.get("/status")
async def get_translation_status():
    """Get translation service status."""
    return translation_service.get_status()


@router.post("")
async def translate_text(request: dict):
    """Translate text between Hindi and English."""
    try:
        text = request.get("text", "")
        target_language = request.get("target_language", "hi")

        if not text.strip():
            raise HTTPException(status_code=400, detail="Text is required")

        if target_language not in ["en", "hi"]:
            raise HTTPException(status_code=400, detail="Target language must be 'en' or 'hi'")

        translated_text = translation_service.translate_text(text, target_language)

        return {
            "status": "success",
            "original_text": text,
            "translated_text": translated_text,
            "target_language": target_language
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Translation endpoint error", error=str(e))
        raise HTTPException(status_code=500, detail="Translation failed. Please try again.")
