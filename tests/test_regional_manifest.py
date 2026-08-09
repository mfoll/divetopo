from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "apps" / "web" / "scripts" / "regional_manifest.py"
SPEC = importlib.util.spec_from_file_location("regional_manifest", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
REGIONAL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REGIONAL)


class RegionalManifestTests(unittest.TestCase):
    def test_region_inventory_filters_unpublished_site_drafts(self) -> None:
        var_ouest = REGIONAL.load_published_configs(ROOT, "var-ouest")
        var_centre = REGIONAL.load_published_configs(ROOT, "var-centre")
        var_est = REGIONAL.load_published_configs(ROOT, "var-est")
        self.assertEqual(
            [config["slug"] for config in var_ouest],
            [
                "pointe-portissol",
                "deux-freres-cap-sicie",
                "pointe-de-la-cride",
                "les-magnons",
                "la-merveilleuse",
            ],
        )
        self.assertEqual(
            [config["slug"] for config in var_centre],
            [
                "les-fourmigues",
                "sec-de-la-jeaune-garde",
                "sec-du-langoustier",
                "cap-des-medes",
                "la-gabiniere-port-cros",
            ],
        )
        self.assertEqual(
            [config["slug"] for config in var_est],
            [
                "les-pyramides-cap-dramont",
                "sec-de-l-ile-d-or",
                "arche-du-dramont",
                "cathedrale-du-trayas",
                "le-village",
            ],
        )

    def test_web_metadata_converts_site_data_to_manifest_shape(self) -> None:
        metadata = REGIONAL.web_site_metadata(
            {
                "web": {
                    "published": True,
                    "site_label_layout": {
                        "side": "left",
                        "shift_y_rem": -1,
                        "connector_angle_deg": 20,
                    },
                    "interactive_initial_view": {
                        "zoom": 0.8,
                        "center_offset_east_m": 30,
                    },
                }
            }
        )
        self.assertEqual(
            metadata,
            {
                "siteLabelLayout": {
                    "side": "left",
                    "shiftYRem": -1,
                    "connectorAngleDeg": 20,
                },
                "interactiveInitialView": {
                    "zoom": 0.8,
                    "centerOffsetEastM": 30,
                },
            },
        )


if __name__ == "__main__":
    unittest.main()
