import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "eval_calibrate", ROOT / "scripts" / "eval_calibrate.py"
)
eval_calibrate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(eval_calibrate)


def scored_row(case_id, overall, score, blocking):
    return {
        "id": case_id,
        "overall": overall,
        "scores": {axis: score for axis in eval_calibrate.AXES},
        "blocking_fabrication": blocking,
    }


class CalibrationMetricsTests(unittest.TestCase):
    def test_axis_agreement_and_blocking_false_negatives(self):
        human = [scored_row("safe", 3, 3, False), scored_row("fabricated", 1, 1, True)]
        judge = [
            scored_row("safe", 3, 3, False),
            scored_row("fabricated", 2, 2, False),
        ]

        metrics = eval_calibrate.calibration_metrics(human, judge)

        self.assertEqual(metrics["cases_compared"], 2)
        self.assertEqual(metrics["overall"]["exact"], 0.5)
        self.assertEqual(metrics["axes"]["factuality"]["exact"], 0.5)
        self.assertEqual(metrics["blocking"]["false_negatives"], ["fabricated"])
        self.assertEqual(metrics["disagreements"][0]["id"], "fabricated")
