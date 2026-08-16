from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "release" / "check_release.py"
SPEC = importlib.util.spec_from_file_location("release_check", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
release_check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release_check)


class ReleaseContractTests(unittest.TestCase):
    def test_declared_release_sites_are_fully_published(self) -> None:
        self.assertEqual(release_check.validate_release(ROOT), [])


if __name__ == "__main__":
    unittest.main()
