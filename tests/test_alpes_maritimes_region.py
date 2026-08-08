from __future__ import annotations

import json
import unittest
from pathlib import Path

from cartography.config import ROOT, region_manifest, region_output_directory


REGION_ROOT = ROOT / "regions" / "alpes-maritimes"


class AlpesMaritimesRegionTests(unittest.TestCase):
    def test_autonomous_region_contract(self) -> None:
        manifest = region_manifest({"region": "alpes-maritimes"})

        self.assertEqual(manifest["slug"], "alpes-maritimes")
        self.assertEqual(manifest["route"], "/alpes-maritimes")
        self.assertEqual(
            manifest["pipeline"]["module"],
            "cartography.regions.alpes_maritimes",
        )
        self.assertEqual(manifest["sites"], [])
        self.assertEqual(
            region_output_directory({"region": "alpes-maritimes"}),
            REGION_ROOT / "outputs",
        )

    def test_region_paths_exist_without_borrowing_paca_directories(self) -> None:
        manifest = json.loads(
            (REGION_ROOT / "region.json").read_text(encoding="utf-8")
        )
        pipeline = manifest["pipeline"]

        for key in (
            "siteConfigDirectory",
            "outputDirectory",
            "interactiveTerrainDirectory",
        ):
            self.assertTrue(pipeline[key].startswith("regions/alpes-maritimes/"))
            self.assertNotIn("regions/paca/", pipeline[key])


if __name__ == "__main__":
    unittest.main()
