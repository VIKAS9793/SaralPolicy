"""
SaralPolicy Services Module

This module exports all service classes for the SaralPolicy application.
Services are organized by function:

Core Services:
- OllamaLLMService: Local LLM integration via Ollama
- RAGService: Retrieval-Augmented Generation with ChromaDB
- PolicyService: Main policy analysis orchestration
- DocumentService: Document processing and extraction

Supporting Services:
- GuardrailsService: Input/output validation and safety
- HITLService: Human-in-the-loop review workflow
- EvaluationManager: Response quality evaluation
- TTSService: Text-to-speech for accessibility
- TranslationService: Hindi/English translation

OSS Framework Services:
- RAGEvaluationService: RAGAS-based RAG evaluation (Apache 2.0)
- ObservabilityService: OpenTelemetry metrics/tracing (Apache 2.0)
- TaskQueueService: Huey background task queue (MIT)
"""

# Core Services
from app.services.ollama_llm_service import OllamaLLMService
from app.services.rag_service import RAGService, create_rag_service
from app.services.policy_service import PolicyService
from app.services.document_service import DocumentService

# Supporting Services
from app.services.guardrails_service import GuardrailsService
from app.services.hitl_service import HITLService
from app.services.evaluation import EvaluationManager
from app.services.tts_service import TTSService
from app.services.translation_service import TranslationService

# OSS Framework Services
from app.services.rag_evaluation_service import (
    RAGEvaluationService,
    RAGEvaluationResult,
    get_rag_evaluation_service
)
from app.services.observability_service import (
    ObservabilityService,
    get_observability_service,
    timed
)
from app.services.task_queue_service import (
    TaskQueueService,
    Task,
    TaskStatus,
    TaskPriority,
    HITLTaskTypes,
    get_task_queue_service,
    setup_hitl_task_handlers
)

__all__ = [
    # Core
    "OllamaLLMService",
    "RAGService",
    "create_rag_service",
    "PolicyService",
    "DocumentService",
    # Supporting
    "GuardrailsService",
    "HITLService",
    "EvaluationManager",
    "TTSService",
    "TranslationService",
    # OSS Frameworks
    "RAGEvaluationService",
    "RAGEvaluationResult",
    "get_rag_evaluation_service",
    "ObservabilityService",
    "get_observability_service",
    "timed",
    "TaskQueueService",
    "Task",
    "TaskStatus",
    "TaskPriority",
    "HITLTaskTypes",
    "get_task_queue_service",
    "setup_hitl_task_handlers",
]
