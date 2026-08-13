from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from cartography.plate import _plate_paths, compose, font, format_dms
from cartography.config import ROOT


class FormatDmsTests(unittest.TestCase):
    def test_second_rounding_carries_into_minutes(self) -> None:
        value = 12 + 34 / 60 + 59.96 / 3600
        self.assertEqual(format_dms(value, "N", "S"), '12° 35\' 00.0" N')

    def test_second_rounding_carries_into_degrees_and_keeps_direction(self) -> None:
        value = -(12 + 59 / 60 + 59.96 / 3600)
        self.assertEqual(format_dms(value, "E", "O"), '13° 00\' 00.0" O')


class PlateConfigurationTests(unittest.TestCase):
    def test_default_paths_are_resolved_without_a_paths_object(self) -> None:
        config = {"slug": "new-site"}
        plan, relief, locator, output = _plate_paths(config, "topography")
        self.assertEqual(plan, ROOT / "regions" / "reunion" / "outputs" / "new-site-topobathy-2d.jpg")
        self.assertEqual(relief, ROOT / "regions" / "reunion" / "outputs" / "new-site-topobathy-3d.jpg")
        self.assertEqual(locator, ROOT / "regions" / "reunion" / "outputs" / "new-site-locator-reunion.jpg")
        self.assertEqual(
            output,
            ROOT / "regions" / "reunion" / "outputs" / "new-site-planche-topographique.jpg",
        )

    def test_interactive_relief_source_matches_the_web_view(self) -> None:
        config = {
            "slug": "new-site",
            "orthophoto_enabled": True,
            "plate_relief_source": "interactive",
        }
        _, relief, _, _ = _plate_paths(config, "orthophoto")
        self.assertEqual(
            relief,
            ROOT
            / "apps"
            / "web"
            / "public"
            / "maps"
            / "new-site"
            / "downloads"
            / "3d-dynamic-orthophoto-full.jpg",
        )

    def test_autonomous_region_interactive_relief_uses_regional_namespace(self) -> None:
        config = {
            "slug": "new-site",
            "region": "var-ouest",
            "orthophoto_enabled": True,
            "plate_relief_source": "interactive",
        }
        _, relief, _, _ = _plate_paths(config, "orthophoto")
        self.assertEqual(
            relief,
            ROOT
            / "apps"
            / "web"
            / "public"
            / "maps"
            / "var-ouest"
            / "new-site"
            / "maps"
            / "downloads"
            / "3d-dynamic-orthophoto-full.jpg",
        )

    def test_nonstandard_canvas_width_is_rejected_before_inputs_are_opened(self) -> None:
        config = {"plate_canvas_width_px": 4000}
        with patch("cartography.plate.validate_config") as validate:
            with self.assertRaisesRegex(
                ValueError,
                "plate_canvas_width_px must be 5400",
            ):
                compose(config, "topography")
        validate.assert_called_once_with(config)

    def test_missing_input_error_names_the_file_and_prerequisite(self) -> None:
        missing = ROOT / "regions" / "reunion" / "outputs" / "definitely-missing-test-image.jpg"
        resolved = (missing, Path("unused"), Path("unused"), Path("unused"))
        with (
            patch("cartography.plate.validate_config"),
            patch("cartography.plate._plate_paths", return_value=resolved),
        ):
            with self.assertRaisesRegex(
                FileNotFoundError,
                "Generate the site maps before composing the plate",
            ):
                compose({}, "topography")

    def test_font_error_includes_path_and_face_index(self) -> None:
        with patch("cartography.plate.ImageFont.truetype", side_effect=OSError):
            with self.assertRaisesRegex(
                RuntimeError,
                "missing-font.*face index 3",
            ):
                font("missing-font.ttc", 12, index=3)


if __name__ == "__main__":
    unittest.main()
