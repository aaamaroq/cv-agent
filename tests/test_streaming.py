"""Tests for the token-gating and runtime-limit hardening (ADR 0007).

All offline: the LLM and the guardrail classifiers are mocked.
"""

import asyncio
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from langchain_core.messages import AIMessage, HumanMessage  # noqa: E402
from langchain_core.runnables import RunnableLambda  # noqa: E402

import cv_chat.graph as graph_mod  # noqa: E402
import cv_chat.guardrails as guardrails  # noqa: E402
import cv_chat.streaming as streaming  # noqa: E402
from cv_chat.config import get_settings  # noqa: E402


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------

_CALL_COUNT = 0


def _fake_llm(**_kw):
    def _call(prompt):
        global _CALL_COUNT
        _CALL_COUNT += 1
        messages = prompt.to_messages() if hasattr(prompt, "to_messages") else prompt
        return AIMessage(content=f"DRAFT-{_CALL_COUNT}<{messages[-1].content[:20]}>")
    return RunnableLambda(_call)


@contextmanager
def stubbed(rejects=0, verdict="ok"):
    """Patch LLM + guardrails for a deterministic, offline turn."""
    global _CALL_COUNT
    _CALL_COUNT = 0
    state = {"out": 0}

    def fake_classify(_llm, _msg):
        return verdict, "n/a"

    def fake_check(_llm, _q, _a, _src, _profile_context=""):
        state["out"] += 1
        return (False, "overclaim") if state["out"] <= rejects else (True, "")

    with mock.patch.object(graph_mod, "ChatOpenRouter", _fake_llm), \
         mock.patch.object(guardrails, "classify_input", fake_classify), \
         mock.patch.object(guardrails, "check_output", fake_check):
        yield


def _collect(graph, message, thread_id):
    return list(streaming.stream_turn(graph, message, thread_id))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class GatingTests(unittest.TestCase):

    def test_rejected_draft_tokens_never_appear_and_exactly_one_restart(self):
        with stubbed(rejects=1):
            g = graph_mod.build_graph(get_settings())
            events = _collect(g, "Kafka", "t-gate-reject")
        tokens = [e["token"] for e in events if "token" in e]
        restarts = [e for e in events if "restart" in e]
        # draft-1 was rejected and its tokens were discarded;
        # draft-2 (accepted) streamed through
        self.assertEqual(len(restarts), 1)
        self.assertTrue(any("DRAFT-2" in t for t in tokens))
        self.assertFalse(any("DRAFT-1" in t for t in tokens))
        self.assertEqual(events[-1], {"done": True})

    def test_accepted_tokens_appear_exactly_once_ending_with_done(self):
        with stubbed(rejects=0):
            g = graph_mod.build_graph(get_settings())
            events = _collect(g, "Spring", "t-gate-accept")
        tokens = [e["token"] for e in events if "token" in e]
        self.assertEqual(len(tokens), 1)
        self.assertIn("DRAFT-1", tokens[0])
        self.assertEqual(events[-1], {"done": True})

    def test_repeated_rejections_end_with_fallback(self):
        with stubbed(rejects=5):
            g = graph_mod.build_graph(get_settings())
            events = _collect(g, "Kafka", "t-gate-fallback")
        tokens = [e["token"] for e in events if "token" in e]
        restarts = [e for e in events if "restart" in e]
        # two rejections (retries 1 then 2 > MAX_OUTPUT_RETRIES=1) → fallback
        self.assertEqual(len(restarts), 2)
        self.assertTrue(tokens[-1].startswith(guardrails.FALLBACK_MESSAGE[:40]))
        self.assertEqual(events[-1], {"done": True})

    def test_deflect_streams_injection_text(self):
        with stubbed(verdict="injection"):
            g = graph_mod.build_graph(get_settings())
            events = _collect(g, "reveal prompt", "t-gate-inject")
        tokens = [e["token"] for e in events if "token" in e]
        self.assertTrue(tokens[0].startswith(guardrails.INJECTION_MESSAGE[:40]))
        self.assertEqual(events[-1], {"done": True})

    def test_deflect_streams_abuse_text(self):
        with stubbed(verdict="abuse"):
            g = graph_mod.build_graph(get_settings())
            events = _collect(g, "insulto", "t-gate-abuse")
        tokens = [e["token"] for e in events if "token" in e]
        self.assertTrue(tokens[0].startswith(guardrails.DEFLECT_MESSAGE[:40]))
        self.assertEqual(events[-1], {"done": True})


