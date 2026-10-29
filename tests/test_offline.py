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
    """Stand-in for ChatOpenRouter. Supports both the structured path
    (``with_structured_output``) and the raw ``invoke`` fallback, and records
    which one was used."""

    def __init__(self, content=None, error=None, structured=None, structured_error=None):
        self._content = content
        self._error = error
        self._structured = structured
        self._structured_error = structured_error
        self.raw_called = False
        self.structured_called = False

    def invoke(self, *_args, **_kwargs):
        self.raw_called = True
        if self._error:
            raise self._error
        return SimpleNamespace(content=self._content)

    def with_structured_output(self, schema):
        outer = self

        class _Chain:
            def invoke(self, *_a, **_k):
                outer.structured_called = True
                if outer._structured_error:
                    raise outer._structured_error
                result = outer._structured
                return result if isinstance(result, schema) else None

        return _Chain()



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


class StructuredOutputTests(unittest.TestCase):
    """The native structured path (ChatOpenRouter.with_structured_output)."""

    def test_check_output_uses_structured_when_available(self):
        verdict = guardrails.OutputCheck(ok=False, reason="overclaim: PhD")
        llm = FakeLLM(structured=verdict)
        self.assertEqual(guardrails.check_output(llm, "q", "a", "src"), (False, "overclaim: PhD"))
        self.assertTrue(llm.structured_called)
        self.assertFalse(llm.raw_called)  # fallback must not run when structured succeeds

    def test_classify_input_uses_structured_when_available(self):
        verdict = guardrails.InputVerdict(verdict="loaded", neutral_question="¿Es adecuado? ")
        llm = FakeLLM(structured=verdict)
        self.assertEqual(guardrails.classify_input(llm, "hostil"), ("loaded", "¿Es adecuado?"))
        self.assertFalse(llm.raw_called)

    def test_structured_failure_falls_back_to_raw(self):
        llm = FakeLLM(
            structured_error=RuntimeError("schema unsupported"),
            content='{"verdict": "abuse", "neutral_question": ""}',
        )
        self.assertEqual(guardrails.classify_input(llm, "insulto"), ("abuse", ""))
        self.assertTrue(llm.structured_called)
        self.assertTrue(llm.raw_called)  # fallback used after structured errored

    def test_both_paths_down_fails_open(self):
        llm = FakeLLM(structured_error=RuntimeError("boom"), error=ConnectionError())
        self.assertEqual(guardrails.check_output(llm, "q", "a", "src"), (True, ""))


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

    def test_parses_environment_variables_with_empty_defaults(self):
        self.assertEqual(
            self.gen.parse_env('os.getenv("LANGFUSE_PUBLIC_KEY", "")'),
            ['- `LANGFUSE_PUBLIC_KEY` (default ``)'],
        )


if __name__ == "__main__":
    unittest.main()
