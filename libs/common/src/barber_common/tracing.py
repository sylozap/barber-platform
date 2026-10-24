"""OpenTelemetry tracing across HTTP and Kafka, switched by ``OTLP_ENABLED``.

The outbox stores the ``traceparent`` of the write; the relay's ``publish`` span links to
it, and the consumer continues it, so one trace covers request to handler. Tracers are
looked up per span because tests install a provider per test.
"""

from __future__ import annotations

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan, Span, SpanProcessor, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter
from opentelemetry.semconv.resource import ResourceAttributes
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from sqlalchemy.ext.asyncio import AsyncEngine

from barber_common.config import BaseAppSettings
from barber_common.logging import get_logger

__all__ = [
    "TRACEPARENT_HEADER",
    "OrphanDatabaseSpanFilter",
    "configure_tracing",
    "context_of",
    "current_traceparent",
    "extract_trace_context",
    "inject_trace_context",
    "instrument_engine",
    "instrument_fastapi",
    "links_to",
]

TRACEPARENT_HEADER = "traceparent"

# Both spellings: the attribute was renamed by the database semantic
# conventions, and the instrumentation emits either, depending on opt-in.
_DATABASE_SYSTEM_ATTRIBUTES = ("db.system", "db.system.name")

_logger = get_logger(__name__)
_propagator = TraceContextTextMapPropagator()


def configure_tracing(
    settings: BaseAppSettings,
    *,
    span_exporter: SpanExporter | None = None,
) -> None:
    """Install the tracer provider of the process.

    ``span_exporter`` replaces the OTLP exporter; tests pass an in-memory one.
    When tracing is disabled and no exporter is given, nothing is installed and
    the no-op provider of the API stays in place.
    """
    if span_exporter is None and not settings.otlp_enabled:
        _logger.info("tracing is disabled", otlp_enabled=False)
        return

    exporter = span_exporter
    if exporter is None:
        if settings.otlp_endpoint is None:
            raise ValueError("OTLP_ENABLED is set but OTLP_ENDPOINT is empty")
        exporter = OTLPSpanExporter(endpoint=settings.otlp_endpoint)

    resource = Resource.create(
        {
            ResourceAttributes.SERVICE_NAME: settings.service_name,
            ResourceAttributes.DEPLOYMENT_ENVIRONMENT: settings.environment.value,
        }
    )
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(OrphanDatabaseSpanFilter(BatchSpanProcessor(exporter)))
    trace.set_tracer_provider(provider)

    # The outgoing side of every synchronous call between services.
    HTTPXClientInstrumentor().instrument(tracer_provider=provider)
    _instrument_redis(provider)

    _logger.info("tracing is enabled", otlp_endpoint=settings.otlp_endpoint)


class OrphanDatabaseSpanFilter(SpanProcessor):
    """Drops database spans that have no parent.

    The relay and delivery worker poll every second; without this each poll would be its own
    trace in Tempo. Done at export because the sampler runs before the span is named.
    """

    def __init__(self, delegate: SpanProcessor) -> None:
        self._delegate = delegate

    def on_start(self, span: Span, parent_context: Context | None = None) -> None:
        self._delegate.on_start(span, parent_context=parent_context)

    def on_end(self, span: ReadableSpan) -> None:
        if span.parent is None and _is_database_span(span):
            return
        self._delegate.on_end(span)

    def shutdown(self) -> None:
        self._delegate.shutdown()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return self._delegate.force_flush(timeout_millis)


def _is_database_span(span: ReadableSpan) -> bool:
    attributes = span.attributes or {}
    return any(name in attributes for name in _DATABASE_SYSTEM_ATTRIBUTES)


def _instrument_redis(provider: TracerProvider) -> None:
    """Instrument Redis if the instrumentation package is installed."""
    try:
        from opentelemetry.instrumentation.redis import RedisInstrumentor
    except ImportError:
        return
    RedisInstrumentor().instrument(tracer_provider=provider)


def instrument_fastapi(app: FastAPI) -> None:
    """Create a server span for every request handled by this application."""
    FastAPIInstrumentor.instrument_app(
        app,
        excluded_urls="/health/live,/health/ready,/metrics",
    )


def instrument_engine(engine: AsyncEngine) -> None:
    """Create a span for every statement the service sends to its database."""
    SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)


def inject_trace_context(carrier: dict[str, str]) -> dict[str, str]:
    """Write the current span into a carrier, W3C style.

    Used for Kafka headers, so a trace continues on the other side of the
    broker instead of starting again from the consumer.
    """
    _propagator.inject(carrier)
    return carrier


def extract_trace_context(carrier: dict[str, str]) -> Context:
    """Read a span context out of a carrier, for use as the parent of a span."""
    return _propagator.extract(carrier)


def current_traceparent() -> str | None:
    """The ``traceparent`` of the current span, or nothing while tracing is off.

    Stored with a row that is picked up later, outside the current trace: an
    outbox record, a queued notification.
    """
    return inject_trace_context({}).get(TRACEPARENT_HEADER)


def context_of(traceparent: str | None) -> Context:
    """A context whose span is the one ``traceparent`` names.

    Empty when there is none, which makes a span started in it a root.
    """
    if traceparent is None:
        return Context()
    return extract_trace_context({TRACEPARENT_HEADER: traceparent})


def links_to(traceparent: str | None) -> list[trace.Link]:
    """A link to the span ``traceparent`` names, for a span that is not its child."""
    span_context = trace.get_current_span(context_of(traceparent)).get_span_context()
    if not span_context.is_valid:
        return []
    return [trace.Link(span_context)]
