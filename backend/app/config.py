"""
Application Configuration with Pydantic Validation

This module provides centralized, validated configuration for SaralPolicy.
All environment variables are validated at startup with clear error messages.

Per Engineering Constitution:
- Section 1.5: Production Readiness - configuration management
- Section 1.4: Security by Default - validate inputs at all boundaries
"""

import os
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings
import structlog

logger = structlog.get_logger(__name__)


class OllamaConfig(BaseModel):
    """Ollama LLM service configuration."""
    
    host: str = Field(
        default="http://localhost:11434",
        description="Ollama API endpoint URL"
    )
    model: str = Field(
        default="gemma2:2b",
        description="LLM model name for text generation"
    )
    embedding_model: str = Field(
        default="nomic-embed-text",
        description="Embedding model for RAG"
    )
    timeout: int = Field(
        default=120,
        ge=10,
        le=600,
        description="Request timeout in seconds"
    )

    @field_validator("host")
    @classmethod
    def validate_host(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError(f"Ollama host must start with http:// or https://, got: {v}")
        return v.rstrip("/")


class RateLimitConfig(BaseModel):
    """Rate limiting configuration."""
    
    requests_per_minute: int = Field(
        default=60,
        ge=1,
        le=1000,
        description="Maximum requests per minute per IP"
    )


class FileLimitsConfig(BaseModel):
    """File and text size limits."""
    
    max_file_size: int = Field(
        default=10 * 1024 * 1024,  # 10MB
        ge=1024,  # At least 1KB
        le=100 * 1024 * 1024,  # Max 100MB
        description="Maximum upload file size in bytes"
    )
    max_text_length: int = Field(
        default=30 * 1024 * 1024,  # 30MB
        ge=1024,
        le=100 * 1024 * 1024,
        description="Maximum text length for processing"
    )
    max_request_size: int = Field(
        default=10 * 1024 * 1024,  # 10MB
        ge=1024,
        le=100 * 1024 * 1024,
        description="Maximum HTTP request body size"
    )


class RAGConfig(BaseModel):
    """RAG service configuration."""
    
    max_embedding_batch_size: int = Field(
        default=1000,
        ge=10,
        le=10000,
        description="Maximum embeddings per batch"
    )
    max_chunk_text_length: int = Field(
        default=50 * 1024 * 1024,  # 50MB
        ge=1024,
        description="Maximum text length before chunking"
    )
    persist_directory: str = Field(
        default="./data/chroma",
        description="ChromaDB persistence directory"
    )


class HITLConfig(BaseModel):
    """Human-in-the-Loop configuration."""
    
    confidence_threshold: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Threshold below which human review is required"
    )
    max_pending_reviews: int = Field(
        default=100,
        ge=1,
        le=10000,
        description="Maximum pending HITL reviews"
    )


class DatabaseConfig(BaseModel):
    """Database configuration."""
    
    url: str = Field(
        default="sqlite:///./data/saralpolicy.db",
        description="Database connection URL"
    )

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        valid_prefixes = ("sqlite:///", "postgresql://", "mysql://")
        if not v.startswith(valid_prefixes):
            raise ValueError(
                f"Database URL must start with one of {valid_prefixes}, got: {v[:20]}..."
            )
        return v


