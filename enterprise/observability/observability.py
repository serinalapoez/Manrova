"""
Agent Observability
======================
OpenTelemetry-compliant audit logs and end-to-end reasoning-chain traces,
per the Fortified Enterprise Fleet track requirement. Wraps an investigation
run in a trace span, with each specialist consultation and the final risk
fusion as child spans - the same shape you'd see in Cloud Trace once this
is exported to a billing-enabled project (see `_configure_exporter` below).

Falls back to console-only span logging when no OTLP exporter is
configured, so this works identically in local dev, the CLI demo, and the
free-tier deployment - the instrumentation code never changes, only where
the spans end up.
"""

from __future__ import annotations
import os
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

_console_spans: list[dict] = []


def _configure_exporter():
    """Attempts to wire a real OTLP exporter (e.g. Google Cloud Trace) if
    the environment is configured for it. Returns True if a real exporter
    is active, False if falling back to console-only logging."""
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

        provider = TracerProvider()
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

        if os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))

        trace.set_tracer_provider(provider)
        return trace.get_tracer("manrova.oow"), True
    except Exception:
        return None, False


_tracer, _otel_active = _configure_exporter()


@contextmanager
def traced_span(name: str, attributes: dict | None = None):
    """Context manager wrapping one unit of work (a specialist consultation,
    a risk fusion call, a full investigation) in a trace span. Works whether
    or not opentelemetry is installed/configured - always records locally,
    optionally also exports via OTLP.

    Usage:
        with traced_span("consult_nav_integrity", {"vessel_id": "V-001"}):
            ... do the work ...
    """
    span_id = str(uuid.uuid4())[:8]
    start = time.monotonic()
    start_ts = datetime.now(timezone.utc).isoformat()

    if _otel_active and _tracer is not None:
        with _tracer.start_as_current_span(name) as otel_span:
            if attributes:
                for k, v in attributes.items():
                    otel_span.set_attribute(k, str(v))
            yield span_id
    else:
        yield span_id

    duration_ms = round((time.monotonic() - start) * 1000, 2)
    _console_spans.append({
        "span_id": span_id,
        "name": name,
        "attributes": attributes or {},
        "started_at": start_ts,
        "duration_ms": duration_ms,
    })


def get_trace_log() -> list[dict]:
    """Returns all spans recorded this process run - the reasoning-chain
    trace a judge or auditor can inspect."""
    return list(_console_spans)