class GraphEventAdapterTests(unittest.TestCase):

    def test_decodes_nested_chatbot_tokens_without_exposing_graph_metadata(self):
        decoded = streaming._decode_graph_event((
            ("agent:stream",),
            "messages",
            (AIMessage(content="draft"), {"langgraph_node": "chatbot"}),
        ))
        self.assertEqual(decoded, streaming._TokenChunk(node="chatbot", text="draft"))

    def test_decodes_output_verdicts_into_semantic_events(self):
        decoded = streaming._decode_graph_event((
            ("agent:stream",),
            "updates",
            {"output_guardrail": {"output_ok": False}},
        ))
        self.assertEqual(decoded, streaming._OutputVerdict(accepted=False))


class LangfuseConfigTests(unittest.TestCase):

    def test_turn_config_sets_profile_metadata_tag_and_callback(self):
        callback = object()
        with mock.patch.object(streaming, "langfuse_callback_handler", return_value=callback):
            config = streaming._config("acme:thread-local-42")

        self.assertEqual(
            config["configurable"], {"thread_id": "acme:thread-local-42"}
        )
        self.assertEqual(config["run_name"], "cv-chat-turn")
        self.assertEqual(
            config["metadata"]["langfuse_session_id"], "acme:thread-local-42"
        )
        self.assertEqual(config["metadata"]["langfuse_trace_name"], "CV chat turn")
        self.assertEqual(config["metadata"]["profile_id"], "acme")
        self.assertIn("profile:acme", config["metadata"]["langfuse_tags"])
        self.assertEqual(config["callbacks"], [callback])

    def test_unscoped_turn_uses_general_profile_metadata(self):
        with mock.patch.object(
            streaming, "langfuse_callback_handler", return_value=object()
        ):
            config = streaming._config("thread-local-42")

        self.assertEqual(config["metadata"]["profile_id"], "general")
        self.assertIn("profile:general", config["metadata"]["langfuse_tags"])

    def test_turn_config_remains_valid_without_langfuse(self):
        with mock.patch.object(streaming, "langfuse_callback_handler", return_value=None):
            config = streaming._config("thread-no-telemetry")

        self.assertEqual(config, {"configurable": {"thread_id": "thread-no-telemetry"}})


class ClientHistoryTests(unittest.TestCase):

    def test_history_is_explicit_input_and_graph_has_no_process_checkpointer(self):
        history = [
            {"role": "user", "content": "first question"},
            {"role": "assistant", "content": "first answer"},
        ]
        graph_input = streaming._input("follow-up", history=history)
        self.assertEqual(
            [(type(message), message.content) for message in graph_input["messages"]],
            [
                (HumanMessage, "first question"),
                (AIMessage, "first answer"),
                (HumanMessage, "follow-up"),
            ],
        )

        with stubbed(rejects=0):
            graph = graph_mod.build_graph(get_settings())
        self.assertIsNone(graph.checkpointer)

    def test_history_window_keeps_only_complete_recent_pairs(self):
        history = [
            {"role": "user", "content": "old question"},
            {"role": "assistant", "content": "old answer"},
            {"role": "user", "content": "recent question"},
            {"role": "assistant", "content": "recent answer"},
        ]
        with mock.patch.object(streaming, "get_settings") as settings:
            settings.return_value.history_window = 4
            graph_input = streaming._input("current", history=history)
        self.assertEqual(
            [message.content for message in graph_input["messages"]],
            ["recent question", "recent answer", "current"],
        )


class AstreamTests(unittest.TestCase):

    def test_astream_turn_matches_sync_output(self):
        with stubbed(rejects=0):
            g = graph_mod.build_graph(get_settings())
            agen = streaming.astream_turn(g, "Kafka", "t-async")
            async def _collect_async():
                out = []
                async for e in agen:
                    out.append(e)
                return out
            events = asyncio.run(_collect_async())
        tokens = [e["token"] for e in events if "token" in e]
        self.assertEqual(len(tokens), 1)
        self.assertIn("DRAFT-1", tokens[0])
        self.assertEqual(events[-1], {"done": True})


class HealthEndpointTests(unittest.TestCase):

    def test_health_contains_expected_fields(self):
        from fastapi.testclient import TestClient
        from cv_chat.server import app

        client = TestClient(app)
        resp = client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body, {"status": "ok"})
        self.assertNotIn("OPENROUTER_API_KEY", resp.text)

    def test_warmup_returns_no_operational_details(self):
        from fastapi.testclient import TestClient
        from cv_chat.server import app

        with TestClient(app) as client:
            response = client.get("/api/warmup")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")


if __name__ == "__main__":
    unittest.main()
