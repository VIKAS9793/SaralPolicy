"""
Tests for configuration validation (HIGH-010).

Tests cover:
- Valid configuration acceptance
- Invalid value rejection with clear errors
- Type coercion
- Range validation
- Production mode restrictions
"""

import pytest
import os
from unittest.mock import patch

from app.config import (
    OllamaConfig,
    RateLimitConfig,
    FileLimitsConfig,
    RAGConfig,
    HITLConfig,
    DatabaseConfig,
    AppSettings,
    load_settings_from_env,
)


class TestOllamaConfig:
    """Tests for Ollama configuration."""

    def test_valid_config(self):
        config = OllamaConfig(host="http://localhost:11434", model="gemma2:2b")
        assert config.host == "http://localhost:11434"
        assert config.model == "gemma2:2b"

    def test_https_host(self):
        config = OllamaConfig(host="https://ollama.example.com")
        assert config.host == "https://ollama.example.com"

    def test_invalid_host_no_scheme(self):
        with pytest.raises(ValueError) as exc_info:
            OllamaConfig(host="localhost:11434")
        assert "must start with http://" in str(exc_info.value)

    def test_host_trailing_slash_removed(self):
        config = OllamaConfig(host="http://localhost:11434/")
        assert config.host == "http://localhost:11434"

    def test_timeout_boundaries(self):
        # Valid range
        config = OllamaConfig(timeout=60)
        assert config.timeout == 60
        
        # Below minimum
        with pytest.raises(ValueError):
            OllamaConfig(timeout=5)
        
        # Above maximum
        with pytest.raises(ValueError):
            OllamaConfig(timeout=700)


class TestRateLimitConfig:
    """Tests for rate limiting configuration."""

    def test_valid_config(self):
        config = RateLimitConfig(requests_per_minute=100)
        assert config.requests_per_minute == 100

    def test_below_minimum(self):
        with pytest.raises(ValueError):
            RateLimitConfig(requests_per_minute=0)

    def test_above_maximum(self):
        with pytest.raises(ValueError):
            RateLimitConfig(requests_per_minute=1001)


class TestFileLimitsConfig:
    """Tests for file limits configuration."""

    def test_valid_config(self):
        config = FileLimitsConfig(
            max_file_size=5 * 1024 * 1024,  # 5MB
            max_text_length=20 * 1024 * 1024,  # 20MB
        )
        assert config.max_file_size == 5 * 1024 * 1024

    def test_file_size_below_minimum(self):
        with pytest.raises(ValueError):
            FileLimitsConfig(max_file_size=100)  # Below 1KB minimum

    def test_file_size_above_maximum(self):
        with pytest.raises(ValueError):
            FileLimitsConfig(max_file_size=200 * 1024 * 1024)  # Above 100MB max


class TestHITLConfig:
    """Tests for HITL configuration."""

    def test_valid_threshold(self):
        config = HITLConfig(confidence_threshold=0.9)
        assert config.confidence_threshold == 0.9

    def test_threshold_below_zero(self):
        with pytest.raises(ValueError):
            HITLConfig(confidence_threshold=-0.1)

    def test_threshold_above_one(self):
        with pytest.raises(ValueError):
            HITLConfig(confidence_threshold=1.5)


class TestDatabaseConfig:
    """Tests for database configuration."""

    def test_sqlite_url(self):
        config = DatabaseConfig(url="sqlite:///./test.db")
        assert "sqlite" in config.url

    def test_postgres_url(self):
        config = DatabaseConfig(url="postgresql://user:pass@localhost/db")
        assert "postgresql" in config.url

    def test_invalid_url_scheme(self):
        with pytest.raises(ValueError) as exc_info:
            DatabaseConfig(url="invalid://localhost/db")
        assert "must start with" in str(exc_info.value)


class TestAppSettings:
    """Tests for main application settings."""

    def test_valid_development_settings(self):
        settings = AppSettings(
            environment="development",
            debug=True,
        )
        assert settings.environment == "development"
        assert settings.debug is True

    def test_environment_normalization(self):
        settings = AppSettings(environment="PRODUCTION", debug=False)
        assert settings.environment == "production"

    def test_invalid_environment(self):
        with pytest.raises(ValueError) as exc_info:
            AppSettings(environment="invalid")
        assert "must be one of" in str(exc_info.value)

    def test_production_debug_blocked(self):
        """Debug must be disabled in production."""
        with pytest.raises(ValueError) as exc_info:
            AppSettings(environment="production", debug=True)
        assert "Debug mode must be disabled" in str(exc_info.value)


class TestLoadSettingsFromEnv:
    """Tests for environment variable loading."""

    @patch.dict(os.environ, {
        "ENVIRONMENT": "development",
        "OLLAMA_MODEL": "gemma2:2b",
        "RATE_LIMIT_PER_MINUTE": "120",
    }, clear=False)
    def test_loads_from_environment(self):
        # Clear cache for fresh load
        import app.config as config_module
        config_module._settings_cache = None
        
        settings = load_settings_from_env()
        assert settings.environment == "development"
        assert settings.ollama.model == "gemma2:2b"
        assert settings.rate_limit.requests_per_minute == 120

    @patch.dict(os.environ, {
        "MAX_FILE_SIZE": "not_a_number",
    }, clear=False)
    def test_invalid_type_raises_error(self):
        import app.config as config_module
        config_module._settings_cache = None
        
        with pytest.raises(Exception):
            load_settings_from_env()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
