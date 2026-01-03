"""
Observability Service for SaralPolicy
Uses OpenTelemetry for metrics, tracing, and logging.

OpenTelemetry is the industry-standard observability framework (Apache 2.0).
GitHub: https://github.com/open-telemetry/opentelemetry-python (1.5k+ stars)

Per Engineering Constitution Section 2.4:
- Define how correctness is evaluated
- Define how failures are surfaced

This service provides:
1. Metrics - Request counts, latencies, error rates
2. Tracing - Distributed tracing for request flows
3. Health metrics - Service health indicators

Note: Can export to console/file (local) or Prometheus/Jaeger (production).
No cloud dependency required.
"""

import os
import time
from typing import Dict, Any, Optional, Callable
from functools import wraps
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)

# Check if OpenTelemetry is available
OTEL_AVAILABLE = False
try:
    from opentelemetry import trace, metrics
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor
    from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader
    OTEL_AVAILABLE = True
    logger.info("OpenTelemetry available")
except ImportError:
    logger.warning(
        "OpenTelemetry not installed. Install with: pip install opentelemetry-api opentelemetry-sdk",
        fallback="Using built-in metrics collection"
    )


@dataclass
class MetricPoint:
    """A single metric data point."""
    name: str
    value: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class SpanData:
    """A single trace span."""
    name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: float = 0.0
    status: str = "ok"
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: list = field(default_factory=list)


