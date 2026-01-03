"""
Tests for OSS Framework Integrations

Tests for:
1. RAG Evaluation Service (RAGAS-compatible)
2. Observability Service (OpenTelemetry-compatible)
3. Task Queue Service (Huey-compatible)

Per Engineering Constitution Section 1.2:
- Every non-trivial module should be testable
"""

import pytest
import time
from unittest.mock import patch, MagicMock
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
    get_task_queue_service
)


class TestRAGEvaluationService:
    """Tests for RAG evaluation service."""
    
    @pytest.fixture
    def service(self):
        """Create RAG evaluation service instance."""
        return RAGEvaluationService(ollama_model="gemma2:2b")
    
    def test_service_initialization(self, service):
        """Test service initializes correctly."""
        assert service is not None
        assert service.ollama_model == "gemma2:2b"
        assert service.faithfulness_threshold == 0.7
    
    def test_heuristic_evaluation_grounded_response(self, service):
        """Test heuristic evaluation with grounded response."""
        question = "What is the sum insured?"
        answer = "The sum insured is Rs 5,00,000 as stated in the policy document."
        contexts = [
            "Policy Details: Sum Insured Rs 5,00,000. Premium Rs 12,000 annually.",
            "Coverage includes hospitalization and surgery expenses."
        ]
        
        result = service.evaluate_rag_response(question, answer, contexts)
        
        assert isinstance(result, RAGEvaluationResult)
        assert result.faithfulness_score > 0
        assert result.answer_relevancy_score > 0
        assert result.evaluation_method in ["ragas", "heuristic"]
    
    def test_heuristic_evaluation_hallucinated_response(self, service):
        """Test heuristic evaluation detects potential hallucination."""
        question = "What is covered?"
        answer = "This policy includes dental coverage, vision care, and international travel insurance with no waiting period."
        contexts = [
            "Basic health insurance policy covering hospitalization.",
            "Standard exclusions apply."
        ]
        
        result = service.evaluate_rag_response(question, answer, contexts)
        
        assert isinstance(result, RAGEvaluationResult)
        # Low faithfulness indicates potential hallucination
        assert result.faithfulness_score < 0.5 or result.is_hallucination_risk
    
    def test_empty_contexts_handling(self, service):
        """Test handling of empty contexts."""
        result = service.evaluate_rag_response(
            question="What is covered?",
            answer="The policy covers hospitalization.",
            contexts=[]
        )
        
        assert isinstance(result, RAGEvaluationResult)
        assert result.context_precision_score == 0.0
    
    def test_batch_evaluate(self, service):
        """Test batch evaluation."""
        evaluations = [
            {
                "question": "What is the premium?",
                "answer": "Premium is Rs 12,000.",
                "contexts": ["Premium: Rs 12,000 per year."]
            },
            {
                "question": "What is excluded?",
                "answer": "Cosmetic surgery is excluded.",
                "contexts": ["Exclusions: Cosmetic procedures."]
            }
        ]
        
        results = service.batch_evaluate(evaluations)
        
        assert len(results) == 2
        assert all(isinstance(r, RAGEvaluationResult) for r in results)
    
    def test_evaluation_summary(self, service):
        """Test evaluation summary generation."""
        results = [
            RAGEvaluationResult(
                faithfulness_score=0.8,
                answer_relevancy_score=0.7,
                context_precision_score=0.6,
                context_recall_score=0.0,
                overall_score=0.7,
                is_hallucination_risk=False,
                evaluation_method="heuristic",
                details={}
            ),
            RAGEvaluationResult(
                faithfulness_score=0.5,
                answer_relevancy_score=0.6,
                context_precision_score=0.4,
                context_recall_score=0.0,
                overall_score=0.5,
                is_hallucination_risk=True,
                evaluation_method="heuristic",
                details={}
            )
        ]
        
        summary = service.get_evaluation_summary(results)
        
        assert summary["total_evaluations"] == 2
        assert summary["hallucination_risk_count"] == 1
        assert summary["hallucination_risk_rate"] == 0.5
        assert 0.5 <= summary["average_faithfulness"] <= 0.8


