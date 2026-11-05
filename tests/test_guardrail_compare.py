import unittest

from scripts.guardrail_compare import _binary_metrics


class BinaryGuardrailMetricsTests(unittest.TestCase):
    def test_correct_decisions_have_no_missed_unsafe_cases(self):
        rows = [
            {"expected_ok": False, "actual_ok": False}
            for _ in range(8)
        ] + [
            {"expected_ok": True, "actual_ok": True}
            for _ in range(4)
        ]

        metrics = _binary_metrics(rows, "expected_ok", "actual_ok")

        self.assertEqual(metrics["correct"], 12)
        self.assertEqual(metrics["unsafe_missed"], 0)
        self.assertEqual(metrics["benign_blocked"], 0)

    def test_accepting_an_unsafe_case_counts_as_missed(self):
        rows = [
            {"expected_ok": False, "actual_ok": True},
            {"expected_ok": False, "actual_ok": False},
            {"expected_ok": True, "actual_ok": False},
        ]

        metrics = _binary_metrics(rows, "expected_ok", "actual_ok")

        self.assertEqual(metrics["unsafe_missed"], 1)
        self.assertEqual(metrics["benign_blocked"], 1)


if __name__ == "__main__":
    unittest.main()