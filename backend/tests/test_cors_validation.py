"""
Tests for CORS validation module.

Tests cover:
- Origin format validation
- Wildcard with credentials rejection
- Environment variable parsing
"""

import pytest
import os
from unittest.mock import patch

from app.middleware.cors_validation import (
    validate_origin,
    validate_cors_config,
    get_validated_origins,
)


class TestValidateOrigin:
    """Tests for validate_origin function."""

    def test_valid_http_localhost(self):
        is_valid, reason = validate_origin("http://localhost:8000")
        assert is_valid
        assert reason == "Valid"

    def test_valid_https_domain(self):
        is_valid, reason = validate_origin("https://example.com")
        assert is_valid
        assert reason == "Valid"

    def test_valid_https_with_port(self):
        is_valid, reason = validate_origin("https://api.example.com:443")
        assert is_valid
        assert reason == "Valid"

    def test_valid_subdomain(self):
        is_valid, reason = validate_origin("https://app.staging.example.com")
        assert is_valid
        assert reason == "Valid"

    def test_wildcard_special_handling(self):
        is_valid, reason = validate_origin("*")
        assert is_valid
        assert "Wildcard" in reason

    def test_invalid_empty(self):
        is_valid, reason = validate_origin("")
        assert not is_valid
        assert "Empty" in reason

    def test_invalid_no_scheme(self):
        is_valid, reason = validate_origin("localhost:8000")
        assert not is_valid
        assert "Invalid" in reason

    def test_invalid_file_scheme(self):
        is_valid, reason = validate_origin("file:///path/to/file")
        assert not is_valid
        assert "Invalid" in reason


class TestValidateCorsConfig:
    """Tests for validate_cors_config function."""

    def test_valid_config_no_credentials(self):
        origins = ["http://localhost:8000", "https://example.com"]
        is_valid, errors = validate_cors_config(origins, allow_credentials=False)
        assert is_valid
        assert len(errors) == 0

    def test_valid_config_with_credentials(self):
        origins = ["http://localhost:8000", "https://example.com"]
        is_valid, errors = validate_cors_config(origins, allow_credentials=True)
        assert is_valid
        assert len(errors) == 0

    def test_wildcard_without_credentials_ok(self):
        """Wildcard is OK when credentials are disabled."""
        origins = ["*"]
        is_valid, errors = validate_cors_config(origins, allow_credentials=False)
        assert is_valid
        assert len(errors) == 0

    def test_wildcard_with_credentials_blocked(self):
        """CRITICAL: Wildcard with credentials must be blocked."""
        origins = ["*"]
        is_valid, errors = validate_cors_config(origins, allow_credentials=True)
        assert not is_valid
        assert len(errors) == 1
        assert "SECURITY ERROR" in errors[0]
        assert "Wildcard" in errors[0]

    def test_mixed_origins_with_wildcard_and_credentials(self):
        """Wildcard mixed with other origins + credentials = blocked."""
        origins = ["http://localhost:8000", "*", "https://example.com"]
        is_valid, errors = validate_cors_config(origins, allow_credentials=True)
        assert not is_valid
        assert any("SECURITY ERROR" in e for e in errors)

    @patch.dict(os.environ, {"ENVIRONMENT": "production"})
    def test_localhost_in_production_warning(self):
        """Localhost origins in production should generate warning."""
        origins = ["http://localhost:8000"]
        is_valid, errors = validate_cors_config(origins, allow_credentials=True)
        # Should have warning but still be valid (warning, not error)
        assert any("SECURITY WARNING" in e for e in errors)


class TestGetValidatedOrigins:
    """Tests for get_validated_origins function."""

    @patch.dict(os.environ, {"ALLOWED_ORIGINS": "http://localhost:8000,https://example.com"})
    def test_parses_env_variable(self):
        origins = get_validated_origins()
        assert "http://localhost:8000" in origins
        assert "https://example.com" in origins

    @patch.dict(os.environ, {"ALLOWED_ORIGINS": ""}, clear=True)
    def test_defaults_when_empty(self):
        # Need to also clear ENVIRONMENT to avoid production check
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}, clear=False):
            origins = get_validated_origins()
            assert len(origins) > 0
            assert "http://localhost:8000" in origins

    @patch.dict(os.environ, {"ALLOWED_ORIGINS": "*"})
    def test_wildcard_with_credentials_raises(self):
        """Wildcard with credentials (our default) should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            get_validated_origins()
        assert "insecure" in str(exc_info.value).lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