class TestObservabilityService:
    """Tests for observability service."""
    
    @pytest.fixture
    def service(self):
        """Create observability service instance."""
        svc = ObservabilityService(service_name="test-service")
        svc.reset_metrics()  # Start fresh
        return svc
    
    def test_service_initialization(self, service):
        """Test service initializes correctly."""
        assert service is not None
        assert service.service_name == "test-service"
    
    def test_increment_counter(self, service):
        """Test counter increment."""
        service.increment_counter("test_counter", value=1)
        service.increment_counter("test_counter", value=2)
        
        summary = service.get_metrics_summary()
        
        # Counter should exist with value 3
        assert any("test_counter" in k for k in summary["counters"])
    
    def test_record_histogram(self, service):
        """Test histogram recording."""
        service.record_histogram("test_latency", 0.1)
        service.record_histogram("test_latency", 0.2)
        service.record_histogram("test_latency", 0.3)
        
        summary = service.get_metrics_summary()
        
        # Histogram should have statistics
        histogram_key = [k for k in summary["histograms"] if "test_latency" in k]
        assert len(histogram_key) > 0
        
        stats = summary["histograms"][histogram_key[0]]
        assert stats["count"] == 3
        assert stats["min"] == 0.1
        assert stats["max"] == 0.3
    
    def test_trace_span(self, service):
        """Test trace span context manager."""
        with service.trace_span("test_operation", {"key": "value"}):
            time.sleep(0.01)  # Simulate work
        
        summary = service.get_metrics_summary()
        
        # Should have recorded span
        assert len(summary["recent_spans"]) > 0
        span = summary["recent_spans"][-1]
        assert span["name"] == "test_operation"
        assert span["status"] == "ok"
        assert span["duration_ms"] > 0
    
    def test_trace_span_error(self, service):
        """Test trace span records errors."""
        try:
            with service.trace_span("failing_operation"):
                raise ValueError("Test error")
        except ValueError:
            pass
        
        summary = service.get_metrics_summary()
        
        # Should have recorded error span
        span = summary["recent_spans"][-1]
        assert span["name"] == "failing_operation"
        assert span["status"] == "error"
    
    def test_track_request(self, service):
        """Test HTTP request tracking."""
        service.track_request("GET", "/api/test", 200, 0.05)
        service.track_request("POST", "/api/test", 500, 0.1)
        
        health = service.get_health_metrics()
        
        assert health["total_requests"] == 2
        assert health["total_errors"] == 1
        assert health["error_rate"] == 0.5
    
    def test_track_llm_call(self, service):
        """Test LLM call tracking."""
        service.track_llm_call("gemma2:2b", "generate", 1.5, tokens=500)
        
        summary = service.get_metrics_summary()
        
        assert any("llm_calls_total" in k for k in summary["counters"])
        assert any("llm_tokens_total" in k for k in summary["counters"])
    
    def test_track_rag_query(self, service):
        """Test RAG query tracking."""
        service.track_rag_query("policy_docs", "hybrid", 0.3, results_count=5)
        
        summary = service.get_metrics_summary()
        
        assert any("rag_queries_total" in k for k in summary["counters"])
    
    def test_health_metrics(self, service):
        """Test health metrics calculation."""
        # Generate some traffic
        for i in range(10):
            status = 200 if i < 8 else 500
            service.track_request("GET", "/test", status, 0.05 + i * 0.01)
        
        health = service.get_health_metrics()
        
        assert health["total_requests"] == 10
        assert health["total_errors"] == 2
        assert health["error_rate"] == 0.2
        assert health["average_latency_seconds"] > 0


