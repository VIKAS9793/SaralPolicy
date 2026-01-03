"""
Health and status endpoints for SaralPolicy.

Provides:
- /health - Quick health check (critical dependencies only)
- /health/detailed - Full health check with all components
- /health/ready - Readiness probe for orchestrators
- /health/live - Liveness probe
- /model-info - Model information
"""

from fastapi import APIRouter
import structlog
import os

from app.services.health_service import (
    get_health_service,
    HealthStatus,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="", tags=["health"])

# Get model from environment
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "gemma2:2b")


@router.get("/health")
async def health_check():
    """
    Quick health check endpoint.
    
    Checks critical dependencies only (Ollama, Database).
    Use /health/detailed for full component status.
    
    Returns:
        Health status with component details
    """
    try:
        health_service = get_health_service()
        system_health = health_service.get_system_health(detailed=False)
        
        return system_health.to_dict()
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": None
        }


@router.get("/health/detailed")
async def detailed_health_check():
    """
    Detailed health check with all components.
    
    Checks:
    - Ollama LLM service
    - ChromaDB vector store
    - Database connectivity
    - Embedding model availability
    
    Returns:
        Full health status with all component details and latency
    """
    try:
        health_service = get_health_service()
        system_health = health_service.get_system_health(detailed=True)
        
        return system_health.to_dict()
        
    except Exception as e:
        logger.error("Detailed health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@router.get("/health/ready")
async def readiness_probe():
    """
    Kubernetes-style readiness probe.
    
    Returns 200 if service is ready to accept traffic.
    Returns 503 if service is not ready.
    """
    from fastapi.responses import JSONResponse
    
    try:
        health_service = get_health_service()
        system_health = health_service.get_system_health(detailed=False)
        
        if system_health.status == HealthStatus.UNHEALTHY:
            return JSONResponse(
                status_code=503,
                content={
                    "ready": False,
                    "status": system_health.status.value,
                    "message": "Service not ready"
                }
            )
        
        return {
            "ready": True,
            "status": system_health.status.value
        }
        
    except Exception as e:
        logger.error("Readiness probe failed", error=str(e))
        return JSONResponse(
            status_code=503,
            content={"ready": False, "error": str(e)}
        )


@router.get("/health/live")
async def liveness_probe():
    """
    Kubernetes-style liveness probe.
    
    Returns 200 if service is alive (process running).
    Does not check dependencies.
    """
    return {
        "alive": True,
        "status": "healthy"
    }


@router.get("/model-info")
async def get_model_info():
    """Get information about the loaded local model."""
    return {
        "model": OLLAMA_MODEL,
        "provider": "Ollama (local)",
        "embedding_model": "nomic-embed-text",
        "privacy": "100% local processing"
    }
