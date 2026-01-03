
import pytest
from app.services.translation_service import TranslationService

def test_offline_translation_initialization():
    """Verify TranslationService initializes correctly with Argos."""
    service = TranslationService()
    assert service.is_available() is True
    assert "Argos Translate (Offline)" in service.get_status()["engine"]

def test_english_to_hindi_translation():
    """Verify actual offline translation logic."""
    service = TranslationService()
    if not service.is_available():
        pytest.skip("Argos Translate not available")
    
    text = "Insurance policy"
    # We expect some Hindi output. Exact match might vary by model version, 
    # but we check it returns something different and non-empty.
    translated = service.translate_text(text, target_language="hi")
    
    assert translated != text
    assert len(translated) > 0
    print(f"Translated '{text}' to '{translated}'")

def test_cache_mechanism():
    """Verify translations are cached."""
    service = TranslationService()
    text = "Cached text"
    
    # First call
    t1 = service.translate_text(text, "hi")
    
    # Modify cache manually to prove it's read from cache on 2nd call
    # (In a real unit test we might mock, but this is an integration verification)
    cache_key = f"{hash(text)}:en:hi"
    service.translation_cache[cache_key] = "Mocked Cache"
    
    # Second call
    t2 = service.translate_text(text, "hi")
    assert t2 == "Mocked Cache"
