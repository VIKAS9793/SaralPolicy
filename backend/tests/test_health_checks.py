"""
Tests for health check service (HIGH-011).

Tests cover:
- Individual component health checks
- Overall system health aggregation
- Health status levels (Healthy, Degraded, Unhealthy)
"""

import pytest
from unittest.mock import patch, MagicMock

from app.services.health_service import (
    HealthCheckService,
    HealthStatus,
    ComponentHealth,
    SystemHealth,
)


class TestComponentHealth:
    """Tests for ComponentHealth dataclass."""

    def test_healthy_component(self):
        health = ComponentHealth(
            name="test",
            status=HealthStatus.HEALTHY,
            message="All good",
            latency_ms=10.5
        )
        assert health.status == HealthStatus.HEALTHY
        assert health.latency_ms == 10.5

    def test_unhealthy_component(self):
        health = ComponentHealth(
            name="test",
            status=HealthStatus.UNHEALTHY,
            message="Failed",
            details={"error_code": 500}
        )
        assert health.status == HealthStatus.UNHEALTHY
        assert health.details["error_code"] == 500


class TestHealthCheckService:
    """Tests for HealthCheckService."""

    @pytest.fixture
    def service(self):
        return HealthCheckService(
            ollama_host="http://localhost:11434",
            ollama_model="gemma2:2b",
            database_url="sqlite:///./test.db"
        )

    def test_check_ollama_success(self, service):
        """Test successful Ollama check."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [{"name": "gemma2:2b"}, {"name": "nomic-embed-text"}]
        }
        
        with patch("requests.get", return_value=mock_response):
            health = service.check_ollama()
            assert health.status == HealthStatus.HEALTHY
            assert "gemma2:2b" in health.message

    def test_check_ollama_model_missing(self, service):
        """Test Ollama check when model is missing."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [{"name": "other-model"}]
        }
        
        with patch("requests.get", return_value=mock_response):
            health = service.check_ollama()
            assert health.status == HealthStatus.DEGRADED
            assert "not found" in health.message

    def test_check_ollama_connection_error(self, service):
        """Test Ollama check when connection fails."""
        import requests
        
        with patch("requests.get", side_effect=requests.exceptions.ConnectionError()):
            health = service.check_ollama()
            assert health.status == HealthStatus.UNHEALTHY
            assert "Cannot connect" in health.message

    def test_check_ollama_timeout(self, service):
        """Test Ollama check on timeout."""
        import requests
        
        with patch("requests.get", side_effect=requests.exceptions.Timeout()):
            health = service.check_ollama()
            assert health.status == HealthStatus.UNHEALTHY
            assert "timed out" in health.message

    def test_check_database_success(self, service):
        """Test successful database check."""
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        
        with patch("sqlalchemy.create_engine", return_value=mock_engine):
            health = service.check_database()
            assert health.status == HealthStatus.HEALTHY

    def test_check_chromadb_success(self, service):
        """Test successful ChromaDB check."""
        mock_client = MagicMock()
        mock_client.list_collections.return_value = ["collection1", "collection2"]
        
        with patch("chromadb.PersistentClient", return_value=mock_client):
            health = service.check_chromadb()
            assert health.status == HealthStatus.HEALTHY
            assert "2 collections" in health.message


class TestSystemHealth:
    """Tests for overall system health."""

    def test_to_dict(self):
        """Test SystemHealth to_dict conversion."""
        system_health = SystemHealth(
            status=HealthStatus.HEALTHY,
            timestamp="2026-01-02T00:00:00Z",
            version="2.1.0",
            components={
                "ollama": ComponentHealth(
                    name="ollama",
                    status=HealthStatus.HEALTHY,
                    message="OK",
                    latency_ms=15.0
                )
            }
        )
        
        result = system_health.to_dict()
        assert result["status"] == "healthy"
        assert result["version"] == "2.1.0"
        assert "ollama" in result["components"]
        assert result["components"]["ollama"]["latency_ms"] == 15.0


class TestHealthAggregation:
    """Tests for health status aggregation."""

    @pytest.fixture
    def service(self):
        return HealthCheckService()

    def test_all_healthy(self, service):
        """Test overall status when all components healthy."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"models": [{"name": "gemma2:2b"}]}
        
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        
        with patch("requests.get", return_value=mock_response):
            with patch("sqlalchemy.create_engine", return_value=mock_engine):
                health = service.get_system_health(detailed=False)
                assert health.status == HealthStatus.HEALTHY

    def test_one_degraded(self, service):
        """Test overall status when one component degraded."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"models": [{"name": "other-model"}]}  # Missing model
        
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        
        with patch("requests.get", return_value=mock_response):
            with patch("sqlalchemy.create_engine", return_value=mock_engine):
                health = service.get_system_health(detailed=False)
                assert health.status == HealthStatus.DEGRADED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
