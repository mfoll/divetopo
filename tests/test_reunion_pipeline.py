from __future__ import annotations

import io
import json
import tempfile
import unittest
import urllib.parse
from pathlib import Path
from unittest.mock import patch

import numpy as np
from osgeo import gdal, osr

from cartography.bathymetry_fusion import (
    fuse_shom_points,
    reconcile_false_edges,
)
from cartography.cache import (
    cache_artifact_keys,
    validate_cache_manifest,
    write_cache_manifest,
)
from cartography.regions.reunion import (
    acquire,
    crop_raster,
    download_gebco_relief,
    download_orthophoto,
    render,
    resolve_hyscores_tiff,
    validate_raster,
    verify_orthophoto_capture_date,
)


def write_raster(path: Path, *, resolution: float = 1.0, bands: int = 1) -> None:
    dataset = gdal.GetDriverByName("GTiff").Create(
        str(path),
        10,
        10,
        bands,
        gdal.GDT_Float32,
    )
    spatial_ref = osr.SpatialReference()
    spatial_ref.ImportFromEPSG(32740)
    dataset.SetProjection(spatial_ref.ExportToWkt())
    dataset.SetGeoTransform((100.0, resolution, 0.0, 200.0, 0.0, -resolution))
    for index in range(1, bands + 1):
        dataset.GetRasterBand(index).WriteArray(
            np.full((10, 10), index, dtype=np.float32)
        )
    dataset = None