class AppSettings(BaseSettings):
    """
    Main application settings.
    
    All settings are loaded from environment variables with validation.
    Invalid configuration will cause startup failure with clear error messages.
    """
    
    # Environment
    environment: str = Field(
        default="development",
        description="Deployment environment (development, staging, production)"
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode"
    )
    
    # Nested configs
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    file_limits: FileLimitsConfig = Field(default_factory=FileLimitsConfig)
    rag: RAGConfig = Field(default_factory=RAGConfig)
    hitl: HITLConfig = Field(default_factory=HITLConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    
    # CORS
    allowed_origins: List[str] = Field(
        default=["http://localhost:8000", "http://127.0.0.1:8000"],
        description="Allowed CORS origins"
    )

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        valid_envs = ("development", "staging", "production")
        v_lower = v.lower()
        if v_lower not in valid_envs:
            raise ValueError(f"Environment must be one of {valid_envs}, got: {v}")
        return v_lower

    @model_validator(mode="after")
    def validate_production_settings(self) -> "AppSettings":
        """Validate settings specific to production environment."""
        if self.environment == "production":
            if self.debug:
                raise ValueError("Debug mode must be disabled in production")
            
            # Check for localhost in allowed origins
            localhost_origins = [
                o for o in self.allowed_origins 
                if "localhost" in o or "127.0.0.1" in o
            ]
            if localhost_origins:
                logger.warning(
                    "Localhost origins configured in production",
                    origins=localhost_origins
                )
        return self

    class Config:
        env_prefix = ""  # No prefix for env vars
        env_nested_delimiter = "__"  # e.g., OLLAMA__HOST


def load_settings_from_env() -> AppSettings:
    """
    Load and validate settings from environment variables.
    
    Maps current env var names to new config structure for backward compatibility.
    
    Returns:
        Validated AppSettings instance
        
    Raises:
        ValidationError: If configuration is invalid
    """
    # Map legacy env vars to new structure
    env_mapping = {
        "OLLAMA_HOST": os.environ.get("OLLAMA_HOST", "http://localhost:11434"),
        "OLLAMA_MODEL": os.environ.get("OLLAMA_MODEL", "gemma2:2b"),
        "RATE_LIMIT_PER_MINUTE": os.environ.get("RATE_LIMIT_PER_MINUTE", "60"),
        "MAX_FILE_SIZE": os.environ.get("MAX_FILE_SIZE", str(10 * 1024 * 1024)),
        "MAX_TEXT_LENGTH": os.environ.get("MAX_TEXT_LENGTH", str(30 * 1024 * 1024)),
        "MAX_REQUEST_SIZE": os.environ.get("MAX_REQUEST_SIZE", str(10 * 1024 * 1024)),
        "MAX_EMBEDDING_BATCH_SIZE": os.environ.get("MAX_EMBEDDING_BATCH_SIZE", "1000"),
        "MAX_CHUNK_TEXT_LENGTH": os.environ.get("MAX_CHUNK_TEXT_LENGTH", str(50 * 1024 * 1024)),
        "HITL_CONFIDENCE_THRESHOLD": os.environ.get("HITL_CONFIDENCE_THRESHOLD", "0.85"),
        "MAX_PENDING_REVIEWS": os.environ.get("MAX_PENDING_REVIEWS", "100"),
        "DATABASE_URL": os.environ.get("DATABASE_URL", "sqlite:///./data/saralpolicy.db"),
        "ENVIRONMENT": os.environ.get("ENVIRONMENT", "development"),
        "DEBUG": os.environ.get("DEBUG", "false"),
        "ALLOWED_ORIGINS": os.environ.get("ALLOWED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000"),
    }
    
    try:
        settings = AppSettings(
            environment=env_mapping["ENVIRONMENT"],
            debug=env_mapping["DEBUG"].lower() in ("true", "1", "yes"),
            ollama=OllamaConfig(
                host=env_mapping["OLLAMA_HOST"],
                model=env_mapping["OLLAMA_MODEL"],
            ),
            rate_limit=RateLimitConfig(
                requests_per_minute=int(env_mapping["RATE_LIMIT_PER_MINUTE"]),
            ),
            file_limits=FileLimitsConfig(
                max_file_size=int(env_mapping["MAX_FILE_SIZE"]),
                max_text_length=int(env_mapping["MAX_TEXT_LENGTH"]),
                max_request_size=int(env_mapping["MAX_REQUEST_SIZE"]),
            ),
            rag=RAGConfig(
                max_embedding_batch_size=int(env_mapping["MAX_EMBEDDING_BATCH_SIZE"]),
                max_chunk_text_length=int(env_mapping["MAX_CHUNK_TEXT_LENGTH"]),
            ),
            hitl=HITLConfig(
                confidence_threshold=float(env_mapping["HITL_CONFIDENCE_THRESHOLD"]),
                max_pending_reviews=int(env_mapping["MAX_PENDING_REVIEWS"]),
            ),
            database=DatabaseConfig(
                url=env_mapping["DATABASE_URL"],
            ),
            allowed_origins=env_mapping["ALLOWED_ORIGINS"].split(","),
        )
        
        logger.info(
            "Configuration validated successfully",
            environment=settings.environment,
            ollama_model=settings.ollama.model,
        )
        
        return settings
        
    except Exception as e:
        logger.error("Configuration validation failed", error=str(e))
        raise


def get_settings() -> AppSettings:
    """
    Get validated application settings.
    
    This function validates settings at first call and caches the result.
    Invalid configuration will cause immediate failure with clear error.
    
    Returns:
        Validated AppSettings instance
    """
    global _settings_cache
    if _settings_cache is None:
        _settings_cache = load_settings_from_env()
    return _settings_cache


# Cache for settings singleton
_settings_cache: Optional[AppSettings] = None


# Export configuration documentation
CONFIG_DOCUMENTATION = """
SaralPolicy Configuration Environment Variables
================================================

Core Settings:
  ENVIRONMENT          - Deployment environment (development/staging/production)
  DEBUG                - Enable debug mode (true/false)

Ollama LLM:
  OLLAMA_HOST          - Ollama API URL (default: http://localhost:11434)
  OLLAMA_MODEL         - LLM model name (default: gemma2:2b)

Rate Limiting:
  RATE_LIMIT_PER_MINUTE - Max requests per IP per minute (default: 60)

File Limits:
  MAX_FILE_SIZE        - Max upload file size in bytes (default: 10MB)
  MAX_TEXT_LENGTH      - Max text length for processing (default: 30MB)
  MAX_REQUEST_SIZE     - Max HTTP request size (default: 10MB)

RAG Service:
  MAX_EMBEDDING_BATCH_SIZE - Max embeddings per batch (default: 1000)
  MAX_CHUNK_TEXT_LENGTH    - Max text before chunking (default: 50MB)

HITL:
  HITL_CONFIDENCE_THRESHOLD - Review threshold 0-1 (default: 0.85)
  MAX_PENDING_REVIEWS       - Max pending reviews (default: 100)

Database:
  DATABASE_URL         - Database connection URL (default: sqlite:///./data/saralpolicy.db)

CORS:
  ALLOWED_ORIGINS      - Comma-separated allowed origins
"""
