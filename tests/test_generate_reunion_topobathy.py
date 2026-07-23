from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from osgeo import gdal, osr

from cache_manifest import (
    cache_artifact_keys,
    validate_cache_manifest,
    write_cache_manifest,
)
from generate_reunion_topobathy import (
    acquire,
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
            (Path(__file__).parents[1] / "sites" / "cap-la-houssaye.json").read_text(
                encoding="utf-8"
            )
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
                    "generate_reunion_topobathy.extract_hyscores",
                    side_effect=create_last_argument,
                ),
                patch(
                    "generate_reunion_topobathy.positive_depth",
                    side_effect=create_last_argument,
                ),
                patch(
                    "generate_reunion_topobathy.download_rge_alti",
                    side_effect=create_last_argument,
                ),
                patch(
                    "generate_reunion_topobathy.crop_raster",
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
            "generate_reunion_topobathy.urllib.request.urlopen",
            return_value=io.BytesIO(json.dumps(response).encode()),
        ):
            verify_orthophoto_capture_date(config)

        config["orthophoto_capture_date"] = "2025-07-22"
        with patch(
            "generate_reunion_topobathy.urllib.request.urlopen",
            return_value=io.BytesIO(json.dumps(response).encode()),
        ):
            with self.assertRaisesRegex(ValueError, "reports 2025-08-02"):
                verify_orthophoto_capture_date(config)


if __name__ == "__main__":
    unittest.main()
