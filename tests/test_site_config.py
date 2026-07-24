from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from site_config import (
    DEFAULT_CACHE,
    DEFAULT_RELIEF_EXPOSURE,
    DEFAULT_VERTICAL_EXAGGERATION,
    ROOT,
    paths_for,
    validate_config,
)


SITES = ROOT / "sites"
REFERENCE_SITE_SLUGS = {
    "boucan-canot",
    "cap-la-houssaye",
    "passe-hermitage",
}


def migrated_config(path: Path) -> dict:
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("orthophoto_enabled", False):
        config.setdefault("orthophoto_capture_date", "2025-07-22")
    if config.get("locator_bathymetry_enabled", False):
        config.setdefault(
            "locator_gebco_attribution",
            "GEBCO Compilation Group, version pinned by the site configuration",
        )
    config.setdefault("max_land_elevation_m", 55.0)
    return config


class SiteConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.configs = [
            migrated_config(path)
            for path in sorted(SITES.glob("*.json"))
        ]

    def test_all_site_configs_validate_before_or_after_planned_migration(self) -> None:
        self.assertTrue(
            REFERENCE_SITE_SLUGS.issubset(
                {config["slug"] for config in self.configs}
            )
        )
        for config in self.configs:
            with self.subTest(slug=config["slug"]):
                validate_config(config)

    def test_reference_sites_share_the_default_vertical_exaggeration(self) -> None:
        for config in self.configs:
            with self.subTest(slug=config["slug"]):
                self.assertEqual(
                    config["vertical_exaggeration"],
                    DEFAULT_VERTICAL_EXAGGERATION,
                )

    def test_reference_sites_share_the_default_relief_exposure(self) -> None:
        self.assertEqual(DEFAULT_RELIEF_EXPOSURE, 1.55)
        for config in self.configs:
            with self.subTest(slug=config["slug"]):
                self.assertEqual(
                    config.get("relief_exposure", DEFAULT_RELIEF_EXPOSURE),
                    DEFAULT_RELIEF_EXPOSURE,
                )

    def test_invalid_bbox_is_rejected(self) -> None:
        config = copy.deepcopy(self.configs[0])
        config["focus_bbox_utm40s"] = [0, 0, 10, 10]
        with self.assertRaisesRegex(ValueError, "must contain focus"):
            validate_config(config)

    def test_unknown_typo_is_rejected(self) -> None:
        config = copy.deepcopy(self.configs[0])
        config["orthphoto_resolution_m"] = 0.2
        with self.assertRaisesRegex(ValueError, "Unknown configuration key"):
            validate_config(config)

    def test_source_and_credit_strings_reject_wrong_types(self) -> None:
        for key, value in (
            ("hyscores_tiff_url", 123),
            ("orthophoto_layer", []),
            ("map_license", {}),
        ):
            config = copy.deepcopy(self.configs[0])
            config[key] = value
            with self.subTest(key=key):
                with self.assertRaisesRegex(ValueError, key):
                    validate_config(config)

    def test_orthophoto_provenance_is_required_and_must_be_iso(self) -> None:
        config = copy.deepcopy(self.configs[0])
        config.pop("orthophoto_capture_date", None)
        with self.assertRaisesRegex(ValueError, "orthophoto_capture_date"):
            validate_config(config)

        config["orthophoto_capture_date"] = "22-07-2025"
        with self.assertRaisesRegex(ValueError, "ISO date"):
            validate_config(config)

    def test_locator_bathymetry_provenance_is_required(self) -> None:
        config = copy.deepcopy(self.configs[0])
        config.pop("locator_gebco_attribution", None)
        with self.assertRaisesRegex(ValueError, "locator_gebco_attribution"):
            validate_config(config)

    def test_default_paths_include_source_locator_detail_and_plates(self) -> None:
        paths = paths_for({"slug": "new-site"})
        self.assertEqual(paths["context_depth_raw"], DEFAULT_CACHE / "new-site-context-depth.tif")
        self.assertEqual(paths["focus_elevation"], DEFAULT_CACHE / "new-site-focus-elevation.tif")
        self.assertEqual(paths["locator_elevation"], DEFAULT_CACHE / "reunion-locator-elevation.tif")
        self.assertEqual(paths["output_2d"], ROOT / "outputs" / "new-site-topobathy-2d.jpg")
        self.assertEqual(paths["output_locator"], ROOT / "outputs" / "new-site-locator-reunion.jpg")
        self.assertEqual(paths["output_plate"], ROOT / "outputs" / "new-site-planche.jpg")
        self.assertEqual(
            paths["output_plate_topography"],
            ROOT / "outputs" / "new-site-planche-topographique.jpg",
        )
        self.assertEqual(len(paths), 16)

    def test_explicit_sea_imagery_bounds_are_paired_and_ordered(self) -> None:
        config = copy.deepcopy(self.configs[0])
        config.pop("imagery_sea_max_depth_m", None)
        with self.assertRaisesRegex(ValueError, "must be set together"):
            validate_config(config)

        config["imagery_sea_max_depth_m"] = 0.5
        with self.assertRaisesRegex(ValueError, "full depth < maximum"):
            validate_config(config)

    def test_legacy_and_new_crop_or_axis_aliases_cannot_be_mixed(self) -> None:
        config = copy.deepcopy(self.configs[0])
        config["east_crop_fraction"] = 0.0
        config["view_left_crop_fraction"] = 0.1
        with self.assertRaisesRegex(ValueError, "Do not mix legacy crop keys"):
            validate_config(config)

        config = copy.deepcopy(self.configs[0])
        config["north_south_projection_scale"] = 1.0
        config["along_view_projection_scale"] = 1.0
        with self.assertRaisesRegex(ValueError, "Do not mix north_south"):
            validate_config(config)

    def test_new_crop_and_axis_names_validate(self) -> None:
        config = copy.deepcopy(self.configs[0])
        for key in (
            "horizontal_crop_fraction",
            "east_crop_fraction",
            "west_crop_fraction",
            "south_crop_fraction",
            "north_south_projection_scale",
        ):
            config.pop(key, None)
        config.update(
            {
                "view_left_crop_fraction": 0.1,
                "view_right_crop_fraction": 0.2,
                "view_top_crop_fraction": 0.15,
                "along_view_projection_scale": 1.1,
            }
        )
        validate_config(config)

    def test_duplicate_resolved_paths_are_rejected(self) -> None:
        config = copy.deepcopy(self.configs[0])
        config.setdefault("paths", {})
        config["paths"]["output_2d"] = "outputs/shared-test-output.jpg"
        config["paths"]["output_3d"] = "outputs/shared-test-output.jpg"
        with self.assertRaisesRegex(ValueError, "same file"):
            validate_config(config)


if __name__ == "__main__":
    unittest.main()
