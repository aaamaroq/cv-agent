import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "eval_report", ROOT / "scripts" / "eval_report.py"
)
eval_report = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(eval_report)


def labels_for(score=3, *, fabrication=False):
    return {
        f"case-{index}": {
            "overall": score,
            "scores": {axis: score for axis in eval_report.AXES},
            "blocking_fabrication": fabrication,
        }
        for index in range(4)
    }


class ApprovalThresholdTests(unittest.TestCase):
    def test_exact_quarter_point_regression_passes(self):
        baseline = labels_for(3)
        candidate = labels_for(3)
        # Three of four scores at 3 and one at 2 gives a 0.25 regression.
        candidate["case-0"]["scores"]["factuality"] = 2
        status, _ = eval_report._approval_message(baseline, candidate)
        self.assertEqual(status, "Pasa el umbral")

    def test_new_fabrication_fails_threshold(self):
        baseline = labels_for(3)
        candidate = labels_for(3)
        candidate["case-2"]["blocking_fabrication"] = True
        status, detail = eval_report._approval_message(baseline, candidate)
        self.assertEqual(status, "No pasa")
        self.assertIn("fabricaciones nuevas", detail)

    def test_axis_regression_over_quarter_point_fails_threshold(self):
        baseline = labels_for(3)
        candidate = labels_for(3)
        for row in candidate.values():
            row["scores"]["guardrails"] = 2
        status, detail = eval_report._approval_message(baseline, candidate)
        self.assertEqual(status, "No pasa")
        self.assertIn("Guardrails", detail)


class HtmlReportTests(unittest.TestCase):
    def test_generates_standalone_html_with_case_and_radar(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run_path = root / "baseline.jsonl"
            labels_path = root / "baseline-labels.jsonl"
            output_path = root / "report.html"
            run_path.write_text(
                "\n".join(
                    json.dumps(row)
                    for row in (
                        {"record_type": "run", "run_id": "baseline-1"},
                        {
                            "record_type": "case",
                            "id": "case-1",
                            "category": "factual",
                            "question": "What did Adrián build?",
                            "answer": "He built a personal chatbot.",
                        },
                    )
                ),
                encoding="utf-8",
            )
            labels_path.write_text(
                json.dumps({
                    "id": "case-1",
                    "overall": 3,
                    "scores": {axis: 3 for axis in eval_report.AXES},
                    "blocking_fabrication": False,
                }) + "\n",
                encoding="utf-8",
            )

            eval_report.build_report(
                run_path, None, labels_path, None, output_path
            )

            report = output_path.read_text(encoding="utf-8")
            self.assertIn("Radar por eje", report)
            self.assertIn("What did Adrián build?", report)
            self.assertIn('"values": [3.0, 3.0, 3.0, 3.0, 3.0]', report)
            self.assertNotIn("<script src=", report)


if __name__ == "__main__":
    unittest.main()
