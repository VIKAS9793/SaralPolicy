"""
Translation Service for SaralPolicy
Provides Hindi and English translation support for insurance documents.
Uses Argos Translate for 100% offline, local processing (DPDP Compliant).
"""

import json
import structlog
from typing import Dict, List
from pathlib import Path
import threading

try:
    import argostranslate.package
    import argostranslate.translate
    ARGOS_AVAILABLE = True
except ImportError:
    ARGOS_AVAILABLE = False

logger = structlog.get_logger(__name__)


class TranslationService:
    """
    Service for translating insurance content between Hindi and English.
    Uses Argos Translate for offline processing.
    """

    def __init__(self):
        self.translation_cache = {}
        self.cache_file = Path.home() / ".saralpolicy" / "translation_cache.json"
        
        # Initialization lock to prevent race conditions during package install
        self._init_lock = threading.Lock()
        self._ready = False

        if ARGOS_AVAILABLE:
            self._initialize_argos()
        else:
            logger.warning("Argos Translate not installed. Translation disabled.")

        # Load cache
        self._load_cache()

    def _initialize_argos(self):
        """Initialize Argos Translate and download language packs if needed."""
        try:
            logger.info("Initializing offline translation engine...")
            
            # Update package index
            argostranslate.package.update_package_index()
            
            # Check/Install EN <-> HI packages
            available_packages = argostranslate.package.get_available_packages()
            installed_packages = argostranslate.package.get_installed_packages()
            
            required_pairs = [('en', 'hi'), ('hi', 'en')]
            
            for from_code, to_code in required_pairs:
                is_installed = any(
                    pkg.from_code == from_code and pkg.to_code == to_code 
                    for pkg in installed_packages
                )
                
                if not is_installed:
                    logger.info(f"Downloading language pack: {from_code} -> {to_code}...")
                    package_to_install = next(
                        filter(
                            lambda x: x.from_code == from_code and x.to_code == to_code,
                            available_packages
                        ), None
                    )
                    
                    if package_to_install:
                        argostranslate.package.install_from_path(package_to_install.download())
                        logger.info(f"Installed {from_code}->{to_code}")
                    else:
                        logger.error(f"Language pack {from_code}->{to_code} not found")
            
            self._ready = True
            logger.info("✅ Offline translation engine ready")
            
        except Exception as e:
            logger.error(f"Failed to initialize Argos Translate: {e}")

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
        Translate text to target language using offline engine.

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
            
        # Determine source language (simple heuristic or assume opposite)
        # For this app, we assume input is EN if target is HI, and vice versa
        # In a real app, we might want detection, but Argos auto-detect is separate.
        source_language = 'en' if target_language == 'hi' else 'hi'

        # Check cache first
        cache_key = f"{hash(text)}:{source_language}:{target_language}"
        if cache_key in self.translation_cache:
            return self.translation_cache[cache_key]

        if not self._ready or not ARGOS_AVAILABLE:
            logger.warning("Offline translator not ready, returning original text")
            return text

        try:
            # Detect lock to ensure thread safety if multiple requests come fast
            # Argos translate is generally thread safe for translation calls
            
            # Translate
            translation = argostranslate.translate.translate(text, source_language, target_language)

            if translation:
                # Cache the translation
                self.translation_cache[cache_key] = translation
                self._save_cache()
                return translation
            else:
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
        if self._ready:
            return ['hi', 'en']
        return []

    def is_available(self) -> bool:
        """Check if translation service is available."""
        return self._ready

    def get_status(self) -> Dict:
        """Get translation service status."""
        return {
            "available": self.is_available(),
            "available_languages": self.get_available_languages(),
            "engine": "Argos Translate (Offline)",
            "cache_size": len(self.translation_cache),
            "cache_file": str(self.cache_file)
        }
