from __future__ import annotations

import inspect
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from osgeo import gdal, osr
from PIL import Image

from render_fused_relief import (
    bboxes_intersect,
    blend_texture,
    draw_interpolated_triangle,
    edge_preserving_bathy,
    expanded_bbox,
    fuse_bathymetry,
    imagery_alpha_across_shore,
    imagery_depth_alpha,
    load_font,
    make_pretty_3d_from_offshore,
    polyline_intersects_bbox,
    raster_bounds,
    sieve_land_components,
    webgl_lit_colors,
    warp_to_reference,
)
from site_config import DEFAULT_RELIEF_EXPOSURE, DEFAULT_VERTICAL_EXAGGERATION


def write_raster(
    path: Path,
    values: np.ndarray,
    transform: tuple[float, float, float, float, float, float],
    *,
    nodata: float | None = None,
) -> None:
    height, width = values.shape
    dataset = gdal.GetDriverByName("GTiff").Create(
        str(path),
        width,
        height,
        1,
        gdal.GDT_Float32,
    )
    spatial_ref = osr.SpatialReference()
    spatial_ref.ImportFromEPSG(32740)
    dataset.SetProjection(spatial_ref.ExportToWkt())
    dataset.SetGeoTransform(transform)
    band = dataset.GetRasterBand(1)
    if nodata is not None:
        band.SetNoDataValue(nodata)
    band.WriteArray(values.astype(np.float32))
    dataset = None


class RasterAlignmentTests(unittest.TestCase):
    def test_warp_uses_geography_instead_of_array_dimensions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reference = root / "reference.tif"
            shifted = root / "shifted.tif"
            write_raster(
                reference,
                np.zeros((2, 4), dtype=np.float32),
                (0.0, 1.0, 0.0, 2.0, 0.0, -1.0),
            )
            write_raster(
                shifted,
                np.tile(np.array([10.0, 20.0, 30.0, 40.0]), (2, 1)),
                (1.0, 1.0, 0.0, 2.0, 0.0, -1.0),
                nodata=-9999.0,
            )

            aligned = warp_to_reference(
                shifted,
                reference,
                resample_alg=gdal.GRA_NearestNeighbour,
            )
            values = aligned.GetRasterBand(1).ReadAsArray()

            self.assertEqual(raster_bounds(aligned), (0.0, 0.0, 4.0, 2.0))
            self.assertTrue(np.all(values[:, 0] == -9999.0))
            np.testing.assert_array_equal(values[:, 1:], [[10.0, 20.0, 30.0]] * 2)


class SurfaceValidityTests(unittest.TestCase):
    def test_cells_without_elevation_or_bathymetry_remain_invalid(self) -> None:
        depth = np.array([[4.0, np.nan], [np.nan, np.nan]], dtype=np.float32)
        bathymetry_valid = np.array([[True, False], [False, False]])
        elevation = np.array([[-2.0, np.nan], [3.0, np.nan]], dtype=np.float32)
        land = np.array([[False, False], [True, False]])

        _, sea = fuse_bathymetry(depth, bathymetry_valid, elevation, land, 20.0)

        np.testing.assert_array_equal(sea, [[True, False], [False, False]])
        np.testing.assert_array_equal(land | sea, [[True, False], [True, False]])

    def test_invalid_neighbors_do_not_deepen_valid_bathymetry(self) -> None:
        depth = np.full((7, 7), 30.0, dtype=np.float32)
        sea = np.zeros((7, 7), dtype=bool)
        sea[2:5, 2:5] = True
        depth[sea] = 1.0

        filtered = edge_preserving_bathy(depth, sea, passes=0)

        np.testing.assert_allclose(filtered[sea], 1.0)
        np.testing.assert_allclose(filtered[~sea], 30.0)

    def test_land_sieve_never_fills_original_water(self) -> None:
        land = np.ones((40, 40), dtype=bool)
        land[18:22, 18:22] = False

        sieved = sieve_land_components(land, threshold_px=100)

        self.assertFalse(np.any(sieved & ~land))
        self.assertFalse(np.any(sieved[18:22, 18:22]))


class ImageryMaskTests(unittest.TestCase):
    def test_orthophoto_depth_alpha_has_a_strict_maximum_depth(self) -> None:
        depths = np.array([0.0, 1.49, 1.5, 1.75, 2.0, 2.1, 8.0], dtype=np.float32)

        alpha = imagery_depth_alpha(depths, None, 0.6, 1.5, 2.0)

        self.assertIsNotNone(alpha)
        assert alpha is not None
        np.testing.assert_allclose(alpha[:3], 1.0)
        self.assertGreater(float(alpha[3]), 0.0)
        self.assertLess(float(alpha[3]), 1.0)
        np.testing.assert_allclose(alpha[4:], 0.0)

    def test_shallow_water_imagery_has_no_zero_alpha_seam_on_land(self) -> None:
        land = np.array([[False, False, True, True]])
        sea_alpha = np.array([[0.0, 1.0, 0.2, 0.0]], dtype=np.float32)

        alpha = imagery_alpha_across_shore(land, sea_alpha)

        np.testing.assert_allclose(alpha, [[0.0, 1.0, 1.0, 1.0]])

    def test_texture_fade_is_a_single_linear_composite(self) -> None:
        base = np.zeros((1, 1, 3), dtype=np.float32)
        texture = np.full((1, 1, 3), 200.0, dtype=np.float32)

        blended = blend_texture(base, texture, np.array([[0.5]], dtype=np.float32))

        np.testing.assert_allclose(blended, 100.0)


