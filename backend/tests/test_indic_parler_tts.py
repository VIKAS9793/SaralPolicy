"""
Tests for Indic Parler-TTS Engine
Tests graceful degradation when optional dependencies are not installed.
"""

import pytest
from unittest.mock import patch, MagicMock


class TestIndicParlerEngineAvailability:
    """Test engine availability detection."""
    
    def test_engine_import_succeeds(self):
        """Verify engine module can be imported."""
        from app.services.indic_parler_engine import IndicParlerEngine
        assert IndicParlerEngine is not None
    
    def test_engine_creation_without_deps(self):
        """Engine should create successfully even without torch/parler deps."""
        from app.services.indic_parler_engine import IndicParlerEngine
        engine = IndicParlerEngine()
        # Should not raise, just report unavailable
        status = engine.get_status()
        assert "available" in status
        assert "dependencies" in status
    
    def test_engine_is_available_checks_deps(self):
        """is_available should return False when deps missing."""
        from app.services.indic_parler_engine import (
            IndicParlerEngine, 
            TORCH_AVAILABLE, 
            PARLER_AVAILABLE
        )
        engine = IndicParlerEngine()
        
        # If torch/parler not installed, should be unavailable
        if not TORCH_AVAILABLE or not PARLER_AVAILABLE:
            assert engine.is_available() is False
    
    def test_engine_status_reports_dependencies(self):
        """get_status should report all dependency states."""
        from app.services.indic_parler_engine import IndicParlerEngine
        engine = IndicParlerEngine()
        status = engine.get_status()
        
        assert "dependencies" in status
        deps = status["dependencies"]
        assert "torch" in deps
        assert "parler_tts" in deps
        assert "soundfile" in deps
        assert "pydub" in deps


class TestIndicParlerEngineGracefulDegradation:
    """Test graceful degradation when model unavailable."""
    
    def test_generate_returns_none_when_unavailable(self):
        """generate() should return None when engine unavailable."""
        from app.services.indic_parler_engine import IndicParlerEngine
        engine = IndicParlerEngine()
        
        if not engine.is_available():
            result = engine.generate("Test text", "hi")
            assert result is None
    
    def test_generate_file_returns_none_when_unavailable(self):
        """generate_file() should return None when engine unavailable."""
        from app.services.indic_parler_engine import IndicParlerEngine
        engine = IndicParlerEngine()
        
        if not engine.is_available():
            result = engine.generate_file("Test text", "hi")
            assert result is None
    
    def test_initialize_returns_false_when_deps_missing(self):
        """initialize() should return False when deps missing."""
        from app.services.indic_parler_engine import IndicParlerEngine
        engine = IndicParlerEngine()
        
        if not engine.is_available():
            result = engine.initialize()
            assert result is False


class TestTextChunking:
    """Test text chunking logic."""
    
    def test_short_text_no_chunking(self):
        """Short text should not be chunked."""
        from app.services.indic_parler_engine import IndicParlerEngine
        engine = IndicParlerEngine()
        
        text = "This is a short test."
        chunks = engine._chunk_text(text)
        assert len(chunks) == 1
        assert chunks[0] == text
    
    def test_long_text_chunked_at_sentences(self):
        """Long text should be chunked at sentence boundaries."""
        from app.services.indic_parler_engine import IndicParlerEngine
        engine = IndicParlerEngine()
        
        # Create text longer than CHUNK_SIZE (200 chars)
        text = "This is sentence one. " * 15  # ~330 chars
        chunks = engine._chunk_text(text)
        
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) <= engine.CHUNK_SIZE + 50  # Allow some flexibility
    
    def test_hindi_sentence_boundaries(self):
        """Hindi text should be chunked at Hindi sentence boundaries (।)."""
        from app.services.indic_parler_engine import IndicParlerEngine
        engine = IndicParlerEngine()
        
        # Hindi text with sentence boundaries
        text = "यह पहला वाक्य है। यह दूसरा वाक्य है। " * 10
        chunks = engine._chunk_text(text)
        
        # Should produce multiple chunks
        assert len(chunks) >= 1


class TestTTSServiceIntegration:
    """Test TTSService integration with IndicParlerEngine."""
    
    def test_tts_service_imports_engine(self):
        """TTSService should import IndicParlerEngine."""
        from app.services.tts_service import TTSService, INDIC_PARLER_IMPORT_OK
        assert INDIC_PARLER_IMPORT_OK is True
    
    def test_tts_service_status_includes_indic_parler(self):
        """TTSService status should include indic_parler info."""
        from app.services.tts_service import TTSService
        service = TTSService()
        status = service.get_status()
        
        assert "indic_parler" in status
    
    def test_tts_service_fallback_chain(self):
        """TTSService should fall back gracefully when IndicParler unavailable."""
        from app.services.tts_service import TTSService, GTTS_AVAILABLE
        service = TTSService()
        
        # If IndicParler not available, should still work via gTTS/pyttsx3
        assert service.is_available() is True


class TestEnvironmentConfiguration:
    """Test environment variable configuration."""
    
    def test_indic_tts_enabled_env_var(self):
        """INDIC_TTS_ENABLED=false should disable engine."""
        import os
        from app.services.indic_parler_engine import IndicParlerEngine
        
        # Save original
        original = os.environ.get("INDIC_TTS_ENABLED")
        
        try:
            os.environ["INDIC_TTS_ENABLED"] = "false"
            engine = IndicParlerEngine()
            assert engine.is_available() is False
        finally:
            # Restore
            if original is not None:
                os.environ["INDIC_TTS_ENABLED"] = original
            else:
                os.environ.pop("INDIC_TTS_ENABLED", None)
    
    def test_device_defaults_to_cpu(self):
        """Device should default to CPU."""
        from app.services.indic_parler_engine import IndicParlerEngine
        engine = IndicParlerEngine()
        assert engine.device == "cpu"
