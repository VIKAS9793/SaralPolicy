"""
Translation Service for SaralPolicy
Provides Hindi and English translation support for insurance documents.
"""

import os
import json
import structlog
from typing import Dict, List, Optional
from pathlib import Path

try:
    import googletrans
    from googletrans import Translator
    TRANSLATOR_AVAILABLE = True
except ImportError:
    TRANSLATOR_AVAILABLE = False

logger = structlog.get_logger(__name__)


class TranslationService:
    """Service for translating insurance content between Hindi and English."""

    def __init__(self):
        self.translator = None
        self.translation_cache = {}
        self.cache_file = Path.home() / ".saralpolicy" / "translation_cache.json"

        if TRANSLATOR_AVAILABLE:
            try:
                self.translator = Translator()
                logger.info("Translation service initialized with Google Translate")
            except Exception as e:
                logger.error("Failed to initialize translator", error=str(e))
                self.translator = None

        # Load cache
        self._load_cache()

    def _load_cache(self):
        """Load translation cache from file."""
        try:
            self.cache_file.parent.mkdir(exist_ok=True)
            if self.cache_file.exists():
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.translation_cache = json.load(f)
        except Exception as e:
            logger.error("Failed to load translation cache", error=str(e))
            self.translation_cache = {}

    def _save_cache(self):
        """Save translation cache to file."""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.translation_cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("Failed to save translation cache", error=str(e))

    def translate_text(self, text: str, target_language: str = "hi") -> str:
        """
        Translate text to target language.

        Args:
            text: Text to translate
            target_language: Target language code ('hi' for Hindi, 'en' for English)

        Returns:
            str: Translated text
        """
        if not text.strip():
            return text

        if target_language not in ['hi', 'en']:
            logger.warning("Unsupported language", language=target_language)
            return text

        # Check cache first
        cache_key = f"{hash(text)}:{target_language}"
        if cache_key in self.translation_cache:
            return self.translation_cache[cache_key]

        if not self.translator:
            logger.warning("Translator not available, returning original text")
            return text

        try:
            # Translate
            result = self.translator.translate(text, dest=target_language)

            if result and result.text:
                translated_text = result.text

                # Cache the translation
                self.translation_cache[cache_key] = translated_text
                self._save_cache()

                logger.info("Translation completed",
                          source_language=result.src,
                          target_language=target_language)
                return translated_text
            else:
                logger.error("Translation failed - no result")
                return text

        except Exception as e:
            logger.error("Translation failed", error=str(e))
            return text

    def translate_insurance_terms(self, terms: List[Dict[str, str]], target_language: str = "hi") -> List[Dict[str, str]]:
        """
        Translate insurance terms and their definitions.

        Args:
            terms: List of term dictionaries with 'term' and 'definition' keys
            target_language: Target language code

        Returns:
            List of translated term dictionaries
        """
        translated_terms = []

        for term in terms:
            translated_term = {
                'term': self.translate_text(term.get('term', ''), target_language),
                'definition': self.translate_text(term.get('definition', ''), target_language),
                'importance': term.get('importance', 'medium')
            }
            translated_terms.append(translated_term)

        return translated_terms

    def translate_exclusions(self, exclusions: List[str], target_language: str = "hi") -> List[str]:
        """
        Translate list of exclusions.

        Args:
            exclusions: List of exclusion strings
            target_language: Target language code

        Returns:
            List of translated exclusions
        """
        return [self.translate_text(exclusion, target_language) for exclusion in exclusions]

    def translate_coverage_details(self, coverage: Dict[str, str], target_language: str = "hi") -> Dict[str, str]:
        """
        Translate coverage details dictionary.

        Args:
            coverage: Dictionary of coverage details
            target_language: Target language code

        Returns:
            Dictionary with translated values
        """
        translated_coverage = {}

        for key, value in coverage.items():
            if isinstance(value, str):
                translated_coverage[key] = self.translate_text(value, target_language)
            else:
                translated_coverage[key] = value

        return translated_coverage

    def get_available_languages(self) -> List[str]:
        """Get list of available languages for translation."""
        if self.translator:
            return ['hi', 'en']
        return []

    def is_available(self) -> bool:
        """Check if translation service is available."""
        return self.translator is not None

    def get_status(self) -> Dict:
        """Get translation service status."""
        return {
            "available": self.is_available(),
            "available_languages": self.get_available_languages(),
            "cache_size": len(self.translation_cache),
            "cache_file": str(self.cache_file)
        }
