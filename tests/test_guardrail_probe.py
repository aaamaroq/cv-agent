import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
SPEC = importlib.util.spec_from_file_location(
    "guardrail_probe", ROOT / "scripts" / "guardrail_probe.py"
)
guardrail_probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guardrail_probe)


class MpcCapabilityProbeTests(unittest.TestCase):
    def test_flags_positive_undocumented_mcp_features(self):
        status, _ = guardrail_probe.evaluate(
            "mcp_grounded",
            "ok",
            "What did the MCP servers do?",
            "What did the MCP servers do?",
            "The servers provided secure access controls and report generation.",
        )
        self.assertEqual(status, "FAIL")

    def test_allows_explicitly_marking_capabilities_as_undocumented(self):
        status, _ = guardrail_probe.evaluate(
            "mcp_grounded",
            "ok",
            "What did the MCP servers do?",
            "What did the MCP servers do?",
            "The sources do not document security controls or report generation.",
        )
        self.assertEqual(status, "PASS")

    def test_allows_the_documented_natural_language_database_access(self):
        status, _ = guardrail_probe.evaluate(
            "mcp_grounded",
            "ok",
            "What did the MCP servers do?",
            "What did the MCP servers do?",
            "They exposed internal databases to LLM agents for natural-language access.",
        )
        self.assertEqual(status, "PASS")


class PreparedQuestionProbeTests(unittest.TestCase):
    def _evaluate(self, expect, answer):
        return guardrail_probe.evaluate(
            expect,
            "ok",
            "prepared question",
            "prepared question",
            answer,
        )[0]

    def test_q04_accepts_a_clear_evidence_boundary_and_rejects_a_fabricated_story(self):
        self.assertEqual(
            self._evaluate(
                "documented_absence",
                "The sources do not document a specific disagreement with a colleague.",
            ),
            "PASS",
        )
        self.assertEqual(
            self._evaluate(
                "documented_absence",
                "At 41OPS, Adrián disagreed with a senior engineer about caching.",
            ),
            "FAIL",
        )

    def test_q03_weakness_boundary_is_specific_to_the_question(self):
        self.assertEqual(
            self._evaluate(
                "documented_absence",
                "The sources do not document a personal weakness or knowledge gap.",
            ),
            "PASS",
        )

    def test_q06_accepts_only_the_documented_career_aspiration(self):
        self.assertEqual(
            self._evaluate(
                "documented_aspiration",
                "Adrián aims to grow as an AI Engineer and later take on technical leadership.",
            ),
            "PASS",
        )
        self.assertEqual(
            self._evaluate(
                "documented_aspiration",
                "I see myself as a senior AI engineer leading large-scale AI research.",
            ),
            "FAIL",
        )

    def test_q11_requires_supported_mcp_details_in_spanish(self):
        self.assertEqual(
            self._evaluate(
                "mcp_factual_es",
                "Adrián construyó servidores MCP en TypeScript para un cliente bancario. "
                "Exponían bases de datos internas a agentes LLM para acceder a datos "
                "empresariales en lenguaje natural.",
            ),
            "PASS",
        )
        self.assertEqual(
            self._evaluate(
                "mcp_factual_es",
                "Adrián construyó servidores MCP en TypeScript con acceso seguro "
                "para generar informes a clientes.",
            ),
            "FAIL",
        )


if __name__ == "__main__":
    unittest.main()
