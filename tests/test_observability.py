"""Offline tests for the optional HTTP tracing middleware."""

import asyncio
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import cv_chat.observability as observability  # noqa: E402


class _Span:
    def __init__(self):
        self.active = False
        self.attributes = {}
        self.status = None
        self.exceptions = []

    def __enter__(self):
        self.active = True
        return self

    def __exit__(self, *_args):
        self.active = False

    def set_attribute(self, key, value):
        self.attributes[key] = value

    def set_status(self, status):
        self.status = status

    def record_exception(self, exception):
        self.exceptions.append(exception)


class _Tracer:
    def __init__(self, span):
        self.span = span
        self.arguments = None

    def start_as_current_span(self, *args, **kwargs):
        self.arguments = (args, kwargs)
        return self.span


class HttpTracingMiddlewareTests(unittest.TestCase):

    def test_chat_span_stays_active_while_sse_body_is_sent(self):
        span = _Span()
        tracer = _Tracer(span)
        sent = []

        async def app(_scope, _receive, send):
            self.assertTrue(span.active)
            await send({"type": "http.response.start", "status": 200, "headers": []})
            self.assertTrue(span.active)
            await send({"type": "http.response.body", "body": b"data", "more_body": False})

        async def send(message):
            sent.append(message)

        scope = {"type": "http", "path": "/api/chat", "method": "POST"}
        with mock.patch.object(observability, "_langfuse_client", object()), \
             mock.patch.object(observability.trace, "get_tracer", return_value=tracer):
            middleware = observability.ChatRequestTracingMiddleware(app)
            asyncio.run(middleware(scope, None, send))

        self.assertFalse(span.active)
        self.assertEqual(span.attributes["http.response.status_code"], 200)
        self.assertEqual(sent[-1]["type"], "http.response.body")
        self.assertEqual(tracer.arguments[0], ("POST /api/chat",))
        self.assertEqual(tracer.arguments[1]["kind"], observability.SpanKind.SERVER)

    def test_unconfigured_chat_bypasses_tracing(self):
        called = []

        async def app(_scope, _receive, send):
            called.append(True)
            await send({"type": "http.response.start", "status": 200, "headers": []})

        async def send(_message):
            pass

        scope = {"type": "http", "path": "/api/chat", "method": "POST"}
        with mock.patch.object(observability, "_langfuse_client", None), \
             mock.patch.object(observability.trace, "get_tracer") as get_tracer:
            middleware = observability.ChatRequestTracingMiddleware(app)
            asyncio.run(middleware(scope, None, send))

        self.assertEqual(called, [True])
        get_tracer.assert_called_once_with(observability._HTTP_INSTRUMENTATION_SCOPE)


if __name__ == "__main__":
    unittest.main()
