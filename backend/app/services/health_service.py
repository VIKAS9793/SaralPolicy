"""
Comprehensive Health Check Service for SaralPolicy

Provides detailed health status with dependency checks:
- Ollama LLM service
- ChromaDB vector store
- SQLite database

Health Levels:
- HEALTHY: All dependencies operational
- DEGRADED: Some non-critical dependencies unavailable
- UNHEALTHY: Critical dependencies unavailable

Per Engineering Constitution Section 1.5: Production Readiness
"""

import os
import time
from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import structlog
import requests

logger = structlog.get_logger(__name__)


class HealthStatus(str, Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ComponentHealth:
    """Health status for a single component."""
    name: str
    status: HealthStatus
    message: str
    latency_ms: Optional[float] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemHealth:
    """Overall system health status."""
    status: HealthStatus
    timestamp: str
    version: str
    components: Dict[str, ComponentHealth]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response."""
        return {
            "status": self.status.value,
            "timestamp": self.timestamp,
            "version": self.version,
            "components": {
                name: {
                    "status": comp.status.value,
                    "message": comp.message,
                    "latency_ms": comp.latency_ms,
                    **comp.details
                }
                for name, comp in self.components.items()
            }
        }


class HealthCheckService:
    """
    Service for comprehensive health checks.
    
    Checks all critical and non-critical dependencies and
    returns appropriate health status.
    """
    
    def __init__(
        self,
        ollama_host: str = None,
        ollama_model: str = None,
        database_url: str = None,
    ):
        self.ollama_host = ollama_host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        self.ollama_model = ollama_model or os.environ.get("OLLAMA_MODEL", "gemma2:2b")
        self.database_url = database_url or os.environ.get("DATABASE_URL", "sqlite:///./data/saralpolicy.db")
        self.version = "2.1.0"
        
        # Timeout for health checks (short to avoid blocking)
        self.timeout = 5
    
    def check_ollama(self) -> ComponentHealth:
        """
        Check Ollama LLM service health.
        
        Verifies:
        1. Ollama API is reachable
        2. Required model is available
        """
        start_time = time.time()
        
        try:
            # Check if Ollama is reachable
            response = requests.get(
                f"{self.ollama_host}/api/tags",
                timeout=self.timeout
            )
            latency_ms = (time.time() - start_time) * 1000
            
            if response.status_code != 200:
                return ComponentHealth(
                    name="ollama",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Ollama API returned status {response.status_code}",
                    latency_ms=latency_ms
                )
            
            # Check if required model is available
            models_data = response.json()
            available_models = [m.get("name", "") for m in models_data.get("models", [])]
            
            # Check for exact match or partial match (e.g., "gemma2:2b" matches "gemma2:2b")
            model_found = any(
                self.ollama_model in model or model.startswith(self.ollama_model.split(":")[0])
                for model in available_models
            )
            
            if not model_found:
                return ComponentHealth(
                    name="ollama",
                    status=HealthStatus.DEGRADED,
                    message=f"Model '{self.ollama_model}' not found. Available: {available_models[:3]}",
                    latency_ms=latency_ms,
                    details={"available_models": available_models[:5]}
                )
            
            return ComponentHealth(
                name="ollama",
                status=HealthStatus.HEALTHY,
                message=f"Ollama running with model '{self.ollama_model}'",
                latency_ms=latency_ms,
                details={
                    "model": self.ollama_model,
                    "models_count": len(available_models)
                }
            )
            
        except requests.exceptions.ConnectionError:
            return ComponentHealth(
                name="ollama",
                status=HealthStatus.UNHEALTHY,
                message=f"Cannot connect to Ollama at {self.ollama_host}. Is it running?",
                details={"host": self.ollama_host}
            )
        except requests.exceptions.Timeout:
            return ComponentHealth(
                name="ollama",
                status=HealthStatus.UNHEALTHY,
                message=f"Ollama request timed out after {self.timeout}s"
            )
        except Exception as e:
            logger.error("Ollama health check failed", error=str(e))
            return ComponentHealth(
                name="ollama",
                status=HealthStatus.UNHEALTHY,
                message=f"Ollama check failed: {str(e)}"
            )
    
    def check_chromadb(self) -> ComponentHealth:
        """
        Check ChromaDB vector store health.
        
        Verifies ChromaDB is accessible and collections can be listed.
        """
        start_time = time.time()
        
        try:
            import chromadb
            from chromadb.config import Settings
            
            # Try to connect to ChromaDB
            persist_dir = os.environ.get("CHROMA_PERSIST_DIR", "./data/chroma")
            
            client = chromadb.PersistentClient(
                path=persist_dir,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=False
                )
            )
            
            # List collections to verify it's working
            collections = client.list_collections()
            latency_ms = (time.time() - start_time) * 1000
            
            return ComponentHealth(
                name="chromadb",
                status=HealthStatus.HEALTHY,
                message=f"ChromaDB operational with {len(collections)} collections",
                latency_ms=latency_ms,
                details={
                    "collections_count": len(collections),
                    "persist_dir": persist_dir
                }
            )
            
        except ImportError:
            return ComponentHealth(
                name="chromadb",
                status=HealthStatus.DEGRADED,
                message="ChromaDB not installed. RAG features unavailable.",
                details={"hint": "pip install chromadb"}
            )
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error("ChromaDB health check failed", error=str(e))
            return ComponentHealth(
                name="chromadb",
                status=HealthStatus.DEGRADED,
                message=f"ChromaDB error: {str(e)[:100]}",
                latency_ms=latency_ms
            )
    
    def check_database(self) -> ComponentHealth:
        """
        Check database connectivity.
        
        Verifies SQLite/PostgreSQL database is accessible.
        """
        start_time = time.time()
        
        try:
            from sqlalchemy import create_engine, text
            
            engine = create_engine(self.database_url)
            
            with engine.connect() as conn:
                # Simple query to verify connection
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
            
            latency_ms = (time.time() - start_time) * 1000
            
            return ComponentHealth(
                name="database",
                status=HealthStatus.HEALTHY,
                message="Database connection successful",
                latency_ms=latency_ms,
                details={
                    "type": "sqlite" if "sqlite" in self.database_url else "postgresql"
                }
            )
            
        except ImportError:
            return ComponentHealth(
                name="database",
                status=HealthStatus.DEGRADED,
                message="SQLAlchemy not installed",
                details={"hint": "pip install sqlalchemy"}
            )
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error("Database health check failed", error=str(e))
            return ComponentHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Database error: {str(e)[:100]}",
                latency_ms=latency_ms
            )
    
    def check_embedding_model(self) -> ComponentHealth:
        """Check if embedding model is available in Ollama."""
        start_time = time.time()
        embedding_model = "nomic-embed-text"
        
        try:
            response = requests.get(
                f"{self.ollama_host}/api/tags",
                timeout=self.timeout
            )
            latency_ms = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                models_data = response.json()
                available_models = [m.get("name", "") for m in models_data.get("models", [])]
                
                if any(embedding_model in m for m in available_models):
                    return ComponentHealth(
                        name="embedding_model",
                        status=HealthStatus.HEALTHY,
                        message=f"Embedding model '{embedding_model}' available",
                        latency_ms=latency_ms
                    )
                else:
                    return ComponentHealth(
                        name="embedding_model",
                        status=HealthStatus.DEGRADED,
                        message=f"Embedding model '{embedding_model}' not found",
                        latency_ms=latency_ms,
                        details={"hint": f"Run: ollama pull {embedding_model}"}
                    )
            
            return ComponentHealth(
                name="embedding_model",
                status=HealthStatus.DEGRADED,
                message="Could not check embedding model",
                latency_ms=latency_ms
            )
            
        except Exception as e:
            return ComponentHealth(
                name="embedding_model",
                status=HealthStatus.DEGRADED,
                message=f"Embedding check failed: {str(e)[:50]}"
            )
    
    def get_system_health(self, detailed: bool = True) -> SystemHealth:
        """
        Get comprehensive system health status.
        
        Args:
            detailed: Include all component checks (slower but complete)
            
        Returns:
            SystemHealth with overall status and component details
        """
        components: Dict[str, ComponentHealth] = {}
        
        # Critical checks (always run)
        components["ollama"] = self.check_ollama()
        components["database"] = self.check_database()
        
        # Detailed checks (optional for quick health endpoint)
        if detailed:
            components["chromadb"] = self.check_chromadb()
            components["embedding_model"] = self.check_embedding_model()
        
        # Determine overall status
        statuses = [c.status for c in components.values()]
        
        if HealthStatus.UNHEALTHY in statuses:
            overall_status = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY
        
        return SystemHealth(
            status=overall_status,
            timestamp=datetime.utcnow().isoformat() + "Z",
            version=self.version,
            components=components
        )


# Singleton instance
_health_service: Optional[HealthCheckService] = None


def get_health_service() -> HealthCheckService:
    """Get or create health check service instance."""
    global _health_service
    if _health_service is None:
        _health_service = HealthCheckService()
    return _health_service
