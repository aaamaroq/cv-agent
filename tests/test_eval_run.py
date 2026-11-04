import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "eval_run", ROOT / "scripts" / "eval_run.py"
)
eval_run = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = eval_run
SPEC.loader.exec_module(eval_run)


class GuardrailRejectionReasonTests(unittest.TestCase):
    def test_extracts_only_the_rejection_reason_from_retry_note(self):
        note = (
            "Your previous draft was rejected by a quality guardrail: "
            "unsupported customer-impact claim. Write a new answer that stays factual."
        )

        self.assertEqual(
            eval_run._guardrail_rejection_reason(note),
            "unsupported customer-impact claim.",
        )

    def test_missing_rejection_note_returns_none(self):
        self.assertIsNone(eval_run._guardrail_rejection_reason(None))


if __name__ == "__main__":
    unittest.main()
