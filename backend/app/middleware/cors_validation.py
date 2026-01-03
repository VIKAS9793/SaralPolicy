"""
CORS Configuration Validation for SaralPolicy

This module provides secure CORS configuration with:
- Origin format validation
- Wildcard rejection when credentials are enabled
- Startup validation with fail-fast behavior

Per Engineering Constitution Section 1.4: Security by Default
- Validate inputs at all boundaries
- Avoid security assumptions
- Call out security risks explicitly
"""

import os
import re
from typing import List, Tuple
import structlog

logger = structlog.get_logger(__name__)

# Valid origin pattern: scheme://host[:port]
ORIGIN_PATTERN = re.compile(
    r'^https?://'  # http:// or https://
    r'[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?'  # hostname
    r'(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*'  # optional subdomains
    r'(:\d{1,5})?$'  # optional port
)


def validate_origin(origin: str) -> Tuple[bool, str]:
    """
    Validate a single origin string.
    
    Args:
        origin: Origin string to validate (e.g., "http://localhost:8000")
        
    Returns:
        Tuple of (is_valid, reason)
    """
    origin = origin.strip()
    
    if not origin:
        return False, "Empty origin"
    
    # Check for wildcard
    if origin == "*":
        return True, "Wildcard (requires special handling)"
    
    # Validate format
    if not ORIGIN_PATTERN.match(origin):
        return False, f"Invalid origin format: {origin}"
    
    return True, "Valid"


def validate_cors_config(
    origins: List[str],
    allow_credentials: bool = False
) -> Tuple[bool, List[str]]:
    """
    Validate CORS configuration for security issues.
    
    Per OWASP: Wildcard origins with credentials is a security vulnerability
    that allows credential theft via CSRF-like attacks.
    
    Args:
        origins: List of allowed origins
        allow_credentials: Whether credentials (cookies, auth headers) are allowed
        
    Returns:
        Tuple of (is_valid, list of error messages)
    """
    errors = []
    
    # Check for wildcard with credentials (CRITICAL SECURITY ISSUE)
    if allow_credentials and "*" in origins:
        errors.append(
            "SECURITY ERROR: Wildcard origin (*) with allow_credentials=True is forbidden. "
            "This combination allows any website to make authenticated requests to your API. "
            "Remove '*' from ALLOWED_ORIGINS or set allow_credentials=False."
        )
    
    # Validate each origin format
    for origin in origins:
        is_valid, reason = validate_origin(origin)
        if not is_valid:
            errors.append(f"Invalid origin '{origin}': {reason}")
    
    # Check for localhost in production
    production_mode = os.environ.get("ENVIRONMENT", "development").lower() == "production"
    if production_mode:
        localhost_origins = [o for o in origins if "localhost" in o or "127.0.0.1" in o]
        if localhost_origins:
            errors.append(
                f"SECURITY WARNING: Localhost origins in production: {localhost_origins}. "
                "Remove these for production deployment."
            )
    
    return len(errors) == 0, errors


def get_validated_origins() -> List[str]:
    """
    Get and validate CORS origins from environment.
    
    Fails fast if configuration is invalid and credentials are enabled.
    
    Returns:
        List of validated origins
        
    Raises:
        ValueError: If CORS configuration is insecure
    """
    origins_str = os.environ.get(
        "ALLOWED_ORIGINS",
        "http://localhost:8000,http://127.0.0.1:8000"
    )
    
    # Parse origins
    origins = [o.strip() for o in origins_str.split(",") if o.strip()]
    
    if not origins:
        logger.warning("No CORS origins configured, using localhost defaults")
        origins = ["http://localhost:8000", "http://127.0.0.1:8000"]
    
    # Validate configuration
    # Note: We check with credentials=True since that's our default config
    is_valid, errors = validate_cors_config(origins, allow_credentials=True)
    
    if not is_valid:
        for error in errors:
            logger.error("CORS validation failed", error=error)
        
        # Fail fast for security errors (not warnings)
        security_errors = [e for e in errors if "SECURITY ERROR" in e]
        if security_errors:
            raise ValueError(
                "CORS configuration is insecure and cannot be used. "
                f"Errors: {security_errors}"
            )
        else:
            # Log warnings but continue
            for error in errors:
                logger.warning("CORS configuration warning", warning=error)
    
    logger.info(
        "CORS origins validated",
        origins=origins,
        count=len(origins)
    )
    
    return origins


# Security documentation for CORS
CORS_SECURITY_NOTES = """
CORS Configuration Security Notes
=================================

1. NEVER use wildcard (*) with allow_credentials=True
   - This allows any website to make authenticated requests
   - Attackers can steal user sessions/data

2. Explicitly list allowed origins
   - Each origin should be a specific URL
   - Format: scheme://hostname[:port]
   - Example: http://localhost:8000, https://myapp.example.com

3. Production checklist:
   - Remove localhost/127.0.0.1 origins
   - Use HTTPS origins only
   - Set ENVIRONMENT=production

4. Environment variables:
   - ALLOWED_ORIGINS: Comma-separated list of allowed origins
   - ENVIRONMENT: Set to 'production' for production mode
"""