class CacheContractTests(unittest.TestCase):
    def test_false_edge_reconciliation_is_local_and_feathered(self) -> None:
        depth = np.full((80, 80), 20.0, dtype=np.float64)
        depth[:, 40:] = 34.0
        valid = np.ones_like(depth, dtype=bool)
        coordinates = np.arange(80, dtype=np.float64) + 0.5
        grid_east, grid_north = np.meshgrid(coordinates, coordinates)

        reconciled, weight = reconcile_false_edges(
            depth,
            valid,
            grid_east,
            grid_north,
            1.0,
            {
                "polylines_utm40s": [[[40.0, 5.0], [40.0, 75.0]]],
                "smoothing_m": 12.0,
                "inner_width_m": 5.0,
                "outer_width_m": 12.0,
                "minimum_depth_m": 18.0,
            },
        )

        self.assertGreater(float(weight[40, 39]), 0.99)
        self.assertLess(float(reconciled[40, 39]), 27.0)
        self.assertGreater(float(reconciled[40, 40]), 27.0)
        self.assertEqual(float(reconciled[40, 5]), 20.0)
        self.assertEqual(float(reconciled[40, 74]), 34.0)

    def test_local_shom_fusion_corrects_only_the_diagnosed_area(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.tif"
            output = root / "fused.tif"
            dataset = gdal.GetDriverByName("GTiff").Create(
                str(source),
                120,
                120,
                1,
                gdal.GDT_Float32,
            )
            spatial_ref = osr.SpatialReference()
            spatial_ref.ImportFromEPSG(32740)
            dataset.SetProjection(spatial_ref.ExportToWkt())
            dataset.SetGeoTransform((0.0, 1.0, 0.0, 120.0, 0.0, -1.0))
            raster = np.full((120, 120), 20.0, dtype=np.float32)
            raster[45:75, 45:75] = 10.0
            band = dataset.GetRasterBand(1)
            band.SetNoDataValue(-99999.0)
            band.WriteArray(raster)
            dataset = None

            datum_east = np.arange(10.5, 40.5, 2.0)
            datum_north = np.full(datum_east.shape, 100.5)
            control_east = np.array([52.5, 60.5, 68.5, 52.5, 60.5, 68.5])
            control_north = np.array([67.5, 67.5, 67.5, 59.5, 59.5, 59.5])
            east = np.concatenate((datum_east, control_east))
            north = np.concatenate((datum_north, control_north))
            shom_depth = np.full(east.shape, 18.0)

            stats = fuse_shom_points(
                source,
                output,
                east,
                north,
                shom_depth,
                {
                    "datum_fit_depth_range_m": [17.0, 19.0],
                    "minimum_datum_points": 10,
                    "control_bbox_utm40s": [45.0, 45.0, 75.0, 75.0],
                    "minimum_correction_m": 4.0,
                    "minimum_control_points": 4,
                    "kernel_sigma_m": 12.0,
                    "influence_start": 0.12,
                    "influence_full": 0.62,
                    "window_padding_m": 25.0,
                },
            )

            fused_dataset = gdal.Open(str(output))
            fused = fused_dataset.GetRasterBand(1).ReadAsArray()
            fused_dataset = None
            self.assertAlmostEqual(stats["datum_offset_m"], 2.0)
            self.assertEqual(stats["control_points"], 6)
            self.assertGreater(float(fused[60, 60]), 18.0)
            self.assertEqual(float(fused[5, 5]), 20.0)
            self.assertFalse((root / "fused.tif.part").exists())

    def test_plan_only_renders_two_maps_without_locator_or_static_relief(self) -> None:
        config = json.loads(
            (
                Path(__file__).parents[1]
                / "regions"
                / "reunion"
                / "sites"
                / "cap-la-houssaye.json"
            ).read_text(encoding="utf-8")
        )
        paths = {
            "focus_depth": Path("focus-depth.tif"),
            "focus_elevation": Path("focus-elevation.tif"),
            "focus_orthophoto": Path("focus-orthophoto.tif"),
            "output_2d": Path("topographic.jpg"),
            "output_2d_ortho": Path("orthophoto.jpg"),
        }

        with (
            patch("cartography.regions.reunion.make_clean_plan") as make_plan,
            patch("cartography.regions.reunion.make_locator_map") as make_locator,
            patch(
                "cartography.regions.reunion.make_pretty_3d_from_offshore"
            ) as make_relief,
        ):
            render(config, paths, plan_only=True)

        self.assertEqual(make_plan.call_count, 2)
        make_locator.assert_not_called()
        make_relief.assert_not_called()

    def test_static_zero_contour_is_topographic_only(self) -> None:
        config = json.loads(
            (
                Path(__file__).parents[1]
                / "regions"
                / "reunion"
                / "sites"
                / "cap-la-houssaye.json"
            ).read_text(encoding="utf-8")
        )
        config["relief_surface_draped_contours"] = True
        config["relief_surface_draped_zero_contour"] = True
        paths = {
            "context_depth": Path("context-depth.tif"),
            "context_elevation": Path("context-elevation.tif"),
            "context_orthophoto": Path("context-orthophoto.tif"),
            "output_3d": Path("topographic.jpg"),
            "output_3d_ortho": Path("orthophoto.jpg"),
        }

        with patch(
            "cartography.regions.reunion.make_pretty_3d_from_offshore"
        ) as make_relief:
            render(config, paths, relief_only=True)

        self.assertEqual(make_relief.call_count, 2)
        topographic_options = make_relief.call_args_list[0].kwargs
        orthophoto_options = make_relief.call_args_list[1].kwargs
        self.assertTrue(topographic_options["surface_draped_zero_contour"])
        self.assertFalse(orthophoto_options["surface_draped_zero_contour"])
        self.assertTrue(orthophoto_options["surface_draped_contours"])

    def test_gebco_warp_declares_gtiff_for_part_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "locator.tif"

            def fake_download(_url: str, path: Path) -> None:
                path.write_bytes(b"source")

            def fake_warp(path: str, *_args, **_kwargs) -> object:
                Path(path).write_bytes(b"projected")
                return object()

            with (
                patch(
                    "cartography.regions.reunion.download_file",
                    side_effect=fake_download,
                ),
                patch(
                    "cartography.regions.reunion.gdal.Warp",
                    side_effect=fake_warp,
                ) as warp,
                patch("cartography.regions.reunion.validate_raster"),
            ):
                download_gebco_relief(
                    (305000.0, 7628000.0, 386000.0, 7696000.0),
                    10,
                    10,
                    20,
                    "GEBCO_2024",
                    "https://example.invalid/wms",
                    output,
                )

            self.assertEqual(warp.call_args.kwargs["format"], "GTiff")
            self.assertTrue(output.exists())

    def test_crop_raster_declares_gtiff_for_part_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.tif"
            output = root / "crop.tif"
            write_raster(source)
            dataset = gdal.Open(str(source), gdal.GA_Update)
            dataset.GetRasterBand(1).WriteArray(
                np.arange(1, 101, dtype=np.float32).reshape((10, 10))
            )
            dataset = None

            crop_raster(
                source,
                (102.0, 192.0, 108.0, 198.0),
                output,
                content_kind="positive_depth",
            )

            self.assertTrue(output.exists())
            self.assertFalse((root / "crop.tif.part").exists())

    def test_expected_grid_passes_and_stale_resolution_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.tif"
            write_raster(path)

            validate_raster(
                path,
                "test raster",
                extent=(100.0, 190.0, 110.0, 200.0),
                resolution=1.0,
                bands=1,
                exact_extent=True,
            )
            with self.assertRaisesRegex(ValueError, "expected about 0.5 m"):
                validate_raster(
                    path,
                    "test raster",
                    extent=(100.0, 190.0, 110.0, 200.0),
                    resolution=0.5,
                    bands=1,
                )

    def test_explicit_hyscores_url_never_requires_a_directory_lookup(self) -> None:
        url = "https://example.invalid/pinned-source.tif"
        self.assertEqual(
            resolve_hyscores_tiff(
                {
                    "hyscores_tiff_url": url,
                    "hyscores_directory": "https://example.invalid/listing/",
                }
            ),
            url,
        )

    def test_georeferenced_but_empty_raster_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "empty.tif"
            write_raster(path)
            dataset = gdal.Open(str(path), gdal.GA_Update)
            dataset.GetRasterBand(1).WriteArray(np.zeros((10, 10), dtype=np.float32))
            dataset = None

            with self.assertRaisesRegex(ValueError, "no plausible varying"):
                validate_raster(
                    path,
                    "empty depth",
                    bands=1,
                    content_kind="positive_depth",
                )

    def test_manifest_rejects_source_changes_and_modified_artifacts(self) -> None:
        config = json.loads(
            (
                Path(__file__).parents[1]
                / "regions"
                / "reunion"
                / "sites"
                / "cap-la-houssaye.json"
            ).read_text(encoding="utf-8")
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = {
                key: root / f"{key}.tif"
                for key in cache_artifact_keys(config)
            }
            for index, path in enumerate(paths.values()):
                path.write_bytes(f"artifact-{index}".encode())

            write_cache_manifest(config, paths)
            validate_cache_manifest(config, paths, verify_hashes=True)

            changed_source = dict(config)
            changed_source["orthophoto_capture_date"] = "2001-01-01"
            with self.assertRaisesRegex(ValueError, "no longer match"):
                validate_cache_manifest(
                    changed_source,
                    paths,
                    verify_hashes=False,
                )

            paths["focus_depth"].write_bytes(b"modified")
            with self.assertRaisesRegex(ValueError, "changed since acquisition"):
                validate_cache_manifest(config, paths, verify_hashes=True)

    def test_rebuilt_parents_force_their_derived_rasters_to_rebuild(self) -> None:
        config = {
            "focus_bbox_utm40s": [2.0, 2.0, 8.0, 8.0],
            "context_bbox_utm40s": [0.0, 0.0, 10.0, 10.0],
            "hyscores_tiff_url": "https://example.invalid/source.tif",
            "topography_resolution_m": 1.0,
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = {
                key: root / f"{key}.tif"
                for key in (
                    "context_depth_raw",
                    "context_depth",
                    "context_elevation",
                    "focus_depth",
                    "focus_elevation",
                )
            }
            for key in ("context_depth", "focus_depth", "focus_elevation"):
                paths[key].write_bytes(b"stale")

            def create_last_argument(*args, **kwargs) -> None:
                output = args[-1]
                output.write_bytes(b"rebuilt")

            with (
                patch(
                    "cartography.regions.reunion.extract_hyscores",
                    side_effect=create_last_argument,
                ),
                patch(
                    "cartography.regions.reunion.positive_depth",
                    side_effect=create_last_argument,
                ),
                patch(
                    "cartography.regions.reunion.download_rge_alti",
                    side_effect=create_last_argument,
                ),
                patch(
                    "cartography.regions.reunion.crop_raster",
                    side_effect=create_last_argument,
                ),
            ):
                rebuilt = acquire(config, paths, refresh=False)

            self.assertTrue(
                {
                    "context_depth_raw",
                    "context_depth",
                    "focus_depth",
                    "context_elevation",
                    "focus_elevation",
                }.issubset(rebuilt)
            )


class OrthophotoProvenanceTests(unittest.TestCase):
    def test_large_orthophoto_is_downloaded_as_aligned_tiles(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "orthophoto.tif"
            calls: list[tuple[int, int]] = []

            def write_tile(url: str, path: Path, *, timeout: int = 120) -> None:
                del timeout
                query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
                width = int(query["WIDTH"][0])
                height = int(query["HEIGHT"][0])
                min_x, min_y, max_x, max_y = map(
                    float,
                    query["BBOX"][0].split(","),
                )
                calls.append((width, height))
                dataset = gdal.GetDriverByName("GTiff").Create(
                    str(path),
                    width,
                    height,
                    3,
                    gdal.GDT_Byte,
                )
                spatial_ref = osr.SpatialReference()
                spatial_ref.ImportFromEPSG(32740)
                dataset.SetProjection(spatial_ref.ExportToWkt())
                dataset.SetGeoTransform(
                    (
                        min_x,
                        (max_x - min_x) / width,
                        0.0,
                        max_y,
                        0.0,
                        -(max_y - min_y) / height,
                    )
                )
                gradient = np.add.outer(
                    np.arange(height, dtype=np.uint8),
                    np.arange(width, dtype=np.uint8),
                )
                for band_index in range(1, 4):
                    dataset.GetRasterBand(band_index).WriteArray(
                        gradient + band_index * 20
                    )
                dataset = None

            with (
                patch("cartography.regions.reunion.WMS_MAX_TILE_PIXELS", 4),
                patch(
                    "cartography.regions.reunion.download_file",
                    side_effect=write_tile,
                ),
            ):
                download_orthophoto(
                    (100.0, 190.0, 110.0, 200.0),
                    1.0,
                    "test-layer",
                    output,
                )

            dataset = gdal.Open(str(output))
            self.assertEqual((dataset.RasterXSize, dataset.RasterYSize), (10, 10))
            self.assertEqual(dataset.RasterCount, 3)
            self.assertEqual(dataset.GetGeoTransform(), (100.0, 1.0, 0.0, 200.0, 0.0, -1.0))
            self.assertEqual(len(calls), 9)
            self.assertTrue(all(width <= 4 and height <= 4 for width, height in calls))

    def test_capture_date_must_match_live_metadata(self) -> None:
        config = {
            "focus_bbox_utm40s": [0.0, 0.0, 10.0, 10.0],
            "locator_marker_utm40s": [5.0, 5.0],
            "orthophoto_capture_date": "2025-08-02",
            "orthophoto_layer": "test-layer",
        }
        response = {
            "features": [
                {"properties": {"date_vol": "2025-08-02"}},
            ]
        }
        with patch(
            "cartography.regions.reunion.urllib.request.urlopen",
            return_value=io.BytesIO(json.dumps(response).encode()),
        ) as urlopen:
            verify_orthophoto_capture_date(config)
        query = urllib.parse.parse_qs(
            urllib.parse.urlparse(urlopen.call_args.args[0]).query
        )
        self.assertEqual(query["FORMAT"], ["image/geotiff"])

        config["orthophoto_capture_date"] = "2025-07-22"
        with patch(
            "cartography.regions.reunion.urllib.request.urlopen",
            return_value=io.BytesIO(json.dumps(response).encode()),
        ):
            with self.assertRaisesRegex(ValueError, "reports 2025-08-02"):
                verify_orthophoto_capture_date(config)


if __name__ == "__main__":
    unittest.main()
