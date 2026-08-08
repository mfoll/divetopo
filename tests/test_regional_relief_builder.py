from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "apps" / "web" / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location(
    "build_regional_relief",
    SCRIPTS / "build_regional_relief.py",
)
assert SPEC is not None and SPEC.loader is not None
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


class RegionalReliefBuilderTests(unittest.TestCase):
    def test_every_autonomous_region_has_valid_derived_bounds(self) -> None:
        for slug in (
            "bouches-du-rhone",
            "var-ouest",
            "var-centre",
            "var-est",
            "alpes-maritimes",
        ):
            with self.subTest(region=slug):
                region = BUILDER.load_region(slug)
                west, south, east, north = BUILDER.marker_bounds(region)
                self.assertLess(west, east)
                self.assertLess(south, north)
                self.assertGreaterEqual(east - west, 0.4)
                self.assertGreaterEqual(north - south, 0.3)

    def test_manifest_template_uses_region_scoped_assets(self) -> None:
        manifest = BUILDER.manifest_template(
            "var-centre",
            (5.8, 42.9, 6.5, 43.3),
        )
        locator = manifest["westCoastLocator"]
        self.assertEqual(
            locator["src"],
            "/maps/var-centre/var-centre-regional-relief.png",
        )
        self.assertEqual(
            locator["boundsWgs84"],
            {"west": 5.8, "south": 42.9, "east": 6.5, "north": 43.3},
        )
        self.assertEqual(manifest["sites"], [])


if __name__ == "__main__":
    unittest.main()
