from __future__ import annotations

import json
import unittest
from pathlib import Path

from cartography.config import ROOT, validate_config


REGION_PATH = ROOT / "regions" / "var-est" / "region.json"
EXPECTED_SITES = [
    "les-pyramides-cap-dramont",
    "sec-de-l-ile-d-or",
    "arche-du-dramont",
    "cathedrale-du-trayas",
    "le-village",
]
class VarEstRegionTests(unittest.TestCase):
    def test_first_wave_inventory_is_exact_and_published(self) -> None:
        region = json.loads(REGION_PATH.read_text(encoding="utf-8"))
        self.assertEqual(region["slug"], "var-est")
        self.assertEqual(region["route"], "/var-est")
        self.assertEqual(region["routeStatus"], "implemented")
        self.assertEqual(region["regionalMap"]["status"], "generated")
        self.assertEqual(
            region["regionalMap"]["sha256"],
            "0f03a6ccac5581749ad92af1e00f2088028dc6b67880ba80247d4bb8ea3c8e57",
        )
        self.assertEqual(
            [site["slug"] for site in region["sites"]],
            EXPECTED_SITES,
        )

        for site in region["sites"]:
            config = json.loads((ROOT / site["config"]).read_text(encoding="utf-8"))
            with self.subTest(slug=site["slug"]):
                self.assertEqual(config["region"], "var-est")
                self.assertEqual(config["slug"], site["slug"])
                self.assertIs(config["web"]["published"], True)
                self.assertTrue(
                    config.get("locator_marker_utm40s")
                    or config.get("site_location_utm40s")
                )
                validate_config(config)

    def test_combined_manifest_indexes_all_published_packages(self) -> None:
        manifest_path = (
            ROOT
            / "regions"
            / "var-est"
            / "outputs"
            / "interactive-terrain"
            / "manifest.json"
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["schemaVersion"], 2)
        self.assertEqual(
            [site["slug"] for site in manifest["sites"]],
            EXPECTED_SITES,
        )


if __name__ == "__main__":
    unittest.main()
