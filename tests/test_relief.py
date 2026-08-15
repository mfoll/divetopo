from __future__ import annotations

import inspect
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from osgeo import gdal, osr
from PIL import Image

from cartography.bathymetry_style import VALIDATED_BATHYMETRY_PALETTE
from cartography.relief import (
    analytic_isobath_coverages,
    bbox_contains_class,
    bboxes_intersect,
    blend_texture,
    clip_polyline_to_bbox,
    compass_point,
    deep_edge_nodata_display_mask,
    depth_locked_plan_render_scale,
    draw_interpolated_triangle,
    edge_preserving_bathy,
    extract_depth_locked_plan_isobaths,
    extract_isobaths,
    expanded_bbox,
    final_frame_layout,
    fill_deep_edge_nodata_at_maximum,
    fuse_bathymetry,
    imagery_alpha_across_shore,
    imagery_depth_alpha,
    interpolate_mesh_gaps,
    load_font,
    local_slope_shade,
    make_pretty_3d_from_offshore,
    palette,
    polyline_intersects_bbox,
    raster_bounds,
    screen_space_boundary_coverages,
    sieve_land_components,
    small_internal_mesh_gap_mask,
    webgl_lit_colors,
    warp_to_reference,
)
from cartography.config import DEFAULT_RELIEF_EXPOSURE, DEFAULT_VERTICAL_EXAGGERATION


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
    def test_final_frame_layout_reports_center_crop_for_fixed_decorations(self) -> None:
        scale, crop_x, crop_y, width, height = final_frame_layout(
            (1250, 1250),
            (2474, 1712),
        )
        self.assertAlmostEqual(scale, 2474 / 1250)
        self.assertEqual(crop_x, 0.0)
        self.assertAlmostEqual(crop_y, (1250 * scale - 1712) / 2.0)
        self.assertEqual((width, height), (2474, 1712))

    def test_depth_locked_plan_render_scale_avoids_final_upscaling(self) -> None:
        self.assertEqual(
            depth_locked_plan_render_scale(2.0, (450, 312), (2474, 1712)),
            6.0,
        )
        self.assertEqual(
            depth_locked_plan_render_scale(4.0, (800, 554), (2474, 1712)),
            4.0,
        )
        self.assertEqual(
            depth_locked_plan_render_scale(2.0, (450, 312), None),
            2.0,
        )

    def test_depth_locked_isobaths_do_not_contract_into_an_island(self) -> None:
        yy, xx = np.mgrid[:120, :120]
        radius = np.hypot(xx - 60.0, yy - 60.0)
        land = radius < 20.0
        sea = ~land
        depth = np.clip((radius - 20.0) * 0.8, 0.0, 40.0)

        legacy = extract_isobaths(depth, sea, (5,))[5]
        locked = extract_depth_locked_plan_isobaths(depth, sea, (5,))[5]

        def land_fraction(lines: list[list[tuple[float, float]]]) -> float:
            points = np.asarray([point for line in lines for point in line])
            x = np.clip(np.rint(points[:, 0]).astype(int), 0, 119)
            y = np.clip(np.rint(points[:, 1]).astype(int), 0, 119)
            return float(land[y, x].mean())

        self.assertGreater(land_fraction(legacy), 0.0)
        self.assertEqual(land_fraction(locked), 0.0)

    def test_coral_blue_scale_uses_the_validated_physical_anchors(self) -> None:
        from cartography.bathymetry_style import remap_bathymetric_depth

        remapped = remap_bathymetric_depth(
            np.array(
                [0.0, 5.0, 10.0, 15.0, 20.0, 30.0],
                dtype=np.float32,
            ),
            maximum_depth_m=30.0,
            depth_scale="coral_blue",
        )

        np.testing.assert_allclose(
            remapped / 30.0,
            [0.0, 0.34, 0.68, 0.82, 0.94, 1.0],
        )

    def test_coral_blue_reaches_the_final_blue_at_twenty_metres(self) -> None:
        from cartography.bathymetry_style import remap_bathymetric_depth

        remapped = remap_bathymetric_depth(
            np.array([0.0, 5.0, 10.0, 15.0, 20.0], dtype=np.float32),
            maximum_depth_m=20.0,
            depth_scale="coral_blue",
        )

        np.testing.assert_allclose(
            remapped / 20.0,
            [0.0, 0.34, 0.68, 0.82, 1.0],
        )

    def test_coral_blue_has_the_exact_validated_rgb_anchors(self) -> None:
        colours = palette(
            np.array(
                [
                    0.0,
                    2.5,
                    3.5,
                    4.25,
                    5.0,
                    5.75,
                    6.5,
                    7.25,
                    8.0,
                    8.75,
                    9.5,
                    10.0,
                    11.0,
                    12.0,
                    13.5,
                    15.0,
                    17.5,
                    20.0,
                    22.5,
                    25.0,
                    30.0,
                    40.0,
                ],
                dtype=np.float32,
            ),
            max_depth=40.0,
            scheme="coral_blue",
            depth_scale="coral_blue",
        )

        np.testing.assert_array_equal(
            colours,
            np.array(
                [
                    [250, 58, 54],
                    [248, 65, 48],
                    [250, 78, 43],
                    [252, 98, 38],
                    [255, 125, 34],
                    [255, 160, 32],
                    [255, 195, 38],
                    [250, 215, 46],
                    [225, 220, 58],
                    [175, 223, 74],
                    [100, 220, 105],
                    [45, 214, 150],
                    [10, 204, 190],
                    [0, 190, 220],
                    [15, 170, 224],
                    [30, 151, 224],
                    [28, 126, 207],
                    [25, 98, 181],
                    [22, 62, 150],
                    [18, 51, 134],
                    [12, 38, 112],
                    [6, 24, 82],
                ],
                dtype=np.uint8,
            ),
        )

    def test_coral_blue_rejects_sites_shallower_than_twenty_metres(self) -> None:
        from cartography.bathymetry_style import remap_bathymetric_depth

        with self.assertRaisesRegex(ValueError, "at least 20 m"):
            remap_bathymetric_depth(
                np.array([0.0, 10.0], dtype=np.float32),
                maximum_depth_m=19.0,
                depth_scale="coral_blue",
            )

    def test_compass_projects_cardinals_for_arbitrary_frame_bearings(self) -> None:
        center = (100.0, 100.0)
        distance = 50.0
        expected = {
            0.0: {
                0.0: (100.0, 50.0),
                90.0: (150.0, 100.0),
                180.0: (100.0, 150.0),
                270.0: (50.0, 100.0),
            },
            60.0: {
                0.0: (56.69873, 75.0),
                90.0: (125.0, 56.69873),
                180.0: (143.30127, 125.0),
                270.0: (75.0, 143.30127),
            },
            135.0: {
                0.0: (64.64466, 135.35534),
                90.0: (64.64466, 64.64466),
                180.0: (135.35534, 64.64466),
                270.0: (135.35534, 135.35534),
            },
        }

        for frame_bearing, positions in expected.items():
            for cardinal_bearing, target in positions.items():
                with self.subTest(
                    frame_bearing=frame_bearing,
                    cardinal_bearing=cardinal_bearing,
                ):
                    actual = compass_point(
                        center,
                        frame_bearing,
                        cardinal_bearing,
                        distance,
                    )
                    self.assertAlmostEqual(actual[0], target[0], places=5)
                    self.assertAlmostEqual(actual[1], target[1], places=5)

    def test_polyline_is_clipped_to_the_view_crop(self) -> None:
        lines = clip_polyline_to_bbox(
            [(-2.0, 1.0), (2.0, 1.0), (6.0, 1.0)],
            (0.0, 0.0, 4.0, 4.0),
        )

        self.assertEqual(lines, [[(0.0, 1.0), (2.0, 1.0), (4.0, 1.0)]])

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
    def test_local_slope_shade_is_orientation_independent(self) -> None:
        ramp = np.tile(np.arange(7, dtype=np.float32), (7, 1))
        valid = np.ones_like(ramp, dtype=bool)

        horizontal = local_slope_shade(
            ramp,
            valid,
            1.0,
            1.0,
            max_slope_deg=45.0,
            max_darkening=0.5,
            smoothing_passes=0,
        )
        vertical = local_slope_shade(
            ramp.T,
            valid,
            1.0,
            1.0,
            max_slope_deg=45.0,
            max_darkening=0.5,
            smoothing_passes=0,
        )

        np.testing.assert_allclose(horizontal, vertical.T)

    def test_local_slope_shade_does_not_create_a_mask_edge(self) -> None:
        depth = np.full((7, 7), 8.0, dtype=np.float32)
        sea = np.zeros_like(depth, dtype=bool)
        sea[1:6, 1:6] = True

        shaded = local_slope_shade(
            depth,
            sea,
            0.4,
            0.4,
            smoothing_passes=2,
        )

        np.testing.assert_allclose(shaded, 1.0)

    def test_cells_without_elevation_or_bathymetry_remain_invalid(self) -> None:
        depth = np.array([[4.0, np.nan], [np.nan, np.nan]], dtype=np.float32)
        bathymetry_valid = np.array([[True, False], [False, False]])
        elevation = np.array([[-2.0, np.nan], [3.0, np.nan]], dtype=np.float32)
        land = np.array([[False, False], [True, False]])

        _, sea = fuse_bathymetry(depth, bathymetry_valid, elevation, land, 20.0)

        np.testing.assert_array_equal(sea, [[True, False], [False, False]])
        np.testing.assert_array_equal(land | sea, [[True, False], [True, False]])

    def test_complete_source_can_disable_edge_feather_without_deepening(self) -> None:
        depth = np.full((9, 12), np.nan, dtype=np.float32)
        depth[:, :8] = np.linspace(8.0, 0.5, 8, dtype=np.float32)
        bathymetry_valid = np.isfinite(depth)
        elevation = np.full_like(depth, np.nan)
        elevation[:, 8:] = 2.0
        land = np.zeros_like(bathymetry_valid)
        land[:, 8:] = True

        fused, sea = fuse_bathymetry(
            depth,
            bathymetry_valid,
            elevation,
            land,
            45.0,
            source_edge_feather_px=0.0,
        )

        np.testing.assert_array_equal(sea, bathymetry_valid)
        np.testing.assert_allclose(fused[sea], depth[sea])

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

    def test_deep_offshore_edge_gap_gets_display_only_fill(self) -> None:
        depth = np.full((5, 6), 19.0, dtype=np.float32)
        valid = np.ones((5, 6), dtype=bool)
        valid[:, :2] = False
        land = np.zeros((5, 6), dtype=bool)

        display_mask = deep_edge_nodata_display_mask(
            depth,
            valid,
            land,
            max_depth=20.0,
            min_boundary_pixels=5,
        )

        np.testing.assert_array_equal(display_mask, ~valid)
        self.assertFalse(np.any(display_mask & valid))

    def test_opt_in_deep_edge_terrain_fill_is_flat_and_non_mutating(self) -> None:
        depth = np.full((10, 6), 39.0, dtype=np.float32)
        valid = np.ones((10, 6), dtype=bool)
        valid[:, :2] = False
        land = np.zeros((10, 6), dtype=bool)
        original_depth = depth.copy()
        original_valid = valid.copy()

        filled_depth, filled_valid, fill_mask = (
            fill_deep_edge_nodata_at_maximum(
                depth,
                valid,
                land,
                max_depth=40.0,
            )
        )

        np.testing.assert_array_equal(fill_mask, ~valid)
        np.testing.assert_array_equal(filled_depth[fill_mask], 40.0)
        np.testing.assert_array_equal(filled_valid, np.ones_like(valid))
        np.testing.assert_array_equal(depth, original_depth)
        np.testing.assert_array_equal(valid, original_valid)

    def test_site_local_deep_edge_threshold_can_follow_source_coverage(
        self,
    ) -> None:
        depth = np.full((10, 6), 31.0, dtype=np.float32)
        valid = np.ones((10, 6), dtype=bool)
        valid[:, :2] = False
        land = np.zeros((10, 6), dtype=bool)

        _, default_valid, default_mask = fill_deep_edge_nodata_at_maximum(
            depth,
            valid,
            land,
            max_depth=40.0,
        )
        self.assertFalse(np.any(default_mask))
        np.testing.assert_array_equal(default_valid, valid)

        filled_depth, filled_valid, fill_mask = (
            fill_deep_edge_nodata_at_maximum(
                depth,
                valid,
                land,
                max_depth=40.0,
                min_boundary_depth_m=30.0,
            )
        )
        np.testing.assert_array_equal(fill_mask, ~valid)
        np.testing.assert_array_equal(filled_depth[fill_mask], 40.0)
        np.testing.assert_array_equal(filled_valid, np.ones_like(valid))

    def test_shallow_or_land_adjacent_edge_gaps_remain_no_data(self) -> None:
        depth = np.full((5, 6), 19.0, dtype=np.float32)
        valid = np.ones((5, 6), dtype=bool)
        valid[:, :2] = False
        depth[2, 2] = 8.0
        land = np.zeros((5, 6), dtype=bool)

        shallow_mask = deep_edge_nodata_display_mask(
            depth,
            valid,
            land,
            max_depth=20.0,
            min_boundary_pixels=5,
        )
        self.assertFalse(np.any(shallow_mask))

        depth[2, 2] = 19.0
        land[2, 2] = True
        land_mask = deep_edge_nodata_display_mask(
            depth,
            valid,
            land,
            max_depth=20.0,
            min_boundary_pixels=5,
        )
        self.assertFalse(np.any(land_mask))

    def test_internal_deep_gap_remains_no_data(self) -> None:
        depth = np.full((5, 5), 19.0, dtype=np.float32)
        valid = np.ones((5, 5), dtype=bool)
        valid[2, 2] = False
        land = np.zeros((5, 5), dtype=bool)

        display_mask = deep_edge_nodata_display_mask(
            depth,
            valid,
            land,
            max_depth=20.0,
            min_boundary_pixels=1,
        )

        self.assertFalse(np.any(display_mask))

    def test_small_internal_sea_gap_can_be_interpolated_for_the_mesh(self) -> None:
        valid = np.ones((5, 5), dtype=bool)
        valid[2, 2] = False
        land = np.zeros((5, 5), dtype=bool)
        values = np.add.outer(
            np.arange(5, dtype=np.float32),
            np.arange(5, dtype=np.float32),
        )

        fill = small_internal_mesh_gap_mask(valid, land, max_component_pixels=1)
        interpolated = interpolate_mesh_gaps(values, fill, valid)

        self.assertTrue(fill[2, 2])
        self.assertAlmostEqual(float(interpolated[2, 2]), 4.0)
        self.assertFalse(valid[2, 2])

    def test_mesh_gap_fill_rejects_edges_large_gaps_and_land_neighbors(self) -> None:
        land = np.zeros((5, 5), dtype=bool)

        edge_valid = np.ones((5, 5), dtype=bool)
        edge_valid[0, 2] = False
        self.assertFalse(
            np.any(
                small_internal_mesh_gap_mask(
                    edge_valid,
                    land,
                    max_component_pixels=2,
                )
            )
        )

        large_valid = np.ones((5, 5), dtype=bool)
        large_valid[2, 2:4] = False
        self.assertFalse(
            np.any(
                small_internal_mesh_gap_mask(
                    large_valid,
                    land,
                    max_component_pixels=1,
                )
            )
        )

        coastal_valid = np.ones((5, 5), dtype=bool)
        coastal_valid[2, 2] = False
        coastal_land = land.copy()
        coastal_land[2, 1] = True
        self.assertFalse(
            np.any(
                small_internal_mesh_gap_mask(
                    coastal_valid,
                    coastal_land,
                    max_component_pixels=1,
                )
            )
        )


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
    def test_coral_is_the_selected_validation_palette(self) -> None:
        self.assertEqual(VALIDATED_BATHYMETRY_PALETTE, "coral_blue")

    def test_renderer_uses_shared_dimensionless_vertical_exaggeration_default(self) -> None:
        parameter = inspect.signature(make_pretty_3d_from_offshore).parameters[
            "vertical_exaggeration"
        ]
        self.assertEqual(parameter.default, DEFAULT_VERTICAL_EXAGGERATION)

    def test_missing_map_font_fails_instead_of_changing_typography(self) -> None:
        with patch(
            "cartography.relief.ImageFont.truetype",
            side_effect=OSError("missing"),
        ):
            with self.assertRaisesRegex(RuntimeError, "required map font"):
                load_font(20)


