from __future__ import annotations

import inspect
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from osgeo import gdal, osr

from render_fused_relief import (
    blend_texture,
    edge_preserving_bathy,
    fuse_bathymetry,
    imagery_alpha_across_shore,
    imagery_depth_alpha,
    load_font,
    make_pretty_3d_from_offshore,
    raster_bounds,
    sieve_land_components,
    warp_to_reference,
)
from site_config import DEFAULT_VERTICAL_EXAGGERATION


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
        depths = np.array([0.0, 1.0, 1.5, 2.0, 2.1, 8.0], dtype=np.float32)

        alpha = imagery_depth_alpha(depths, None, 0.6, 1.0, 2.0)

        self.assertIsNotNone(alpha)
        assert alpha is not None
        np.testing.assert_allclose(alpha[:2], 1.0)
        self.assertGreater(float(alpha[2]), 0.0)
        self.assertLess(float(alpha[2]), 1.0)
        np.testing.assert_allclose(alpha[3:], 0.0)

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


if __name__ == "__main__":
    unittest.main()
