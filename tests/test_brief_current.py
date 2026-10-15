"""The committed docs/PROJECT.md must match what the generator produces.

`docs/PROJECT.md` is generated, never hand-edited (see AGENTS.md). This test
makes a stale brief a failing test instead of a silent honesty bug.
"""

import importlib.util
import unittest
from pathlib import Path


def _load_gen_brief():
    path = Path(__file__).resolve().parents[1] / "scripts" / "gen_project_brief.py"
    spec = importlib.util.spec_from_file_location("gen_project_brief", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ProjectBriefCurrentTests(unittest.TestCase):
    def test_committed_brief_matches_generated(self):
        gen = _load_gen_brief()
        self.assertEqual(
            gen.build_brief(),
            Path("docs/PROJECT.md").read_text(encoding="utf-8"),
            "docs/PROJECT.md is stale. Regenerate it with: "
            ".venv/bin/python scripts/gen_project_brief.py",
        )


if __name__ == "__main__":
    unittest.main()