class ObservabilityService:
    """
    Service for application observability.
    
    Features:
    - Request metrics (count, latency, errors)
    - Service health metrics
    - Distributed tracing (when OTEL available)
    - Local export (console/file) - no cloud required
    
    Fallback: If OpenTelemetry is not installed, uses built-in metrics collection.
    """
    
    def __init__(self, service_name: str = "saralpolicy"):
        """
        Initialize observability service.
        
        Args:
            service_name: Name of the service for metrics/traces
        """
        self.service_name = service_name
        self.otel_available = OTEL_AVAILABLE
        
        # Built-in metrics storage (fallback)
        self._metrics: Dict[str, list] = {}
        self._spans: list = []
        self._counters: Dict[str, int] = {}
        self._histograms: Dict[str, list] = {}
        
        # Initialize OpenTelemetry if available
        if self.otel_available:
            self._setup_otel()
        
        logger.info(
            "Observability service initialized",
            otel_available=self.otel_available,
            service_name=service_name
        )
    
    def _setup_otel(self):
        """Setup OpenTelemetry with console exporters (local, no cloud)."""
        try:
            # Setup tracing
            trace_provider = TracerProvider()
            
            # Console exporter for local development
            # In production, replace with Jaeger/Zipkin exporter
            console_exporter = ConsoleSpanExporter()
            trace_provider.add_span_processor(SimpleSpanProcessor(console_exporter))
            trace.set_tracer_provider(trace_provider)
            self.tracer = trace.get_tracer(self.service_name)
            
            # Setup metrics
            metric_reader = PeriodicExportingMetricReader(
                ConsoleMetricExporter(),
                export_interval_millis=60000  # Export every 60 seconds
            )
            meter_provider = MeterProvider(metric_readers=[metric_reader])
            metrics.set_meter_provider(meter_provider)
            self.meter = metrics.get_meter(self.service_name)
            
            # Create standard metrics
            self.request_counter = self.meter.create_counter(
                "http_requests_total",
                description="Total HTTP requests"
            )
            self.request_duration = self.meter.create_histogram(
                "http_request_duration_seconds",
                description="HTTP request duration in seconds"
            )
            self.error_counter = self.meter.create_counter(
                "errors_total",
                description="Total errors"
            )
            
            logger.info("OpenTelemetry configured with console exporters")
            
        except Exception as e:
            logger.error("Failed to setup OpenTelemetry", error=str(e))
            self.otel_available = False
    
    def increment_counter(self, name: str, value: int = 1, labels: Optional[Dict[str, str]] = None):
        """
        Increment a counter metric.
        
        Args:
            name: Counter name
            value: Value to increment by
            labels: Optional labels/tags
        """
        labels = labels or {}
        
        if self.otel_available and hasattr(self, 'meter'):
            try:
                counter = self.meter.create_counter(name)
                counter.add(value, labels)
            except Exception as e:
                logger.error("OTEL counter increment failed", error=str(e))
        
        # Always update built-in counter (for fallback and local access)
        key = f"{name}:{str(labels)}"
        self._counters[key] = self._counters.get(key, 0) + value
    
    def record_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """
        Record a histogram value (e.g., latency).
        
        Args:
            name: Histogram name
            value: Value to record
            labels: Optional labels/tags
        """
        labels = labels or {}
        
        if self.otel_available and hasattr(self, 'meter'):
            try:
                histogram = self.meter.create_histogram(name)
                histogram.record(value, labels)
            except Exception as e:
                logger.error("OTEL histogram record failed", error=str(e))
        
        # Always update built-in histogram
        key = f"{name}:{str(labels)}"
        if key not in self._histograms:
            self._histograms[key] = []
        self._histograms[key].append(value)
        
        # Keep only last 1000 values to prevent memory growth
        if len(self._histograms[key]) > 1000:
            self._histograms[key] = self._histograms[key][-1000:]
    
    @contextmanager
    def trace_span(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """
        Context manager for tracing a span.
        
        Args:
            name: Span name
            attributes: Optional span attributes
            
        Usage:
            with observability.trace_span("process_document", {"doc_id": "123"}):
                # ... processing code ...
        """
        attributes = attributes or {}
        start_time = datetime.utcnow()
        span_data = SpanData(name=name, start_time=start_time, attributes=attributes)
        
        if self.otel_available and hasattr(self, 'tracer'):
            with self.tracer.start_as_current_span(name) as span:
                for key, value in attributes.items():
                    span.set_attribute(key, str(value))
                try:
                    yield span
                    span_data.status = "ok"
                except Exception as e:
                    span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                    span_data.status = "error"
                    span_data.events.append({"error": str(e)})
                    raise
                finally:
                    span_data.end_time = datetime.utcnow()
                    span_data.duration_ms = (span_data.end_time - start_time).total_seconds() * 1000
                    self._spans.append(span_data)
        else:
            # Fallback: just track timing
            try:
                yield None
                span_data.status = "ok"
            except Exception as e:
                span_data.status = "error"
                span_data.events.append({"error": str(e)})
                raise
            finally:
                span_data.end_time = datetime.utcnow()
                span_data.duration_ms = (span_data.end_time - start_time).total_seconds() * 1000
                self._spans.append(span_data)
    
    def track_request(self, method: str, path: str, status_code: int, duration_seconds: float):
        """
        Track an HTTP request.
        
        Args:
            method: HTTP method
            path: Request path
            status_code: Response status code
            duration_seconds: Request duration in seconds
        """
        labels = {"method": method, "path": path, "status": str(status_code)}
        
        self.increment_counter("http_requests_total", labels=labels)
        self.record_histogram("http_request_duration_seconds", duration_seconds, labels=labels)
        
        if status_code >= 400:
            self.increment_counter("http_errors_total", labels=labels)
    
    def track_llm_call(self, model: str, operation: str, duration_seconds: float, tokens: int = 0):
        """
        Track an LLM API call.
        
        Args:
            model: Model name
            operation: Operation type (generate, embed, etc.)
            duration_seconds: Call duration
            tokens: Number of tokens processed
        """
        labels = {"model": model, "operation": operation}
        
        self.increment_counter("llm_calls_total", labels=labels)
        self.record_histogram("llm_call_duration_seconds", duration_seconds, labels=labels)
        
        if tokens > 0:
            self.increment_counter("llm_tokens_total", value=tokens, labels=labels)
    
    def track_rag_query(self, collection: str, query_type: str, duration_seconds: float, results_count: int):
        """
        Track a RAG query.
        
        Args:
            collection: Collection name
            query_type: Query type (hybrid, vector, bm25)
            duration_seconds: Query duration
            results_count: Number of results returned
        """
        labels = {"collection": collection, "query_type": query_type}
        
        self.increment_counter("rag_queries_total", labels=labels)
        self.record_histogram("rag_query_duration_seconds", duration_seconds, labels=labels)
        self.record_histogram("rag_results_count", float(results_count), labels=labels)
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get summary of all collected metrics.
        
        Returns:
            Dict with metrics summary
        """
        summary = {
            "counters": dict(self._counters),
            "histograms": {},
            "recent_spans": []
        }
        
        # Calculate histogram statistics
        for key, values in self._histograms.items():
            if values:
                sorted_values = sorted(values)
                summary["histograms"][key] = {
                    "count": len(values),
                    "min": min(values),
                    "max": max(values),
                    "avg": sum(values) / len(values),
                    "p50": sorted_values[len(sorted_values) // 2],
                    "p95": sorted_values[int(len(sorted_values) * 0.95)] if len(sorted_values) > 1 else sorted_values[0],
                    "p99": sorted_values[int(len(sorted_values) * 0.99)] if len(sorted_values) > 1 else sorted_values[0]
                }
        
        # Get recent spans
        recent_spans = self._spans[-10:] if self._spans else []
        summary["recent_spans"] = [
            {
                "name": s.name,
                "duration_ms": s.duration_ms,
                "status": s.status,
                "start_time": s.start_time.isoformat() if s.start_time else None
            }
            for s in recent_spans
        ]
        
        return summary
    
    def get_health_metrics(self) -> Dict[str, Any]:
        """
        Get health-related metrics.
        
        Returns:
            Dict with health metrics
        """
        # Calculate error rate
        total_requests = sum(v for k, v in self._counters.items() if "http_requests_total" in k)
        total_errors = sum(v for k, v in self._counters.items() if "http_errors_total" in k)
        error_rate = total_errors / total_requests if total_requests > 0 else 0.0
        
        # Calculate average latency
        latency_values = []
        for key, values in self._histograms.items():
            if "http_request_duration" in key:
                latency_values.extend(values)
        avg_latency = sum(latency_values) / len(latency_values) if latency_values else 0.0
        
        return {
            "total_requests": total_requests,
            "total_errors": total_errors,
            "error_rate": error_rate,
            "average_latency_seconds": avg_latency,
            "otel_enabled": self.otel_available,
            "spans_collected": len(self._spans)
        }
    
    def reset_metrics(self):
        """Reset all collected metrics (useful for testing)."""
        self._counters.clear()
        self._histograms.clear()
        self._spans.clear()


def timed(observability: ObservabilityService, operation_name: str):
    """
    Decorator to time a function and record metrics.
    
    Args:
        observability: ObservabilityService instance
        operation_name: Name for the operation
        
    Usage:
        @timed(observability, "process_document")
        def process_document(doc):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                with observability.trace_span(operation_name):
                    result = func(*args, **kwargs)
                duration = time.time() - start_time
                observability.record_histogram(f"{operation_name}_duration_seconds", duration)
                observability.increment_counter(f"{operation_name}_total")
                return result
            except Exception as e:
                duration = time.time() - start_time
                observability.record_histogram(f"{operation_name}_duration_seconds", duration)
                observability.increment_counter(f"{operation_name}_errors_total")
                raise
        return wrapper
    return decorator


# Singleton instance
_observability_service: Optional[ObservabilityService] = None


def get_observability_service() -> ObservabilityService:
    """Get or create the observability service singleton."""
    global _observability_service
    if _observability_service is None:
        service_name = os.environ.get("SERVICE_NAME", "saralpolicy")
        _observability_service = ObservabilityService(service_name=service_name)
    return _observability_service
