import unittest

from scripts.eval_run_jev import input_verdict_for_graph


class JevInputMappingTests(unittest.TestCase):
    def test_loaded_verdict_is_deflected_without_rewrite(self):
        self.assertEqual(input_verdict_for_graph("loaded"), ("abuse", None))

    def test_other_verdicts_keep_their_graph_routes(self):
        for verdict in ("ok", "abuse", "injection"):
            with self.subTest(verdict=verdict):
                self.assertEqual(input_verdict_for_graph(verdict), (verdict, None))

    def test_unknown_verdict_fails_closed(self):
        with self.assertRaises(ValueError):
            input_verdict_for_graph("unknown")


if __name__ == "__main__":
    unittest.main()