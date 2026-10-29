"""Optional OpenTelemetry + Langfuse tracing for chat turns."""

from __future__ import annotations

import logging
from typing import Any

from opentelemetry import trace
from opentelemetry.trace import SpanKind, Status, StatusCode

from .config import Settings

logger = logging.getLogger(__name__)

_HTTP_INSTRUMENTATION_SCOPE = "cv_chat.http"
_langfuse_client: Any | None = None
_langfuse_settings: Settings | None = None


def configure_observability(settings: Settings) -> bool:
    """Initialize Langfuse once, without making tracing a startup dependency."""
    global _langfuse_client, _langfuse_settings

    if not settings.langfuse_configured:
        return False
    if _langfuse_client is not None:
        return True

    try:
        from langfuse import Langfuse
        from langfuse.span_filter import is_default_export_span

        def should_export_span(span: Any) -> bool:
            scope = getattr(span, "instrumentation_scope", None)
            return is_default_export_span(span) or (
                scope is not None and scope.name == _HTTP_INSTRUMENTATION_SCOPE
            )

        _langfuse_client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            base_url=settings.langfuse_base_url,
            should_export_span=should_export_span,
        )
        _langfuse_settings = settings
        return True
    except Exception:  # noqa: BLE001 - observability must never prevent startup
        logger.exception("Langfuse initialization failed; tracing is disabled")
        _langfuse_client = None
        _langfuse_settings = None
        return False


def langfuse_callback_handler() -> Any | None:
    """Create a per-turn callback handler when Langfuse is configured."""
    if _langfuse_client is None or _langfuse_settings is None:
        return None

    try:
        from langfuse.langchain import CallbackHandler

        return CallbackHandler(public_key=_langfuse_settings.langfuse_public_key)
    except Exception:  # noqa: BLE001 - a callback failure must not break a turn
        logger.exception("Could not create Langfuse callback; continuing untraced")
        return None


def shutdown_observability() -> None:
    """Flush buffered observations during graceful application shutdown."""
    if _langfuse_client is None:
        return
    try:
        _langfuse_client.shutdown()
    except Exception:  # noqa: BLE001 - shutdown telemetry is best-effort
        logger.exception("Langfuse shutdown failed")


class ChatRequestTracingMiddleware:
    """Create an OpenTelemetry server span around the full streamed chat request.

    This is a small pure-ASGI middleware rather than BaseHTTPMiddleware so the
    active span stays current until StreamingResponse has sent its final body
    event. Langfuse exports this scope alongside its own LLM observations.
    """

    def __init__(self, app: Any) -> None:
        self.app = app
        self.tracer = trace.get_tracer(_HTTP_INSTRUMENTATION_SCOPE)

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if (
            scope.get("type") != "http"
            or scope.get("path") != "/api/chat"
            or scope.get("method") != "POST"
            or _langfuse_client is None
        ):
            await self.app(scope, receive, send)
            return

        method = scope["method"]
        attributes = {
            "http.request.method": method,
            "http.route": "/api/chat",
            "url.path": "/api/chat",
        }
        with self.tracer.start_as_current_span(
            f"{method} /api/chat",
            kind=SpanKind.SERVER,
            attributes=attributes,
        ) as span:
            async def traced_send(message: dict) -> None:
                if message.get("type") == "http.response.start":
                    status_code = message.get("status", 500)
                    span.set_attribute("http.response.status_code", status_code)
                    if status_code >= 500:
                        span.set_status(Status(StatusCode.ERROR))
                await send(message)

            try:
                await self.app(scope, receive, traced_send)
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR))
                raise
