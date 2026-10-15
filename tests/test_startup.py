"""Startup contracts: a missing cv.md must fail helpfully, and the shipped
template must mirror the structure the loaders expect.

Run with:

    PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cv_chat import prompts  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]


class TestStartup(unittest.TestCase):
    def test_load_cv_raises_actionable_error_when_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "cv.md"
            self.assertFalse(missing.exists())
            with patch.object(prompts, "CV_PATH", missing):
                with self.assertRaises(FileNotFoundError) as ctx:
                    prompts.load_cv()
        self.assertIn("cv.md.sample", str(ctx.exception))

    def test_sample_covers_real_cv_sections(self):
        sample = (REPO_ROOT / "cv.md.sample").read_text(encoding="utf-8")
        for heading in (
            "Summary",
            "Technical Skills",
            "Professional Experience",
            "Education",
        ):
            self.assertIn(heading, sample)

    def test_source_of_truth_has_cv_and_project_sections(self):
        source = prompts.source_of_truth()
        self.assertIn("## CV", source)
        self.assertIn("## Project notes", source)


if __name__ == "__main__":
    unittest.main()
