"""
Text-to-Speech Service for SaralPolicy
Provides TTS functionality for both Hindi and English content.
"""

import os
import tempfile
import structlog
from typing import Optional
from pathlib import Path
import time

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False

try:
    from gtts import gTTS
    import pygame
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False

logger = structlog.get_logger(__name__)


class TTSService:
    """Service for text-to-speech functionality in Hindi and English."""
    
    def __init__(self):
        self.engine = None
        self.temp_dir = Path(tempfile.gettempdir()) / "saralpolicy_tts"
        self.temp_dir.mkdir(exist_ok=True)
        
        # Initialize TTS engines
        self._init_pyttsx3()
        self._init_pygame()
        
        logger.info("TTS Service initialized", 
                   pyttsx3_available=PYTTSX3_AVAILABLE,
                   gtts_available=GTTS_AVAILABLE)
    
    def _init_pyttsx3(self):
        """Initialize pyttsx3 engine for offline TTS."""
        if PYTTSX3_AVAILABLE:
            try:
                self.engine = pyttsx3.init()
                # Set properties for better quality
                self.engine.setProperty('rate', 150)  # Speed of speech
                self.engine.setProperty('volume', 0.8)  # Volume level
                logger.info("pyttsx3 engine initialized successfully")
            except Exception as e:
                logger.error("Failed to initialize pyttsx3", error=str(e))
                self.engine = None
    
    def _init_pygame(self):
        """Initialize pygame for audio playback."""
        if GTTS_AVAILABLE:
            try:
                pygame.mixer.init()
                logger.info("pygame mixer initialized successfully")
            except Exception as e:
                logger.error("Failed to initialize pygame", error=str(e))
    
    def speak_text(self, text: str, language: str = "en") -> bool:
        """
        Convert text to speech and play it.
        
        Args:
            text: Text to convert to speech
            language: Language code ('en' for English, 'hi' for Hindi)
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not text.strip():
                logger.warning("Empty text provided for TTS")
                return False
            
            # Clean text for better TTS
            clean_text = self._clean_text_for_tts(text)
            
            # Use gTTS for both languages if available (better quality)
            if GTTS_AVAILABLE:
                return self._speak_with_gtts(clean_text, language)
            elif self.engine:
                return self._speak_with_pyttsx3(clean_text)
            else:
                logger.error("No TTS engine available")
                return False
                
        except Exception as e:
            logger.error("TTS failed", error=str(e), language=language)
            return False

    def generate_audio_file(self, text: str, language: str = "en") -> Optional[str]:
        """Generate an audio file for the given text and return its path.

        Prefers gTTS (MP3). Falls back to pyttsx3 (WAV) if available.
        """
        try:
            if not text.strip():
                return None

            self._purge_old_files(max_age_sec=15 * 60)

            clean_text = self._clean_text_for_tts(text)

            if GTTS_AVAILABLE:
                try:
                    from gtts import gTTS  # ensure import
                    filename = f"tts_{language}_{int(time.time()*1000)}.mp3"
                    filepath = self.temp_dir / filename
                    tts = gTTS(text=clean_text, lang=language, slow=False)
                    tts.save(str(filepath))
                    return str(filepath)
                except Exception as e:
                    logger.error("gTTS file generation failed", error=str(e))

            if self.engine:  # Fallback offline
                try:
                    filename = f"tts_{language}_{int(time.time()*1000)}.wav"
                    filepath = self.temp_dir / filename
                    self.engine.save_to_file(clean_text, str(filepath))
                    self.engine.runAndWait()
                    return str(filepath)
                except Exception as e:
                    logger.error("pyttsx3 file generation failed", error=str(e))

            return None
        except Exception as e:
            logger.error("generate_audio_file failed", error=str(e))
            return None
    
    def _speak_with_gtts(self, text: str, language: str) -> bool:
        """Use Google TTS for speech synthesis."""
        import threading
        
        def play_audio():
            try:
                # Create TTS object
                tts = gTTS(text=text, lang=language, slow=False)
                
                # Save to temporary file
                temp_file = self.temp_dir / f"tts_{language}_{int(time.time())}.mp3"
                tts.save(str(temp_file))
                
                # Play the audio
                pygame.mixer.music.load(str(temp_file))
                pygame.mixer.music.play()
                
                # Wait for playback to complete
                while pygame.mixer.music.get_busy():
                    pygame.time.wait(100)
                
                # Clean up temporary file
                try:
                    temp_file.unlink(missing_ok=True)
                except:
                    pass
                
                logger.info("TTS completed successfully", language=language)
                
            except Exception as e:
                logger.error("gTTS playback failed", error=str(e), language=language)
        
        try:
            # Run TTS in a separate thread to avoid blocking
            thread = threading.Thread(target=play_audio, daemon=True)
            thread.start()
            return True
            
        except Exception as e:
            logger.error("gTTS failed", error=str(e), language=language)
            return False
    
    def _speak_with_pyttsx3(self, text: str) -> bool:
        """Use pyttsx3 for offline speech synthesis."""
        try:
            if not self.engine:
                return False
            
            # Set voice properties
            voices = self.engine.getProperty('voices')
            if voices:
                # Try to find a suitable voice
                for voice in voices:
                    if 'english' in voice.name.lower():
                        self.engine.setProperty('voice', voice.id)
                        break
            
            # Speak the text
            self.engine.say(text)
            self.engine.runAndWait()
            
            logger.info("pyttsx3 TTS completed successfully")
            return True
            
        except Exception as e:
            logger.error("pyttsx3 failed", error=str(e))
            return False
    
    def _clean_text_for_tts(self, text: str) -> str:
        """Clean text for better TTS output."""
        # Remove HTML tags
        import re
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove special characters that might cause issues
        text = re.sub(r'[^\w\s.,!?;:()-]', '', text)
        
        # Replace common abbreviations
        replacements = {
            'Rs.': 'Rupees',
            'Rs': 'Rupees',
            'No.': 'Number',
            'Ltd.': 'Limited',
            'Co.': 'Company',
            'Mr.': 'Mister',
            'Dr.': 'Doctor',
            'etc.': 'etcetera',
            'i.e.': 'that is',
            'e.g.': 'for example'
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        # Limit text length for TTS
        if len(text) > 500:
            text = text[:500] + "..."
        
        return text.strip()

    def get_audio_file_path(self, filename: str) -> Optional[str]:
        """Return full path for a generated audio file if it exists."""
        try:
            # Avoid path traversal
            safe_name = os.path.basename(filename)
            full_path = self.temp_dir / safe_name
            if full_path.exists():
                return str(full_path)
            return None
        except Exception:
            return None

    def _purge_old_files(self, max_age_sec: int = 900) -> None:
        """Delete temp audio files older than max_age_sec."""
        now = time.time()
        try:
            for p in self.temp_dir.glob("tts_*.*"):
                try:
                    if now - p.stat().st_mtime > max_age_sec:
                        p.unlink(missing_ok=True)
                except Exception:
                    pass
        except Exception:
            pass
    
    def get_available_languages(self) -> list:
        """Get list of available languages for TTS."""
        languages = []
        
        if GTTS_AVAILABLE:
            languages.extend(['en', 'hi'])
        
        if self.engine:
            languages.append('en_offline')
        
        return languages
    
    def is_available(self) -> bool:
        """Check if TTS is available."""
        return PYTTSX3_AVAILABLE or GTTS_AVAILABLE
    
    def get_status(self) -> dict:
        """Get TTS service status."""
        return {
            "pyttsx3_available": PYTTSX3_AVAILABLE,
            "gtts_available": GTTS_AVAILABLE,
            "engine_initialized": self.engine is not None,
            "available_languages": self.get_available_languages(),
            "temp_dir": str(self.temp_dir)
        }
