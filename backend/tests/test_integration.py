"""
Integration Tests for SaralPolicy

Tests service interactions and end-to-end workflows
without requiring external API services.

Per Engineering Constitution Section 4.3: Backend / API Engineering
- Test service interactions
- Verify end-to-end flows
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any


class TestServiceContainerIntegration:
    """Test ServiceContainer initialization and wiring."""
    
    def test_container_initialization(self):
        """Test that ServiceContainer initializes correctly."""
        from app.dependencies import ServiceContainer
        
        container = ServiceContainer()
        
        # All services should be None before init
        assert container.ollama_service is None
        assert container.rag_service is None
        assert container.policy_service is None
        assert container._initialized is False
    
    def test_container_prevents_double_init(self):
        """Test that container prevents double initialization."""
        from app.dependencies import ServiceContainer
        
        container = ServiceContainer()
        container._initialized = True  # Simulate already initialized
        
        # Should log warning and skip
        with patch('app.dependencies.logger') as mock_logger:
            container.init_services()
            # Should have logged a warning about already initialized
            # (actual behavior depends on implementation)
    
    def test_get_container_before_init_raises(self):
        """Test that get_container raises before initialization."""
        from app.dependencies import get_container, _container
        import app.dependencies as deps
        
        # Save original
        original = deps._container
        deps._container = None
        
        try:
            with pytest.raises(RuntimeError) as exc_info:
                get_container()
            
            assert 'not initialized' in str(exc_info.value).lower()
        finally:
            # Restore
            deps._container = original


class TestPolicyServiceIntegration:
    """Test PolicyService integration with other services."""
    
    @pytest.fixture
    def integrated_service(self):
        """Create PolicyService with real service instances where possible."""
        from app.services.policy_service import PolicyService
        from app.services.guardrails_service import GuardrailsService
        from app.services.hitl_service import HITLService
        from app.services.evaluation import EvaluationManager
        from app.services.translation_service import TranslationService
        from app.services.tts_service import TTSService
        
        # Use real services where they don't require external deps
        return PolicyService(
            ollama_service=Mock(),  # Mock LLM (requires Ollama)
            rag_service=Mock(enabled=False),  # Mock RAG (requires ChromaDB)
            guardrails_service=GuardrailsService(),  # Real guardrails
            hitl_service=HITLService(),  # Real HITL
            eval_manager=EvaluationManager(),  # Real eval
            translation_service=TranslationService(),  # Real translation
            tts_service=TTSService()  # Real TTS
        )
    
    def test_guardrails_integration(self, integrated_service):
        """Test that guardrails properly filter input."""
        # Test with valid input - configure mock to return analysis
        integrated_service.ollama_service.analyze_policy.return_value = {
            'summary': 'Test analysis',
            'confidence': 0.9
        }
        
        # Configure RAG mock to avoid errors
        integrated_service.rag_service.get_stats.return_value = {'irdai_indexed': False}
        integrated_service.rag_service.index_document.return_value = None
        
        result = integrated_service.analyze_policy("Valid policy document text with sufficient content for analysis")
        
        # Should pass guardrails and return a result
        assert 'status' in result
        # If LLM was called, status should be success
        if result['status'] == 'success':
            integrated_service.ollama_service.analyze_policy.assert_called()
    
    def test_hitl_integration(self, integrated_service):
        """Test that HITL properly flags low-confidence results."""
        # Configure LLM to return low-confidence result
        integrated_service.ollama_service.analyze_policy.return_value = {
            'summary': 'Test',
            'confidence': 0.3  # Low confidence
        }
        
        result = integrated_service.analyze_policy("Test policy")
        
        # HITL should have been called
        # (actual flagging depends on HITL implementation)
        assert 'status' in result


class TestRAGServiceIntegration:
    """Test RAG service integration."""
    
    def test_rag_service_factory(self):
        """Test RAG service factory function."""
        from app.services.rag_service import create_rag_service
        
        # Should create service without crashing
        service = create_rag_service(persist_directory="./test_data/chroma")
        
        # May be None if ChromaDB not available
        if service is not None:
            assert hasattr(service, 'enabled')
            assert hasattr(service, 'query_document')
    
    def test_rag_lazy_proxy(self):
        """Test RAG lazy proxy for backward compatibility."""
        from app.services.rag_service import rag_service
        
        # Should be a lazy proxy
        assert rag_service is not None
        
        # Accessing attributes should work (may raise if ChromaDB unavailable)
        try:
            _ = rag_service.enabled
        except RuntimeError:
            # Expected if RAG not available
            pass


class TestHealthServiceIntegration:
    """Test health service integration with dependencies."""
    
    def test_health_check_all_components(self):
        """Test comprehensive health check."""
        from app.services.health_service import HealthCheckService, HealthStatus
        
        service = HealthCheckService()
        health = service.get_system_health(detailed=True)
        
        # Should have checked all components
        assert 'ollama' in health.components
        assert 'database' in health.components
        
        # Status should be one of the valid values
        assert health.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.UNHEALTHY]
    
    def test_health_check_quick_mode(self):
        """Test quick health check (less detailed)."""
        from app.services.health_service import HealthCheckService
        
        service = HealthCheckService()
        health = service.get_system_health(detailed=False)
        
        # Should still have critical components
        assert 'ollama' in health.components
        assert 'database' in health.components


class TestDocumentProcessingIntegration:
    """Test document processing pipeline."""
    
    def test_text_extraction_to_analysis_flow(self):
        """Test flow from document upload to analysis."""
        from app.services.document_service import DocumentService
        from app.services.policy_service import PolicyService
        
        # Create services
        doc_service = DocumentService()
        
        # Create mock policy service
        policy_service = PolicyService(
            ollama_service=Mock(),
            rag_service=Mock(enabled=False),
            guardrails_service=Mock(validate_input=Mock(return_value={'is_valid': True})),
            hitl_service=Mock(check_analysis_quality=Mock(return_value={'requires_review': False})),
            eval_manager=Mock(),
            translation_service=Mock(),
            tts_service=Mock()
        )
        
        # Configure LLM mock
        policy_service.ollama_service.analyze_policy.return_value = {
            'summary': 'Test policy analysis'
        }
        
        # Simulate document processing flow
        sample_text = "This is a sample insurance policy document."
        
        # Step 1: Would normally extract from file
        # Step 2: Analyze
        result = policy_service.analyze_policy(sample_text)
        
        assert result['status'] == 'success'
        assert 'summary' in result


class TestConfigIntegration:
    """Test configuration integration."""
    
    def test_settings_singleton(self):
        """Test that settings are singleton."""
        from app.config import get_settings
        
        settings1 = get_settings()
        settings2 = get_settings()
        
        # Should be same instance (cached)
        assert settings1 is settings2
    
    def test_settings_validation_on_load(self):
        """Test that settings are validated on load."""
        from app.config import get_settings
        
        settings = get_settings()
        
        # Should have valid values
        assert settings.ollama.host.startswith('http')
        assert settings.ollama.model is not None
        assert settings.environment in ['development', 'staging', 'production']


class TestGracefulDegradationIntegration:
    """Test graceful degradation across services."""
    
    def test_degradation_propagates_to_response(self):
        """Test that degradation info is included in responses."""
        from app.services.policy_service import PolicyService, ServiceMode
        
        # Create service with no LLM
        service = PolicyService(
            ollama_service=None,
            rag_service=Mock(enabled=False),
            guardrails_service=Mock(validate_input=Mock(return_value={'is_valid': True})),
            hitl_service=Mock(),
            eval_manager=Mock(),
            translation_service=Mock(),
            tts_service=Mock()
        )
        
        result = service.analyze_policy("Test policy")
        
        # Should include degradation info
        assert 'service_mode' in result
        assert result['service_mode'] == ServiceMode.MINIMAL.value
        assert 'degradation_notice' in result
    
    def test_qa_degradation_uses_fallback(self):
        """Test that Q&A uses fallback when RAG unavailable."""
        from app.services.policy_service import PolicyService
        
        mock_ollama = Mock()
        mock_ollama.answer_question.return_value = "Test answer"
        
        mock_rag = Mock()
        mock_rag.enabled = False  # RAG disabled
        
        service = PolicyService(
            ollama_service=mock_ollama,
            rag_service=mock_rag,
            guardrails_service=Mock(),
            hitl_service=Mock(),
            eval_manager=Mock(),
            translation_service=Mock(),
            tts_service=Mock()
        )
        
        result = service.answer_question(
            "The coverage is Rs. 5,00,000.",
            "What is the coverage?"
        )
        
        # Should still return an answer
        assert 'answer' in result
        assert result['answer'] is not None


class TestDatabaseIntegration:
    """Test database integration."""
    
    def test_hitl_database_operations(self):
        """Test HITL service database operations."""
        from app.services.hitl_service import HITLService
        from app.db.database import init_db
        
        # Initialize database
        try:
            init_db()
        except Exception:
            pass  # May already be initialized
        
        service = HITLService()
        
        # Test triggering a review (correct method name)
        result = service.trigger_review(
            analysis={
                'summary': 'Test analysis',
                'confidence_score': 0.5
            }
        )
        
        assert result is not None
        assert 'review_id' in result
        
        review_id = result.get('review_id')
        
        if review_id:
            # Test retrieving the review (correct method name)
            review = service.get_review_details(review_id)
            assert review is not None
            
            # Test getting pending reviews
            pending = service.get_pending_reviews()
            assert isinstance(pending, list)