class AnalyticIsobathTextureTests(unittest.TestCase):
    def test_isobaths_are_derived_from_mesh_elevation_like_the_viewer(self) -> None:
        elevation = -np.tile(
            np.arange(41, dtype=np.float32),
            (5, 1),
        )
        outline, center = analytic_isobath_coverages(
            elevation,
            1.0,
            interval_m=5.0,
            maximum_depth_m=40.0,
            pixel_ratio=1.0,
        )

        self.assertGreater(float(outline[2, 5]), 0.95)
        self.assertGreater(float(center[2, 10]), 0.95)
        self.assertEqual(float(outline[2, 0]), 0.0)
        self.assertEqual(float(center[2, 40]), 0.0)

    def test_visible_land_sea_boundary_has_continuous_nested_coverages(self) -> None:
        surface_classes = np.zeros((9, 11), dtype=np.uint8)
        surface_classes[:, :5] = 1
        surface_classes[:, 5:] = 2
        outline, center = screen_space_boundary_coverages(
            surface_classes,
            outline_half_width_px=3.0,
            center_half_width_px=1.0,
        )

        self.assertGreater(float(outline[4, 4]), 0.95)
        self.assertGreater(float(center[4, 5]), 0.90)
        self.assertGreater(float(outline[4, 2]), float(center[4, 2]))
        self.assertEqual(float(outline[4, 0]), 0.0)


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

    def test_label_bbox_class_detection_rejects_land_pixels(self) -> None:
        surface_classes = np.array(
            [[2, 2, 2], [2, 1, 2], [2, 2, 2]],
            dtype=np.uint8,
        )

        self.assertTrue(bbox_contains_class(surface_classes, (0, 0, 2, 2), 1))
        self.assertFalse(bbox_contains_class(surface_classes, (0, 0, 1, 1), 1))
        self.assertFalse(bbox_contains_class(surface_classes, (4, 4, 7, 7), 1))

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
