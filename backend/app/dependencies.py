
import os
import structlog
from typing import Optional
from app.config import get_settings
from app.services.ollama_llm_service import OllamaLLMService
from app.services.rag_service import create_rag_service, RAGService
from app.services.evaluation import EvaluationManager
from app.services.hitl_service import HITLService
from app.db.database import init_db
from app.services.guardrails_service import GuardrailsService
from app.services.tts_service import TTSService
from app.services.translation_service import TranslationService
from app.services.document_service import DocumentService
from app.services.policy_service import PolicyService

# OSS Framework Services (RAGAS, OpenTelemetry, Huey)
from app.services.rag_evaluation_service import RAGEvaluationService, get_rag_evaluation_service
from app.services.observability_service import ObservabilityService, get_observability_service
from app.services.task_queue_service import TaskQueueService, get_task_queue_service

logger = structlog.get_logger(__name__)


class ServiceContainer:
    """
    Dependency Injection Container for SaralPolicy services.
    
    Design Rationale:
    -----------------
    This replaces the previous GlobalServices class-attribute pattern with
    an instance-based container that:
    
    1. Enables Testing: Services can be mocked by creating a container with
       test doubles instead of real implementations.
    
    2. Explicit Dependencies: All service dependencies are visible in __init__
       and init_services(), making the dependency graph clear.
    
    3. Lifecycle Management: Services are created once per container instance,
       with clear initialization order and error handling.
    
    4. No Import-Time Side Effects: Services are created explicitly via
       init_services(), not at module import time.
    
    Usage:
    ------
    # Production (in main.py startup):
    container = ServiceContainer()
    container.init_services()
    
    # Testing:
    container = ServiceContainer()
    container.rag_service = MockRAGService()
    container.ollama_service = MockOllamaService()
    # ... inject other mocks as needed
    
    Migration Note:
    ---------------
    GlobalServices is kept as an alias for backward compatibility.
    New code should use ServiceContainer directly.
    """
    
    def __init__(self):
        """Initialize container with None services (lazy initialization)."""
        self.ollama_service: Optional[OllamaLLMService] = None
        self.rag_service: Optional[RAGService] = None
        self.eval_manager: Optional[EvaluationManager] = None
        self.hitl_service: Optional[HITLService] = None
        self.guardrails_service: Optional[GuardrailsService] = None
        self.tts_service: Optional[TTSService] = None
        self.translation_service: Optional[TranslationService] = None
        self.document_service: Optional[DocumentService] = None
        self.policy_service: Optional[PolicyService] = None
        # OSS Framework Services
        self.rag_evaluation_service: Optional[RAGEvaluationService] = None
        self.observability_service: Optional[ObservabilityService] = None
        self.task_queue_service: Optional[TaskQueueService] = None
        self._initialized = False
    
    def init_services(self) -> None:
        """
        Initialize all services using validated configuration.
        
        Initialization Order:
        1. Database (required by HITL)
        2. Ollama LLM (validates model availability)
        3. RAG Service (via factory function)
        4. Supporting services (evaluation, guardrails, TTS, translation)
        5. Domain services (document, policy)
        
        Raises:
            ConnectionError: If Ollama is not reachable
            ValueError: If configured model is not available
        """
        if self._initialized:
            logger.warning("ServiceContainer already initialized, skipping")
            return
        
        # Get validated settings (already validated at startup)
        settings = get_settings()
        
        # 0. Initialize database (must be first)
        try:
            init_db()
            logger.info("✅ Database initialized")
        except Exception as e:
            logger.error("❌ Failed to initialize database", error=str(e))
            # Continue anyway for POC, but log error
        
        # 1. LLM Service - use validated config
        OLLAMA_MODEL = settings.ollama.model
        OLLAMA_HOST = settings.ollama.host
        
        # Validate model exists before initializing service
        self._validate_ollama_model(OLLAMA_MODEL, OLLAMA_HOST)
        
        # Initialize LLM service after validation
        try:
            self.ollama_service = OllamaLLMService(model_name=OLLAMA_MODEL)
            logger.info(f"✅ Ollama LLM Service initialized", model=OLLAMA_MODEL)
        except Exception as e:
            logger.error("❌ Failed to initialize Ollama LLM Service", error=str(e))
            self.ollama_service = None

        # 2. RAG Service - use factory function (no import-time side effects)
        self.rag_service = create_rag_service()
        if self.rag_service:
            logger.info("✅ RAG Service initialized")
        else:
            logger.warning("⚠️ RAG Service not available")
        
        # 3. Supporting Services
        self.eval_manager = EvaluationManager()
        self.hitl_service = HITLService()
        self.guardrails_service = GuardrailsService()
        self.tts_service = TTSService()
        self.translation_service = TranslationService()

        # 4. Core Domain Services
        self.document_service = DocumentService()
        self.policy_service = PolicyService(
            ollama_service=self.ollama_service,
            rag_service=self.rag_service,
            guardrails_service=self.guardrails_service,
            hitl_service=self.hitl_service,
            eval_manager=self.eval_manager,
            translation_service=self.translation_service,
            tts_service=self.tts_service
        )
        
        # 5. OSS Framework Services (RAGAS, OpenTelemetry, Huey)
        # These are optional - graceful degradation if not installed
        try:
            self.rag_evaluation_service = get_rag_evaluation_service()
            logger.info("✅ RAG Evaluation Service (RAGAS) initialized")
        except Exception as e:
            logger.warning("⚠️ RAG Evaluation Service not available", error=str(e))
            self.rag_evaluation_service = None
        
        try:
            self.observability_service = get_observability_service()
            logger.info("✅ Observability Service (OpenTelemetry) initialized")
        except Exception as e:
            logger.warning("⚠️ Observability Service not available", error=str(e))
            self.observability_service = None
        
        try:
            self.task_queue_service = get_task_queue_service()
            logger.info("✅ Task Queue Service (Huey) initialized")
        except Exception as e:
            logger.warning("⚠️ Task Queue Service not available", error=str(e))
            self.task_queue_service = None
        
        self._initialized = True
        logger.info("✅ All services initialized and wired.")
    
    def _validate_ollama_model(self, model: str, host: str) -> None:
        """
        Validate that the configured Ollama model is available.
        
        Raises:
            ConnectionError: If Ollama is not reachable
            ValueError: If model is not available
        """
        import requests
        
        try:
            response = requests.get(f"{host}/api/tags", timeout=5)
            if response.status_code == 200:
                available_models = [m['name'] for m in response.json().get('models', [])]
                if model not in available_models:
                    logger.error(
                        f"❌ Model '{model}' not found in Ollama",
                        available_models=available_models,
                        hint=f"Run: ollama pull {model}"
                    )
                    raise ValueError(
                        f"Model '{model}' not found. "
                        f"Available models: {available_models}. "
                        f"Please run: ollama pull {model}"
                    )
                logger.info(f"✅ Model '{model}' verified in Ollama")
            else:
                logger.warning("⚠️ Could not verify Ollama models (API returned non-200)")
        except requests.exceptions.RequestException as e:
            logger.error(
                "❌ Could not connect to Ollama service",
                error=str(e),
                hint=f"Ensure Ollama is running: ollama serve (host: {host})"
            )
            raise ConnectionError(
                f"Could not connect to Ollama service at {host}. "
                f"Please ensure Ollama is running (ollama serve). Error: {e}"
            )