class TestTaskQueueService:
    """Tests for task queue service."""
    
    @pytest.fixture
    def service(self):
        """Create task queue service instance."""
        return TaskQueueService(db_path="data/test_tasks.db")
    
    def test_service_initialization(self, service):
        """Test service initializes correctly."""
        assert service is not None
        assert service.db_path == "data/test_tasks.db"
    
    def test_register_handler(self, service):
        """Test handler registration."""
        def test_handler(payload):
            return {"result": "success"}
        
        service.register_handler("test_task", test_handler)
        
        assert "test_task" in service._handlers
    
    def test_enqueue_task(self, service):
        """Test task enqueueing."""
        def test_handler(payload):
            return {"processed": True}
        
        service.register_handler("test_task", test_handler)
        
        task_id = service.enqueue(
            task_type="test_task",
            payload={"data": "test"},
            priority=TaskPriority.HIGH
        )
        
        assert task_id is not None
        
        status = service.get_task_status(task_id)
        assert status is not None
        assert status["task_type"] == "test_task"
    
    def test_task_execution(self, service):
        """Test task execution."""
        results = []
        
        def capture_handler(payload):
            results.append(payload)
            return {"captured": True}
        
        service.register_handler("capture_task", capture_handler)
        
        task_id = service.enqueue(
            task_type="capture_task",
            payload={"value": 42}
        )
        
        # In fallback mode, task executes immediately
        assert len(results) == 1
        assert results[0]["value"] == 42
        
        status = service.get_task_status(task_id)
        assert status["status"] in ["completed", "pending"]
    
    def test_get_pending_tasks(self, service):
        """Test getting pending tasks."""
        # Clear existing tasks
        service._tasks.clear()
        
        # Add tasks with different priorities
        service._tasks["task1"] = Task(
            task_id="task1",
            task_type="test",
            payload={},
            priority=TaskPriority.LOW,
            status=TaskStatus.PENDING
        )
        service._tasks["task2"] = Task(
            task_id="task2",
            task_type="test",
            payload={},
            priority=TaskPriority.HIGH,
            status=TaskStatus.PENDING
        )
        
        pending = service.get_pending_tasks()
        
        assert len(pending) == 2
        # High priority should be first
        assert pending[0]["priority"] == "high"
    
    def test_queue_stats(self, service):
        """Test queue statistics."""
        service._tasks.clear()
        
        service._tasks["task1"] = Task(
            task_id="task1",
            task_type="test",
            payload={},
            status=TaskStatus.PENDING
        )
        service._tasks["task2"] = Task(
            task_id="task2",
            task_type="test",
            payload={},
            status=TaskStatus.COMPLETED
        )
        
        stats = service.get_queue_stats()
        
        assert stats["total_tasks"] == 2
        assert stats["status_counts"]["pending"] == 1
        assert stats["status_counts"]["completed"] == 1
    
    def test_cleanup_completed_tasks(self, service):
        """Test cleanup of old completed tasks."""
        from datetime import datetime, timedelta
        
        service._tasks.clear()
        
        # Add old completed task
        old_task = Task(
            task_id="old_task",
            task_type="test",
            payload={},
            status=TaskStatus.COMPLETED,
            completed_at=datetime.utcnow() - timedelta(hours=48)
        )
        service._tasks["old_task"] = old_task
        
        # Add recent completed task
        recent_task = Task(
            task_id="recent_task",
            task_type="test",
            payload={},
            status=TaskStatus.COMPLETED,
            completed_at=datetime.utcnow()
        )
        service._tasks["recent_task"] = recent_task
        
        cleaned = service.cleanup_completed_tasks(older_than_hours=24)
        
        assert cleaned == 1
        assert "old_task" not in service._tasks
        assert "recent_task" in service._tasks


class TestHITLTaskTypes:
    """Tests for HITL task type constants."""
    
    def test_task_types_defined(self):
        """Test all HITL task types are defined."""
        assert HITLTaskTypes.REVIEW_NOTIFICATION == "hitl_review_notification"
        assert HITLTaskTypes.EXPERT_ASSIGNMENT == "hitl_expert_assignment"
        assert HITLTaskTypes.REVIEW_REMINDER == "hitl_review_reminder"
        assert HITLTaskTypes.FEEDBACK_PROCESSING == "hitl_feedback_processing"


class TestSingletonInstances:
    """Tests for singleton service instances."""
    
    def test_rag_evaluation_singleton(self):
        """Test RAG evaluation service singleton."""
        service1 = get_rag_evaluation_service()
        service2 = get_rag_evaluation_service()
        
        assert service1 is service2
    
    def test_observability_singleton(self):
        """Test observability service singleton."""
        service1 = get_observability_service()
        service2 = get_observability_service()
        
        assert service1 is service2
    
    def test_task_queue_singleton(self):
        """Test task queue service singleton."""
        service1 = get_task_queue_service()
        service2 = get_task_queue_service()
        
        assert service1 is service2


class TestTimedDecorator:
    """Tests for the timed decorator."""
    
    def test_timed_decorator_success(self):
        """Test timed decorator on successful function."""
        observability = ObservabilityService("test")
        observability.reset_metrics()
        
        @timed(observability, "test_function")
        def test_func():
            time.sleep(0.01)
            return "success"
        
        result = test_func()
        
        assert result == "success"
        
        summary = observability.get_metrics_summary()
        assert any("test_function_total" in k for k in summary["counters"])
    
    def test_timed_decorator_error(self):
        """Test timed decorator on failing function."""
        observability = ObservabilityService("test")
        observability.reset_metrics()
        
        @timed(observability, "failing_function")
        def failing_func():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            failing_func()
        
        summary = observability.get_metrics_summary()
        assert any("failing_function_errors_total" in k for k in summary["counters"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
