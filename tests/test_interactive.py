from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from osgeo import gdal
from PIL import Image

from cartography.interactive import (
    DEFAULT_GRID_MAX,
    DEFAULT_OUTPUT,
    DEFAULT_VECTOR_ISOBATH_MAX_POINTS,
    DEFAULT_VECTOR_ISOBATH_MAX_POLYLINES,
    artifact_record,
    complete_interactive_deep_edge_nodata,
    correct_interactive_shallow_basin,
    fitted_dimensions,
    interactive_footprint_mask,
    interactive_source_paths,
    isobath_source_vertex_mask,
    static_view_horizontal_center_offset_m,
    static_view_along_center_offset_m,
    swap_output,
    validate_export,
    view_center_metadata,
)
from cartography.config import ROOT, interactive_footprint_bounds


class InteractiveTerrainPackageTests(unittest.TestCase):
    def test_default_output_is_owned_by_the_map_pipeline(self) -> None:
        self.assertEqual(
            DEFAULT_OUTPUT,
            ROOT / "regions" / "reunion" / "outputs" / "interactive-terrain",
        )

    def test_heightfield_resize_preserves_footprint_vertices(self) -> None:
        self.assertEqual(DEFAULT_GRID_MAX, 513)
        self.assertEqual(
            fitted_dimensions(
                769,
                385,
                DEFAULT_GRID_MAX,
                preserve_vertices=True,
            ),
            (513, 257),
        )

    def test_interactive_extent_uses_context_rasters_without_mutating_paths(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths: dict[str, Path] = {}
            source_values = np.arange(100, dtype=np.float32).reshape(10, 10)
            for key in (
                "context_depth",
                "context_elevation",
                "context_orthophoto",
            ):
                source_path = root / f"{key}.tif"
                bands = 3 if key == "context_orthophoto" else 1
                dataset = gdal.GetDriverByName("GTiff").Create(
                    str(source_path),
                    10,
                    10,
                    bands,
                    gdal.GDT_Float32,
                )
                dataset.SetGeoTransform((0.0, 1.0, 0.0, 10.0, 0.0, -1.0))
                for band_index in range(1, bands + 1):
                    dataset.GetRasterBand(band_index).WriteArray(source_values)
                dataset = None
                paths[key] = source_path
            original_paths = dict(paths)

            config = {
                "slug": "example",
                "interactive_bbox_utm40s": [2.0, 3.0, 8.0, 9.0],
            }
            with interactive_source_paths(config, paths) as cropped:
                for key in (
                    "focus_depth",
                    "focus_elevation",
                    "focus_orthophoto",
                ):
                    dataset = gdal.Open(str(cropped[key]))
                    self.assertEqual(
                        (dataset.RasterXSize, dataset.RasterYSize),
                        (6, 6),
                    )
                    self.assertEqual(
                        dataset.GetGeoTransform(),
                        (2.0, 1.0, 0.0, 9.0, 0.0, -1.0),
                    )
                    dataset = None
            self.assertEqual(paths, original_paths)

    def test_oriented_interactive_extent_crops_its_axis_aligned_envelope(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths: dict[str, Path] = {}
            values = np.arange(100, dtype=np.float32).reshape(10, 10)
            for key in (
                "context_depth",
                "context_elevation",
                "context_orthophoto",
            ):
                source_path = root / f"{key}.tif"
                bands = 3 if key == "context_orthophoto" else 1
                dataset = gdal.GetDriverByName("GTiff").Create(
                    str(source_path),
                    10,
                    10,
                    bands,
                    gdal.GDT_Float32,
                )
                dataset.SetGeoTransform((0.0, 1.0, 0.0, 10.0, 0.0, -1.0))
                for band_index in range(1, bands + 1):
                    dataset.GetRasterBand(band_index).WriteArray(values)
                dataset = None
                paths[key] = source_path

            config = {
                "slug": "example",
                "interactive_footprint_utm40s": {
                    "center": [5.0, 5.0],
                    "width_m": 4.0,
                    "depth_m": 6.0,
                    "look_bearing_deg": 0.0,
                },
            }
            with interactive_source_paths(config, paths) as cropped:
                dataset = gdal.Open(str(cropped["focus_depth"]))
                self.assertEqual(
                    (dataset.RasterXSize, dataset.RasterYSize),
                    (4, 6),
                )
                self.assertEqual(
                    dataset.GetGeoTransform(),
                    (3.0, 1.0, 0.0, 8.0, 0.0, -1.0),
                )
                dataset = None

    def test_oriented_interactive_mask_keeps_only_the_rectangle(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            raster_path = Path(directory) / "surface.tif"
            dataset = gdal.GetDriverByName("GTiff").Create(
                str(raster_path),
                11,
                11,
                1,
                gdal.GDT_Float32,
            )
            dataset.SetGeoTransform((0.0, 1.0, 0.0, 11.0, 0.0, -1.0))
            dataset.GetRasterBand(1).WriteArray(
                np.zeros((11, 11), dtype=np.float32)
            )
            dataset = None
            config = {
                "interactive_footprint_utm40s": {
                    "center": [5.5, 5.5],
                    "width_m": 4.0,
                    "depth_m": 8.0,
                    "look_bearing_deg": 45.0,
                },
            }

            mask = interactive_footprint_mask(
                config,
                raster_path,
                (11, 11),
            )

            self.assertTrue(mask[5, 5])
            self.assertFalse(mask[0, 0])
            self.assertFalse(mask[0, -1])
            self.assertFalse(mask[-1, 0])
            self.assertFalse(mask[-1, -1])
            self.assertGreater(np.count_nonzero(mask), 25)
            self.assertLess(np.count_nonzero(mask), 50)

    def test_interactive_deep_edge_completion_is_opt_in_and_flat(self) -> None:
        surface = np.full((10, 6), -39.0, dtype=np.float32)
        depth = np.full((10, 6), 39.0, dtype=np.float32)
        valid = np.ones((10, 6), dtype=bool)
        valid[:, :2] = False
        land = np.zeros((10, 6), dtype=bool)

        completed_surface, completed_depth, completed_valid, fill_mask = (
            complete_interactive_deep_edge_nodata(
                {
                    "max_depth_m": 40.0,
                    "deep_edge_nodata_terrain_fill": True,
                },
                surface,
                depth,
                land,
                valid,
            )
        )

        np.testing.assert_array_equal(fill_mask, ~valid)
        np.testing.assert_array_equal(completed_surface[fill_mask], -40.0)
        np.testing.assert_array_equal(completed_depth[fill_mask], 40.0)
        np.testing.assert_array_equal(completed_valid, np.ones_like(valid))
        np.testing.assert_array_equal(surface, np.full_like(surface, -39.0))
        np.testing.assert_array_equal(depth, np.full_like(depth, 39.0))

    def test_shallow_basin_correction_interpolates_only_its_bounded_mesh(self) -> None:
        surface = np.full((7, 7), -1.0, dtype=np.float32)
        depth = np.full((7, 7), 1.0, dtype=np.float32)
        valid = np.ones((7, 7), dtype=bool)
        surface[2:5, 2:5] = -40.0
        depth[2:5, 2:5] = 40.0
        valid[3, 3] = False
        config = {
            "interactive_shallow_basin_correction_bbox_utm40s": [
                2.0,
                2.0,
                5.0,
                5.0,
            ],
            "interactive_shallow_basin_max_boundary_depth_m": 2.5,
        }

        corrected_surface, corrected_depth, corrected_valid, correction = (
            correct_interactive_shallow_basin(
                config,
                surface,
                depth,
                valid,
                (0.0, 1.0, 0.0, 7.0, 0.0, -1.0),
            )
        )

        expected = np.zeros((7, 7), dtype=bool)
        expected[2:5, 2:5] = True
        np.testing.assert_array_equal(correction, expected)
        np.testing.assert_allclose(corrected_surface[correction], -1.0)
        np.testing.assert_allclose(corrected_depth[correction], 1.0)
        self.assertTrue(np.all(corrected_valid))
        np.testing.assert_array_equal(surface[:2], corrected_surface[:2])

    def test_shallow_basin_correction_rejects_a_deep_boundary(self) -> None:
        surface = np.full((7, 7), -1.0, dtype=np.float32)
        surface[1, 3] = -3.0
        depth = np.maximum(-surface, 0.0)
        valid = np.ones((7, 7), dtype=bool)
        config = {
            "interactive_shallow_basin_correction_bbox_utm40s": [
                2.0,
                2.0,
                5.0,
                5.0,
            ],
            "interactive_shallow_basin_max_boundary_depth_m": 2.5,
        }

        with self.assertRaisesRegex(ValueError, "beyond its configured"):
            correct_interactive_shallow_basin(
                config,
                surface,
                depth,
                valid,
                (0.0, 1.0, 0.0, 7.0, 0.0, -1.0),
            )

    def test_isobath_mask_suppresses_every_filled_transition_cell(self) -> None:
        fill = np.zeros((5, 5), dtype=bool)
        fill[2, 2] = True

        safe = isobath_source_vertex_mask(fill, (5, 5))

        expected = np.ones((5, 5), dtype=bool)
        expected[1:4, 1:4] = False
        np.testing.assert_array_equal(safe, expected)
        for row in range(4):
            for column in range(4):
                corners = safe[row : row + 2, column : column + 2]
                fill_corners = fill[row : row + 2, column : column + 2]
                if np.any(fill_corners):
                    self.assertFalse(np.any(corners))

    def test_isobath_mask_is_all_source_without_completion(self) -> None:
        fill = np.zeros((9, 7), dtype=bool)

        np.testing.assert_array_equal(
            isobath_source_vertex_mask(fill, (5, 4)),
            np.ones((4, 5), dtype=bool),
        )

    def test_isobath_mask_never_marks_invalid_vertices_as_source(self) -> None:
        fill = np.zeros((5, 5), dtype=bool)
        valid = np.ones((5, 5), dtype=bool)
        valid[2, 3] = False

        safe = isobath_source_vertex_mask(fill, (5, 5), valid)

        self.assertFalse(safe[2, 3])
        np.testing.assert_array_equal(safe, valid)

    def test_isobath_mask_keeps_sparse_fill_when_downsampling(self) -> None:
        fill = np.zeros((100, 100), dtype=bool)
        fill[49, 49] = True

        safe = isobath_source_vertex_mask(fill, (5, 5))

        self.assertLess(np.count_nonzero(safe), safe.size)

    def test_static_horizontal_center_is_opt_in(self) -> None:
        self.assertIsNone(
            static_view_horizontal_center_offset_m(
                {
                    "context_bbox_utm40s": [0.0, 0.0, 1000.0, 1000.0],
                    "view_bearing_deg": 0.0,
                },
                (100.0, 100.0, 900.0, 900.0),
            )
        )

    def test_static_horizontal_center_uses_screen_right_sign_convention(
        self,
    ) -> None:
        base_config = {
            "interactive_match_static_horizontal_center": True,
            "context_bbox_utm40s": [0.0, 0.0, 1000.0, 1000.0],
            "view_center_offset_east_m": 100.0,
            "view_center_offset_north_m": 50.0,
        }
        focus_bounds = (100.0, 100.0, 900.0, 900.0)

        looking_north = {
            **base_config,
            "view_bearing_deg": 0.0,
        }
        self.assertAlmostEqual(
            static_view_horizontal_center_offset_m(
                looking_north,
                focus_bounds,
            ),
            100.0,
        )

        looking_east = {
            **base_config,
            "view_bearing_deg": 90.0,
        }
        self.assertAlmostEqual(
            static_view_horizontal_center_offset_m(
                looking_east,
                focus_bounds,
            ),
            -50.0,
        )

    def test_static_along_center_uses_forward_axis_sign_convention(self) -> None:
        base_config = {
            "interactive_match_static_along_center": True,
            "context_bbox_utm40s": [0.0, 0.0, 1000.0, 1000.0],
            "view_center_offset_east_m": 100.0,
            "view_center_offset_north_m": 50.0,
        }
        focus_bounds = (100.0, 100.0, 900.0, 900.0)

        self.assertAlmostEqual(
            static_view_along_center_offset_m(
                {**base_config, "view_bearing_deg": 0.0},
                focus_bounds,
            ),
            50.0,
        )
        self.assertAlmostEqual(
            static_view_along_center_offset_m(
                {**base_config, "view_bearing_deg": 90.0},
                focus_bounds,
            ),
            100.0,
        )

    def test_along_center_metadata_prefers_explicit_override(self) -> None:
        config = {
            "interactive_match_static_along_center": True,
            "interactive_view_along_center_offset_m": -12.3456789,
            "context_bbox_utm40s": [0.0, 0.0, 1000.0, 1000.0],
            "view_center_offset_east_m": 100.0,
            "view_center_offset_north_m": 50.0,
            "view_bearing_deg": 90.0,
        }

        self.assertEqual(
            view_center_metadata(
                config,
                (100.0, 100.0, 900.0, 900.0),
            ),
            {"alongCenterOffsetM": -12.345679},
        )

    def test_horizontal_center_metadata_prefers_explicit_override(self) -> None:
        config = {
            "interactive_match_static_horizontal_center": True,
            "interactive_view_horizontal_center_offset_m": -12.3456789,
            "context_bbox_utm40s": [0.0, 0.0, 1000.0, 1000.0],
            "view_center_offset_east_m": 100.0,
            "view_center_offset_north_m": 50.0,
            "view_bearing_deg": 90.0,
        }

        self.assertEqual(
            view_center_metadata(
                config,
                (100.0, 100.0, 900.0, 900.0),
            ),
            {"horizontalCenterOffsetM": -12.345679},
        )

    def test_two_corrected_sites_export_their_static_horizontal_centres(
        self,
    ) -> None:
        expected_offsets = {
            "passe-hermitage": 0.0,
            "pont-rouge": 0.0,
        }
        for slug, expected in expected_offsets.items():
            config = json.loads(
                (ROOT / "regions" / "reunion" / "sites" / f"{slug}.json").read_text(encoding="utf-8")
            )
            metadata = json.loads(
                (
                    ROOT
                    / "regions"
                    / "reunion"
                    / "outputs"
                    / "interactive-terrain"
                    / slug
                    / "terrain.json"
                ).read_text(encoding="utf-8")
            )
            with self.subTest(slug=slug):
                calculated = static_view_horizontal_center_offset_m(
                    config,
                    interactive_footprint_bounds(config),
                )
                self.assertIsNotNone(calculated)
                assert calculated is not None
                self.assertAlmostEqual(calculated, expected, delta=0.05)
                self.assertAlmostEqual(
                    metadata["view"]["horizontalCenterOffsetM"],
                    calculated,
                    delta=0.05,
                )

    def test_atomic_swap_removes_stale_previous_sites(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output_root = root / "interactive-terrain"
            output_root.mkdir()
            (output_root / "stale.txt").write_text("stale", encoding="utf-8")
            build_root = root / "build"
            build_root.mkdir()
            (build_root / "manifest.json").write_text("{}\n", encoding="utf-8")

            swap_output(build_root, output_root)

            self.assertFalse((output_root / "stale.txt").exists())
            self.assertTrue((output_root / "manifest.json").is_file())

    def test_manifest_records_validate_site_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_root = Path(directory)
            site_root = output_root / "example"
            site_root.mkdir()

            metadata = site_root / "terrain.json"
            metadata.write_text(
                """
{
  "grid": {
    "width": 2,
    "height": 2,
    "heightFile": "height.bin",
    "validMaskFile": "valid-mask.bin",
    "isobathMaskFile": "isobath-mask.bin",
    "vectorIsobathsFile": "isobaths-vector.json"
  },
  "textures": {
    "width": 2,
    "height": 2,
    "topographic": {"file": "topographic.webp"},
    "orthophoto": {"file": "orthophoto.webp"}
  }
}
""".strip()
                + "\n",
                encoding="utf-8",
            )
            height = site_root / "height.bin"
            height.write_bytes(b"\x00\x00" * 4)
            valid_mask = site_root / "valid-mask.bin"
            valid_mask.write_bytes(b"\x0f")
            isobath_mask = site_root / "isobath-mask.bin"
            isobath_mask.write_bytes(b"\x0f")
            vector_isobaths = site_root / "isobaths-vector.json"
            vector_isobaths.write_text(
                '{"coordinateSpace":"grid-pixels","levels":{"5":[]}}\n',
                encoding="utf-8",
            )
            topographic = site_root / "topographic.webp"
            orthophoto = site_root / "orthophoto.webp"
            Image.new("RGB", (2, 2), "red").save(topographic, "WEBP")
            Image.new("RGB", (2, 2), "blue").save(orthophoto, "WEBP")

            manifest = {
                "schemaVersion": 2,
                "sites": [
                    {
                        "slug": "example",
                        "title": "Example",
                        "metadata": "example/terrain.json",
                        "files": {
                            "metadata": artifact_record(metadata, output_root),
                            "height": artifact_record(height, output_root),
                            "validMask": artifact_record(valid_mask, output_root),
                            "isobathMask": artifact_record(
                                isobath_mask,
                                output_root,
                            ),
                            "vectorIsobaths": artifact_record(
                                vector_isobaths,
                                output_root,
                            ),
                            "topographicTexture": artifact_record(
                                topographic,
                                output_root,
                            ),
                            "orthophotoTexture": artifact_record(
                                orthophoto,
                                output_root,
                            ),
                        },
                    }
                ],
            }

            validate_export(output_root, manifest)
            height.write_bytes(b"\x00\x00")
            with self.assertRaisesRegex(ValueError, "artifact size"):
                validate_export(output_root, manifest)

            height.write_bytes(b"\x00\x00" * 4)
            metadata_payload = json.loads(
                metadata.read_text(encoding="utf-8")
            )
            metadata_payload["grid"]["width"] = DEFAULT_GRID_MAX + 1
            metadata.write_text(
                json.dumps(metadata_payload),
                encoding="utf-8",
            )
            manifest["sites"][0]["files"]["metadata"] = artifact_record(
                metadata,
                output_root,
            )
            with self.assertRaisesRegex(
                ValueError,
                "Heightfield dimensions",
            ):
                validate_export(output_root, manifest)

    def test_vector_payload_contract_bounds_draw_calls_and_points(self) -> None:
        self.assertGreater(DEFAULT_VECTOR_ISOBATH_MAX_POLYLINES, 16)
        self.assertGreater(DEFAULT_VECTOR_ISOBATH_MAX_POINTS, 1091)


if __name__ == "__main__":
    unittest.main()
