"""OpenTelemetry-compatible tracing."""

import time
from contextlib import contextmanager
from typing import Any, Generator

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

from docagentline.config import get_settings


_tracer_provider: TracerProvider | None = None


def setup_tracing():
    """Setup OpenTelemetry tracing."""
    global _tracer_provider

    settings = get_settings()

    if not settings.enable_otel_tracing:
        return

    _tracer_provider = TracerProvider()

    if settings.otel_exporter_endpoint:
        exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_endpoint)
    else:
        exporter = ConsoleSpanExporter()

    _tracer_provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(_tracer_provider)


def get_tracer(name: str) -> trace.Tracer:
    """Get tracer instance."""
    return trace.get_tracer(name)


@contextmanager
def trace_span(
    tracer: trace.Tracer,
    name: str,
    attributes: dict[str, Any] | None = None,
) -> Generator[trace.Span, None, None]:
    """Create a traced span context manager."""
    settings = get_settings()

    if not settings.enable_otel_tracing:
        # No-op span
        class NoOpSpan:
            def set_attribute(self, key: str, value: Any):
                pass

            def set_status(self, status):
                pass

            def record_exception(self, exception: Exception):
                pass

        yield NoOpSpan()
        return

    with tracer.start_as_current_span(name) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        yield span
