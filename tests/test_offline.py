"""Offline safety net for the load-bearing pieces.

These exercise pure logic only — no network, no LLM provider. Run with the src
layout the app uses:

    PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
"""

import importlib.util
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cv_chat import guardrails, prompts  # noqa: E402


class FakeLLM:
    """Stand-in for ChatOpenRouter: returns canned content or raises."""

    def __init__(self, content=None, error=None):
        self._content = content
        self._error = error

    def invoke(self, *_args, **_kwargs):
        if self._error:
            raise self._error
        return SimpleNamespace(content=self._content)


class ExtractJsonTests(unittest.TestCase):
    def test_plain_object(self):
        self.assertEqual(guardrails.extract_json('{"ok": true}'), {"ok": True})

    def test_fenced_object(self):
        self.assertEqual(
            guardrails.extract_json('```json\n{"verdict": "ok", "neutral_question": "x"}\n```'),
            {"verdict": "ok", "neutral_question": "x"},
        )

    def test_prose_wrapped_object(self):
        self.assertEqual(
            guardrails.extract_json('Sure! {"verdict": "abuse", "neutral_question": ""} done'),
            {"verdict": "abuse", "neutral_question": ""},
        )

    def test_garbage_returns_none(self):
        self.assertIsNone(guardrails.extract_json("no object here"))

    def test_non_dict_returns_none(self):
        self.assertIsNone(guardrails.extract_json("[1, 2, 3]"))


class CheckOutputTests(unittest.TestCase):
    def test_propagates_rejection(self):
        llm = FakeLLM('{"ok": false, "reason": "overclaim: PhD"}')
        self.assertEqual(
            guardrails.check_output(llm, "q", "a", "src"),
            (False, "overclaim: PhD"),
        )

    def test_propagates_acceptance(self):
        llm = FakeLLM('{"ok": true, "reason": ""}')
        self.assertEqual(guardrails.check_output(llm, "q", "a", "src"), (True, ""))

    def test_fail_open_on_llm_error(self):
        llm = FakeLLM(error=RuntimeError("provider down"))
        self.assertEqual(guardrails.check_output(llm, "q", "a", "src"), (True, ""))

    def test_fail_open_on_unparseable(self):
        llm = FakeLLM("definitely not json")
        self.assertEqual(guardrails.check_output(llm, "q", "a", "src"), (True, ""))

    def test_fail_open_on_missing_ok_field(self):
        llm = FakeLLM('{"reason": "no ok key"}')
        self.assertEqual(guardrails.check_output(llm, "q", "a", "src"), (True, ""))


class ClassifyInputTests(unittest.TestCase):
    def test_ok_passes_verbatim(self):
        llm = FakeLLM('{"verdict": "ok", "neutral_question": "ignored"}')
        self.assertEqual(guardrails.classify_input(llm, "¿Qué sabe de Kafka?"),
                         ("ok", "¿Qué sabe de Kafka?"))

    def test_loaded_returns_neutral(self):
        llm = FakeLLM('{"verdict": "loaded", "neutral_question": "¿Es adecuado? "}')
        self.assertEqual(guardrails.classify_input(llm, "hostil"),
                         ("loaded", "¿Es adecuado?"))

    def test_abuse_and_injection_drop_question(self):
        for verdict in ("abuse", "injection"):
            llm = FakeLLM('{"verdict": "%s", "neutral_question": "x"}' % verdict)
            self.assertEqual(guardrails.classify_input(llm, "x"), (verdict, ""))

    def test_unknown_verdict_fails_open(self):
        llm = FakeLLM('{"verdict": "bogus", "neutral_question": ""}')
        self.assertEqual(guardrails.classify_input(llm, "hola"), ("ok", "hola"))

    def test_fail_open_on_error(self):
        llm = FakeLLM(error=ConnectionError())
        self.assertEqual(guardrails.classify_input(llm, "hola"), ("ok", "hola"))


class SourceOfTruthTests(unittest.TestCase):
    def test_contains_cv_and_project_sections(self):
        sot = prompts.source_of_truth()
        self.assertIn("## CV", sot)
        self.assertIn("## Project notes", sot)


def _load_gen_brief():
    path = Path(__file__).resolve().parents[1] / "scripts" / "gen_project_brief.py"
    spec = importlib.util.spec_from_file_location("gen_project_brief", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ProjectBriefTests(unittest.TestCase):
    def setUp(self):
        self.gen = _load_gen_brief()

    def test_parses_real_nodes_and_endpoints(self):
        graph_src = self.gen._read(self.gen.SRC / "graph.py")
        server_src = self.gen._read(self.gen.SRC / "server.py")
        self.assertIn("chatbot", self.gen.parse_nodes(graph_src))
        self.assertTrue(any("/api/chat" in e for e in self.gen.parse_endpoints(server_src)))

    def test_build_brief_is_deterministic(self):
        self.assertEqual(self.gen.build_brief(), self.gen.build_brief())


if __name__ == "__main__":
    unittest.main()
