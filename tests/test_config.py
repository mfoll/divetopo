from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from cartography.config import (
    DEFAULT_CACHE,
    DEFAULT_RELIEF_EXPOSURE,
    DEFAULT_VERTICAL_EXAGGERATION,
    ROOT,
    interactive_footprint_bounds,
    interactive_footprint_corners,
    paths_for,
    region_manifest,
    region_output_directory,
    validate_config,
)


SITES = ROOT / "regions" / "reunion" / "sites"
PUBLISHED_SITE_SLUGS = {
    "boucan-canot",
    "cap-homard",
    "cap-la-houssaye",
    "passe-hermitage",
    "plage-cimetiere-saint-leu",
    "pointe-des-aigrettes",
    "pointe-au-sel-sec-jaune",
    "pont-rouge",
    "roches-noires",
    "souris-chaude",
    "trois-bassins",
}


class SiteConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.configs = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(SITES.glob("*.json"))
        ]

    def test_all_published_site_configs_validate(self) -> None:
        self.assertEqual(
            {config["slug"] for config in self.configs},
            PUBLISHED_SITE_SLUGS,
        )
        for config in self.configs:
            with self.subTest(slug=config["slug"]):
                validate_config(config)

    def test_region_manifest_owns_the_published_site_inventory(self) -> None:
        manifest = region_manifest({"region": "reunion"})
        self.assertEqual(
            {site["slug"] for site in manifest["sites"]},
            PUBLISHED_SITE_SLUGS,
        )
        self.assertEqual(
            region_output_directory({"region": "reunion"}),
            ROOT / "regions" / "reunion" / "outputs",
        )
        for config in self.configs:
            self.assertEqual(config["region"], "reunion")

    def test_published_sites_share_the_default_vertical_exaggeration(self) -> None:
        for config in self.configs:
            with self.subTest(slug=config["slug"]):
                self.assertEqual(
                    config["vertical_exaggeration"],
                    DEFAULT_VERTICAL_EXAGGERATION,
                )

    def test_published_sites_share_the_default_relief_exposure(self) -> None:
        self.assertEqual(DEFAULT_RELIEF_EXPOSURE, 1.55)
        for config in self.configs:
            with self.subTest(slug=config["slug"]):
                self.assertEqual(
                    config.get("relief_exposure", DEFAULT_RELIEF_EXPOSURE),
                    DEFAULT_RELIEF_EXPOSURE,
                )

    def test_all_orthophoto_sites_share_the_standard_sea_fade(self) -> None:
        for config in self.configs:
            if not config.get("orthophoto_enabled", False):
                continue
            with self.subTest(slug=config["slug"]):
                self.assertEqual(config.get("imagery_sea_full_depth_m"), 1.5)
                self.assertEqual(config.get("imagery_sea_max_depth_m"), 2.0)
                self.assertEqual(config.get("imagery_sea_smoothing_m"), 5.0)

    def test_published_sites_share_map_dimensions_and_graphic_scale(self) -> None:
        for config in self.configs:
            with self.subTest(slug=config["slug"]):
                self.assertEqual(config["final_output_size_px"], [2474, 1712])
                self.assertEqual(config["map_style_scale"], 2.0)

    def test_site_local_depth_and_completion_overrides_remain_scoped(self) -> None:
        configs = {config["slug"]: config for config in self.configs}
        pointe = configs["pointe-au-sel-sec-jaune"]
        self.assertEqual(pointe["max_depth_m"], 40)
        self.assertEqual(pointe["plan_max_depth_m"], 30)
        self.assertNotIn("interactive_max_depth_m", pointe)
        self.assertEqual(pointe["view_crop_depth_m"], 1400.0)
        self.assertEqual(
            pointe["interactive_footprint_utm40s"],
            {
                "center": [321581.5, 7654180.4],
                "width_m": 1040.0,
                "depth_m": 1545.0,
                "look_bearing_deg": 60.0,
            },
        )
        self.assertTrue(pointe["deep_edge_nodata_terrain_fill"])
        self.assertEqual(
            pointe["deep_edge_nodata_terrain_min_depth_m"],
            20.0,
        )
        self.assertEqual(pointe["relief_mesh_gap_fill_max_area_m2"], 64.0)
        souris = configs["souris-chaude"]
        self.assertEqual(souris["plan_max_depth_m"], 40)
        self.assertTrue(souris["deep_edge_nodata_terrain_fill"])
        self.assertEqual(
            souris["deep_edge_nodata_terrain_min_depth_m"],
            14.8,
        )
        for slug, config in configs.items():
            with self.subTest(slug=slug):
                if slug not in {"pointe-au-sel-sec-jaune", "souris-chaude"}:
                    self.assertNotIn("plan_max_depth_m", config)
                self.assertNotIn("interactive_max_depth_m", config)
                self.assertNotIn("interactive_bbox_utm40s", config)
                self.assertIn("interactive_footprint_utm40s", config)
                if slug not in {"pointe-au-sel-sec-jaune", "souris-chaude"}:
                    self.assertNotIn("deep_edge_nodata_terrain_fill", config)
                    self.assertNotIn(
                        "deep_edge_nodata_terrain_min_depth_m",
                        config,
                    )
                if slug not in {"pointe-au-sel-sec-jaune", "souris-chaude"}:
                    self.assertNotIn("relief_mesh_gap_fill_max_area_m2", config)

    def test_static_interactive_center_alignment_is_site_local(self) -> None:
        self.assertEqual(
            {
                config["slug"]
                for config in self.configs
                if config.get("interactive_match_static_horizontal_center")
            },
            {"passe-hermitage", "pont-rouge"},
        )

    def test_interactive_visible_width_override_is_site_local(self) -> None:
        configs = {config["slug"]: config for config in self.configs}
        self.assertEqual(
            {
                slug
                for slug, config in configs.items()
                if "interactive_view_visible_width_m" in config
            },
            {"cap-homard", "souris-chaude"},
        )
        self.assertEqual(configs["cap-homard"]["view_visible_width_m"], 600.0)
        self.assertEqual(
            configs["cap-homard"]["interactive_view_visible_width_m"],
            540.0,
        )
        self.assertEqual(configs["souris-chaude"]["view_visible_width_m"], 650.0)
        self.assertEqual(
            configs["souris-chaude"]["interactive_view_visible_width_m"],
            600.0,
        )

    def test_all_sites_use_a_valid_coast_aligned_interactive_footprint(
        self,
    ) -> None:
        for config in self.configs:
            with self.subTest(slug=config["slug"]):
                footprint = config["interactive_footprint_utm40s"]
                self.assertEqual(
                    footprint["look_bearing_deg"],
                    config.get("view_bearing_deg", 180.0),
                )
                self.assertNotIn("interactive_bbox_utm40s", config)
                west, south, east, north = interactive_footprint_bounds(
                    config
                )
                context = config["context_bbox_utm40s"]
                self.assertGreaterEqual(west, context[0])
                self.assertGreaterEqual(south, context[1])
                self.assertLessEqual(east, context[2])
                self.assertLessEqual(north, context[3])

    def test_oriented_footprint_corners_and_bounds(self) -> None:
        north = {
            "interactive_footprint_utm40s": {
                "center": [100.0, 200.0],
                "width_m": 20.0,
                "depth_m": 40.0,
                "look_bearing_deg": 0.0,
            }
        }
        self.assertEqual(
            interactive_footprint_corners(north),
            (
                (90.0, 180.0),
                (110.0, 180.0),
                (110.0, 220.0),
                (90.0, 220.0),
            ),
        )
        diagonal = copy.deepcopy(north)
        diagonal["interactive_footprint_utm40s"][
            "look_bearing_deg"
        ] = 45.0
        bounds = interactive_footprint_bounds(diagonal)
        expected_half_span = 30.0 / (2.0 ** 0.5)
        self.assertAlmostEqual(bounds[0], 100.0 - expected_half_span)
        self.assertAlmostEqual(bounds[1], 200.0 - expected_half_span)
        self.assertAlmostEqual(bounds[2], 100.0 + expected_half_span)
        self.assertAlmostEqual(bounds[3], 200.0 + expected_half_span)

    def test_invalid_bbox_is_rejected(self) -> None:
        config = copy.deepcopy(self.configs[0])
        config["focus_bbox_utm40s"] = [0, 0, 10, 10]
        with self.assertRaisesRegex(ValueError, "must contain focus"):
            validate_config(config)

        config = copy.deepcopy(self.configs[0])
        config.pop("interactive_footprint_utm40s")
        config["interactive_bbox_utm40s"] = [0, 0, 10, 10]
        with self.assertRaisesRegex(ValueError, "must contain interactive"):
            validate_config(config)

        config = copy.deepcopy(self.configs[0])
        config["interactive_footprint_utm40s"]["center"] = [0, 0]
        with self.assertRaisesRegex(ValueError, "must contain interactive"):
            validate_config(config)

    def test_interactive_footprint_rejects_short_or_misaligned_extents(
        self,
    ) -> None:
        config = copy.deepcopy(self.configs[0])
        config["interactive_footprint_utm40s"]["width_m"] = 1.0
        with self.assertRaisesRegex(ValueError, "1.15 times"):
            validate_config(config)

        config = copy.deepcopy(self.configs[0])
        config["interactive_footprint_utm40s"]["depth_m"] = 1.0
        with self.assertRaisesRegex(ValueError, "too short"):
            validate_config(config)

        config = copy.deepcopy(self.configs[0])
        config["context_bbox_utm40s"] = [
            config["context_bbox_utm40s"][0] - 100.0,
            config["context_bbox_utm40s"][1] - 100.0,
            config["context_bbox_utm40s"][2] + 100.0,
            config["context_bbox_utm40s"][3] + 100.0,
        ]
        config["interactive_footprint_utm40s"]["look_bearing_deg"] += 1.0
        with self.assertRaisesRegex(ValueError, "must match"):
            validate_config(config)

    def test_plan_depth_must_not_exceed_relief_depth(self) -> None:
        config = copy.deepcopy(self.configs[0])
        config["plan_max_depth_m"] = config["max_depth_m"] + 1
        with self.assertRaisesRegex(ValueError, "at most max_depth_m"):
            validate_config(config)

        config["plan_max_depth_m"] = config["max_depth_m"]
        validate_config(config)

        config["interactive_max_depth_m"] = config["max_depth_m"] + 1
        with self.assertRaisesRegex(ValueError, "interactive_max_depth_m"):
            validate_config(config)

        config["interactive_max_depth_m"] = config["max_depth_m"]
        validate_config(config)

        config["deep_edge_nodata_terrain_fill"] = True
        config["deep_edge_nodata_terrain_min_depth_m"] = 20
        config["interactive_max_depth_m"] = 10
        with self.assertRaisesRegex(
            ValueError,
            "effective interactive depth",
        ):
            validate_config(config)

        config = copy.deepcopy(self.configs[0])
        config["relief_mesh_gap_fill_max_area_m2"] = 0
        with self.assertRaisesRegex(ValueError, "relief_mesh_gap_fill_max_area_m2"):
            validate_config(config)

    def test_reunion_depth_limit_remains_40_metres(self) -> None:
        config = copy.deepcopy(self.configs[0])
        config["max_depth_m"] = 40.0
        validate_config(config)
        config["max_depth_m"] = 40.01
        with self.assertRaisesRegex(
            ValueError,
            "at most 40 for region reunion",
        ):
            validate_config(config)

    def test_unknown_typo_is_rejected(self) -> None:
        config = copy.deepcopy(self.configs[0])
        config["orthphoto_resolution_m"] = 0.2
        with self.assertRaisesRegex(ValueError, "Unknown configuration key"):
            validate_config(config)

    def test_interactive_static_center_alignment_requires_a_boolean(self) -> None:
        config = copy.deepcopy(self.configs[0])
        config["interactive_match_static_horizontal_center"] = "yes"
        with self.assertRaisesRegex(
            ValueError,
            "interactive_match_static_horizontal_center",
        ):
            validate_config(config)

        config = copy.deepcopy(self.configs[0])
        config["deep_edge_nodata_terrain_fill"] = "yes"
        with self.assertRaisesRegex(
            ValueError,
            "deep_edge_nodata_terrain_fill",
        ):
            validate_config(config)

        config = copy.deepcopy(self.configs[0])
        config["deep_edge_nodata_terrain_min_depth_m"] = 10
        with self.assertRaisesRegex(
            ValueError,
            "requires deep_edge_nodata_terrain_fill",
        ):
            validate_config(config)

        config["deep_edge_nodata_terrain_fill"] = True
        config["deep_edge_nodata_terrain_min_depth_m"] = (
            config["max_depth_m"] + 1
        )
        with self.assertRaisesRegex(
            ValueError,
            "deep_edge_nodata_terrain_min_depth_m",
        ):
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

    def test_plate_identity_requires_one_site_one_city_and_one_island_line(self) -> None:
        config = copy.deepcopy(self.configs[0])
        for invalid_name in (
            "Cap Homard / Cap de Tonton",
            "Sec Jaune, Pointe au Sel",
            "Pont Rouge · La Tortue",
            "Cap La Houssaye, La Réunion",
        ):
            config["plate_site_name"] = invalid_name
            with self.subTest(plate_site_name=invalid_name):
                with self.assertRaisesRegex(
                    ValueError,
                    "plate_site_name",
                ):
                    validate_config(config)

        config = copy.deepcopy(self.configs[0])
        for invalid_city in ("Saint-Paul, La Réunion", "Saint-Leu / Réunion"):
            config["plate_city"] = invalid_city
            with self.subTest(plate_city=invalid_city):
                with self.assertRaisesRegex(ValueError, "plate_city"):
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
        self.assertEqual(paths["output_2d"], ROOT / "regions" / "reunion" / "outputs" / "new-site-topobathy-2d.jpg")
        self.assertEqual(paths["output_locator"], ROOT / "regions" / "reunion" / "outputs" / "new-site-locator-reunion.jpg")
        self.assertEqual(paths["output_plate"], ROOT / "regions" / "reunion" / "outputs" / "new-site-planche.jpg")
        self.assertEqual(
            paths["output_plate_topography"],
            ROOT / "regions" / "reunion" / "outputs" / "new-site-planche-topographique.jpg",
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