class ConfigurationDefaultTests(unittest.TestCase):
    def test_renderer_uses_shared_dimensionless_vertical_exaggeration_default(self) -> None:
        parameter = inspect.signature(make_pretty_3d_from_offshore).parameters[
            "vertical_exaggeration"
        ]
        self.assertEqual(parameter.default, DEFAULT_VERTICAL_EXAGGERATION)

    def test_missing_map_font_fails_instead_of_changing_typography(self) -> None:
        with patch(
            "render_fused_relief.ImageFont.truetype",
            side_effect=OSError("missing"),
        ):
            with self.assertRaisesRegex(RuntimeError, "required map font"):
                load_font(20)


class IsobathLabelPlacementTests(unittest.TestCase):
    def test_label_clearance_detects_a_nearby_isobath(self) -> None:
        text_bbox = (20.0, 15.0, 60.0, 28.0)
        nearby_isobath = [(0.0, 8.0), (80.0, 8.0)]

        self.assertFalse(polyline_intersects_bbox(nearby_isobath, text_bbox))
        self.assertTrue(
            polyline_intersects_bbox(
                nearby_isobath,
                expanded_bbox(text_bbox, 8.0),
            )
        )

    def test_expanded_label_boxes_prevent_near_collisions(self) -> None:
        first = (10.0, 10.0, 40.0, 25.0)
        second = (45.0, 10.0, 75.0, 25.0)

        self.assertFalse(bboxes_intersect(first, second))
        self.assertTrue(
            bboxes_intersect(
                expanded_bbox(first, 4.0),
                expanded_bbox(second, 4.0),
            )
        )


class ReliefLightingTests(unittest.TestCase):
    def test_default_exposure_brightens_radiance_before_srgb_conversion(self) -> None:
        colors = np.full((3, 3, 3), 128.0, dtype=np.float32)
        z = np.zeros((3, 3), dtype=np.float32)

        reference = webgl_lit_colors(
            colors,
            z,
            pixel_size_m=1.0,
            vertical_exaggeration=DEFAULT_VERTICAL_EXAGGERATION,
            view_bearing_deg=180.0,
            exposure=1.0,
        )
        exposed = webgl_lit_colors(
            colors,
            z,
            pixel_size_m=1.0,
            vertical_exaggeration=DEFAULT_VERTICAL_EXAGGERATION,
            view_bearing_deg=180.0,
        )

        self.assertEqual(
            inspect.signature(webgl_lit_colors).parameters["exposure"].default,
            DEFAULT_RELIEF_EXPOSURE,
        )
        self.assertGreater(float(np.mean(exposed)), float(np.mean(reference)))

    def test_triangle_texture_interpolates_vertex_colors(self) -> None:
        canvas = Image.new("RGB", (12, 12), (0, 0, 0))

        draw_interpolated_triangle(
            canvas,
            [(1.0, 1.0), (10.0, 1.0), (1.0, 10.0)],
            np.asarray(
                [
                    [255.0, 0.0, 0.0],
                    [0.0, 255.0, 0.0],
                    [0.0, 0.0, 255.0],
                ],
                dtype=np.float32,
            ),
        )

        pixels = np.asarray(canvas)
        interior = pixels[np.any(pixels > 0, axis=2)]
        self.assertGreater(len(np.unique(interior, axis=0)), 10)
        self.assertTrue(np.any(np.all(interior > 0, axis=1)))

    def test_webgl_lighting_preserves_shape_and_display_range(self) -> None:
        colors = np.full((5, 7, 3), 128.0, dtype=np.float32)
        z = np.tile(np.linspace(-4.0, 4.0, 7, dtype=np.float32), (5, 1))

        lit = webgl_lit_colors(
            colors,
            z,
            pixel_size_m=1.0,
            vertical_exaggeration=DEFAULT_VERTICAL_EXAGGERATION,
            view_bearing_deg=180.0,
        )

        self.assertEqual(lit.shape, colors.shape)
        self.assertTrue(np.all(np.isfinite(lit)))
        self.assertGreaterEqual(float(lit.min()), 0.0)
        self.assertLessEqual(float(lit.max()), 255.0)
        self.assertGreater(float(np.ptp(lit[:, :, 0])), 0.0)

    def test_webgl_lighting_rejects_non_metric_pixel_size(self) -> None:
        with self.assertRaisesRegex(ValueError, "pixel_size_m"):
            webgl_lit_colors(
                np.ones((2, 2, 3), dtype=np.float32),
                np.zeros((2, 2), dtype=np.float32),
                pixel_size_m=0.0,
                vertical_exaggeration=DEFAULT_VERTICAL_EXAGGERATION,
                view_bearing_deg=180.0,
            )


if __name__ == "__main__":
    unittest.main()
