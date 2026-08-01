from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from osgeo import gdal, osr

from cartography.config import bbox, paths_for, validate_config
from cartography.regions.reunion import render


EXPECTED_EPSG = 2154


def raster_bounds(dataset: gdal.Dataset) -> tuple[float, float, float, float]:
    transform = dataset.GetGeoTransform()
    left = transform[0]
    top = transform[3]
    right = left + dataset.RasterXSize * transform[1]
    bottom = top + dataset.RasterYSize * transform[5]
    return min(left, right), min(bottom, top), max(left, right), max(bottom, top)


def validate_raster(
    path: Path,
    description: str,
    *,
    extent: tuple[float, float, float, float],
    resolution: float,
    bands: int,
    require_depth: bool = False,
) -> None:
    dataset = gdal.Open(str(path), gdal.GA_ReadOnly)
    if dataset is None:
        raise FileNotFoundError(f"Missing {description}: {path}")
    spatial_ref = osr.SpatialReference(wkt=dataset.GetProjection())
    expected = osr.SpatialReference()
    expected.ImportFromEPSG(EXPECTED_EPSG)
    if not spatial_ref.IsSame(expected):
        raise ValueError(f"{description} is not EPSG:2154: {path}")
    if dataset.RasterCount != bands:
        raise ValueError(
            f"{description} has {dataset.RasterCount} bands, expected {bands}: {path}"
        )
    actual_extent = raster_bounds(dataset)
    tolerance = max(resolution * 1.05, 0.01)
    if any(
        abs(actual - expected_value) > tolerance
        for actual, expected_value in zip(actual_extent, extent)
    ):
        raise ValueError(
            f"{description} bounds {actual_extent} do not match {extent}: {path}"
        )
    transform = dataset.GetGeoTransform()
    if (
        abs(abs(transform[1]) - resolution) > resolution * 0.01
        or abs(abs(transform[5]) - resolution) > resolution * 0.01
    ):
        raise ValueError(f"{description} is not at {resolution:g} m: {path}")
    values = dataset.GetRasterBand(1).ReadAsArray().astype(np.float32)
    nodata = dataset.GetRasterBand(1).GetNoDataValue()
    valid = np.isfinite(values)
    if nodata is not None:
        valid &= values != nodata
    if not np.any(valid):
        raise ValueError(f"{description} contains no valid pixels: {path}")
    if require_depth and float(np.max(values[valid])) <= 1.0:
        raise ValueError(f"{description} contains no positive bathymetric depth: {path}")


def validate_cached_inputs(config: dict, paths: dict[str, Path]) -> None:
    context = bbox(config, "context_bbox_utm40s")
    focus = bbox(config, "focus_bbox_utm40s")
    context_resolution = float(config["context_topography_resolution_m"])
    validate_raster(
        paths["context_depth_raw"],
        "raw Litto3D context",
        extent=context,
        resolution=1.0,
        bands=1,
    )
    validate_raster(
        paths["context_depth"],
        "positive-depth context",
        extent=context,
        resolution=context_resolution,
        bands=1,
        require_depth=True,
    )
    validate_raster(
        paths["context_elevation"],
        "Litto3D elevation context",
        extent=context,
        resolution=context_resolution,
        bands=1,
    )
    validate_raster(
        paths["focus_depth"],
        "positive-depth focus",
        extent=focus,
        resolution=1.0,
        bands=1,
        require_depth=True,
    )
    validate_raster(
        paths["focus_elevation"],
        "Litto3D elevation focus",
        extent=focus,
        resolution=1.0,
        bands=1,
    )
    if config.get("orthophoto_enabled", False):
        validate_raster(
            paths["context_orthophoto"],
            "IGN BD ORTHO context",
            extent=context,
            resolution=float(config["orthophoto_3d_resolution_m"]),
            bands=3,
        )
        validate_raster(
            paths["focus_orthophoto"],
            "IGN BD ORTHO focus",
            extent=focus,
            resolution=float(config["orthophoto_resolution_m"]),
            bands=3,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a local Côte d’Azur site package")
    parser.add_argument("config", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--render-only", action="store_true")
    parser.add_argument(
        "--plan-only",
        action="store_true",
        help="Render only the two 2D plans; never create static 3D JPEGs.",
    )
    args = parser.parse_args()

    config_path = args.config.expanduser().resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    validate_config(config)
    if config.get("region") != "paca":
        raise ValueError("The Côte d’Azur pipeline requires region='paca'")
    paths = paths_for(config)
    validate_cached_inputs(config, paths)
    if args.check:
        print(f"Configuration and Côte d’Azur source rasters are valid: {config_path}")
        return 0
    render(config, paths, plan_only=args.plan_only)
    print(paths["output_2d"])
    print(paths["output_2d_ortho"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
