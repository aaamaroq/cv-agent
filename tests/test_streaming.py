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
from cv_chat.config import Settings, get_settings  # noqa: E402


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

    def fake_check(_llm, _q, _a, _src):
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


class MessageWindowTests(unittest.TestCase):

    def test_long_history_is_trimmed_and_turn_still_works(self):
        settings = Settings(
            model="fake", guardrail_model="fake", api_key="",
            temperature=0.0, max_threads=32, history_window=4, llm_timeout_s=60,
        )
        with stubbed(rejects=0), \
             mock.patch.object(streaming, "get_settings", return_value=settings):
            g = graph_mod.build_graph(settings)
            tid = "t-window"
            # run 5 turns; with window=4 the state should stay bounded
            for i in range(5):
                events = _collect(g, f"question-{i}", tid)
                self.assertEqual(events[-1], {"done": True})
            persisted = g.get_state({"configurable": {"thread_id": tid}})
            msgs = persisted.values["messages"]
            # window keeps last 4 messages before the turn; +2 (Human + AI)
            # added by the current turn = max 6
            self.assertLessEqual(len(msgs), 6)
            # oldest surviving messages are from recent turns, not turn 0
            self.assertNotIn("question-0", str(msgs[0].content))


class AstreamTests(unittest.TestCase):

    def test_astream_turn_matches_sync_output(self):
        with stubbed(rejects=0):
            g = graph_mod.build_graph(get_settings())
            events = asyncio.run(
                streaming.astream_turn(g, "Kafka", "t-async").__anext__(),
            ) if False else []  # collect all
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


class ThreadLRUTests(unittest.TestCase):

    def test_eviction_removes_checkpointer_state(self):
        with stubbed(rejects=0):
            g = graph_mod.build_graph(get_settings())
            # replace module limiter with cap=1
            old = streaming._thread_lru
            streaming._thread_lru = streaming.ThreadLRU(1)
            try:
                _collect(g, "first", "t-evict-1")
                _collect(g, "second", "t-evict-2")
                # t-evict-1 should have been evicted
                state1 = g.get_state({"configurable": {"thread_id": "t-evict-1"}})
                self.assertFalse(state1.values.get("messages"))
            finally:
                streaming._thread_lru = old


class HealthEndpointTests(unittest.TestCase):

    def test_health_contains_expected_fields(self):
        from fastapi.testclient import TestClient
        from cv_chat.server import app

        client = TestClient(app)
        resp = client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("api_key_configured", body)
        self.assertIn("cv_present", body)
        self.assertIn("project_notes_present", body)
        self.assertIn("model", body)
        self.assertIn("guardrail_model", body)
        self.assertTrue(body["cv_present"])
        self.assertTrue(body["project_notes_present"])
        self.assertIsInstance(body["api_key_configured"], bool)
        # key value itself must never leak
        self.assertNotIn("OPENROUTER_API_KEY", resp.text)


if __name__ == "__main__":
    unittest.main()