# Global container instance - initialized in main.py startup
_container: Optional[ServiceContainer] = None


def get_container() -> ServiceContainer:
    """
    Get the global service container.
    
    Returns:
        The initialized ServiceContainer instance.
        
    Raises:
        RuntimeError: If container not initialized (init_services not called).
    """
    global _container
    if _container is None:
        raise RuntimeError(
            "ServiceContainer not initialized. "
            "Call init_services() in application startup."
        )
    return _container


def init_services() -> ServiceContainer:
    """
    Initialize the global service container.
    
    This is the main entry point called from main.py startup event.
    
    Returns:
        The initialized ServiceContainer instance.
    """
    global _container
    _container = ServiceContainer()
    _container.init_services()
    return _container


# Backward compatibility alias
# DEPRECATED: Use ServiceContainer and get_container() instead
class GlobalServices:
    """
    DEPRECATED: Backward compatibility wrapper for GlobalServices.
    
    This class provides attribute access to the global ServiceContainer
    for code that still uses GlobalServices.attribute pattern.
    
    Migration: Replace `GlobalServices.service_name` with 
    `get_container().service_name`
    """
    
    @classmethod
    def _get_attr(cls, name: str):
        """Get attribute from global container."""
        try:
            container = get_container()
            return getattr(container, name)
        except RuntimeError:
            # Container not initialized yet
            return None
    
    @property
    def ollama_service(self):
        return self._get_attr('ollama_service')
    
    @property
    def rag_service(self):
        return self._get_attr('rag_service')
    
    @property
    def eval_manager(self):
        return self._get_attr('eval_manager')
    
    @property
    def hitl_service(self):
        return self._get_attr('hitl_service')
    
    @property
    def guardrails_service(self):
        return self._get_attr('guardrails_service')
    
    @property
    def tts_service(self):
        return self._get_attr('tts_service')
    
    @property
    def translation_service(self):
        return self._get_attr('translation_service')
    
    @property
    def document_service(self):
        return self._get_attr('document_service')
    
    @property
    def policy_service(self):
        return self._get_attr('policy_service')


# Create singleton instance for backward compatibility
GlobalServices = type('GlobalServices', (), {
    'ollama_service': property(lambda self: get_container().ollama_service if _container else None),
    'rag_service': property(lambda self: get_container().rag_service if _container else None),
    'eval_manager': property(lambda self: get_container().eval_manager if _container else None),
    'hitl_service': property(lambda self: get_container().hitl_service if _container else None),
    'guardrails_service': property(lambda self: get_container().guardrails_service if _container else None),
    'tts_service': property(lambda self: get_container().tts_service if _container else None),
    'translation_service': property(lambda self: get_container().translation_service if _container else None),
    'document_service': property(lambda self: get_container().document_service if _container else None),
    'policy_service': property(lambda self: get_container().policy_service if _container else None),
    # OSS Framework Services
    'rag_evaluation_service': property(lambda self: get_container().rag_evaluation_service if _container else None),
    'observability_service': property(lambda self: get_container().observability_service if _container else None),
    'task_queue_service': property(lambda self: get_container().task_queue_service if _container else None),
})()
