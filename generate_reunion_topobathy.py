from __future__ import annotations

import argparse
from datetime import date
import html
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import numpy as np
from osgeo import gdal, osr

from cache_manifest import (
    EXPECTED_CRS,
    GEBCO_LAYER,
    GEBCO_WMS,
    ORTHOPHOTO_LAYER,
    RGE_ALTI_LAYER,
    RGE_ALTI_WMS,
    preflight_cache_manifest,
    validate_cache_manifest,
    write_cache_manifest,
)
from render_fused_relief import make_clean_plan, make_locator_map, make_pretty_3d_from_offshore
from site_config import (
    DEFAULT_VERTICAL_EXAGGERATION,
    bbox,
    paths_for,
    validate_config,
)

gdal.UseExceptions()
osr.UseExceptions()


def run(command: list[str]) -> None:
    print("+", " ".join(command))
    subprocess.run(command, check=True)


def temporary_path(output: Path) -> Path:
    return output.with_name(f"{output.name}.part")


def download_file(url: str, output: Path, *, timeout: int = 120) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.unlink(missing_ok=True)
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response, output.open("wb") as handle:
            shutil.copyfileobj(response, handle)
    except Exception:
        output.unlink(missing_ok=True)
        raise


def open_raster(path: Path, description: str) -> gdal.Dataset:
    try:
        dataset = gdal.Open(str(path), gdal.GA_ReadOnly)
    except RuntimeError as error:
        raise ValueError(f"Invalid {description} at {path}: {error}") from error
    if dataset is None:
        raise ValueError(f"Cannot open {description}: {path}")
    return dataset


def raster_bounds(dataset: gdal.Dataset) -> tuple[float, float, float, float]:
    transform = dataset.GetGeoTransform()
    if transform[2] != 0.0 or transform[4] != 0.0:
        raise ValueError("Rotated rasters are not supported")
    left = transform[0]
    top = transform[3]
    right = left + dataset.RasterXSize * transform[1]
    bottom = top + dataset.RasterYSize * transform[5]
    return min(left, right), min(bottom, top), max(left, right), max(bottom, top)


def _is_expected_crs(dataset: gdal.Dataset) -> bool:
    projection = dataset.GetProjection()
    if not projection:
        return False
    spatial_ref = osr.SpatialReference(wkt=projection)
    expected = osr.SpatialReference()
    expected.ImportFromEPSG(32740)
    # IGN's WMS currently labels the correct UTM projection with an unnamed
    # WGS84 datum. Accept that known WKT while still rejecting another grid.
    return bool(spatial_ref.IsSame(expected)) or 'PROJCS["EPSG:32740"' in projection


def validate_raster_content(
    dataset: gdal.Dataset,
    description: str,
    path: Path,
    content_kind: str,
) -> None:
    """Reject empty or constant rasters that happen to have a plausible grid."""
    sample_width = min(dataset.RasterXSize, 512)
    sample_height = min(dataset.RasterYSize, 512)
    samples = [
        dataset.GetRasterBand(index).ReadAsArray(
            buf_xsize=sample_width,
            buf_ysize=sample_height,
        ).astype(np.float32)
        for index in range(1, dataset.RasterCount + 1)
    ]
    if content_kind == "rgb":
        values = np.stack(samples, axis=-1)
        usable = values[np.isfinite(values)]
        if usable.size == 0 or float(np.ptp(usable)) <= 1.0:
            raise ValueError(f"{description} has no varying image data: {path}")
        return

    values = samples[0]
    if content_kind == "hyscores_raw":
        usable = values[np.isfinite(values) & (values >= -80.0) & (values <= 100.0)]
        has_expected_signal = usable.size > 0 and np.any(usable < -0.01)
    elif content_kind == "positive_depth":
        usable = values[np.isfinite(values) & (values >= 0.0) & (values <= 80.0)]
        has_expected_signal = usable.size > 0 and np.any(usable > 0.01)
    elif content_kind == "elevation":
        usable = values[np.isfinite(values) & (values > -1000.0) & (values < 10000.0)]
        has_expected_signal = usable.size > 0 and np.any(usable > 0.01)
    else:
        raise ValueError(f"Unknown raster content contract: {content_kind}")
    if (
        not has_expected_signal
        or usable.size < 2
        or float(np.ptp(usable)) <= 0.01
    ):
        raise ValueError(
            f"{description} has no plausible varying {content_kind} data: {path}"
        )


def validate_raster(
    path: Path,
    description: str,
    *,
    extent: tuple[float, float, float, float] | None = None,
    resolution: float | None = None,
    bands: int | None = None,
    exact_extent: bool = False,
    reference: Path | None = None,
    content_kind: str | None = None,
) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing {description}: {path}")
    dataset = open_raster(path, description)
    if bands is not None and dataset.RasterCount != bands:
        raise ValueError(
            f"{description} must have {bands} band(s), found {dataset.RasterCount}: {path}"
        )
    if not _is_expected_crs(dataset):
        raise ValueError(f"{description} is not in {EXPECTED_CRS}: {path}")
    transform = dataset.GetGeoTransform()
    pixel_x, pixel_y = abs(transform[1]), abs(transform[5])
    if pixel_x <= 0.0 or pixel_y <= 0.0:
        raise ValueError(f"{description} has an invalid pixel size: {path}")
    if resolution is not None:
        tolerance = max(1e-6, resolution * 0.01)
        if abs(pixel_x - resolution) > tolerance or abs(pixel_y - resolution) > tolerance:
            raise ValueError(
                f"{description} has {pixel_x:.6g} x {pixel_y:.6g} m pixels; "
                f"expected about {resolution:g} m: {path}"
            )
    if extent is not None:
        actual = raster_bounds(dataset)
        tolerance = 0.01 if exact_extent else max(pixel_x, pixel_y) * 1.05
        if any(abs(actual_value - expected_value) > tolerance for actual_value, expected_value in zip(actual, extent)):
            raise ValueError(
                f"{description} bounds {actual!r} do not match configured bounds {extent!r}: {path}"
            )
        if exact_extent and resolution is not None:
            expected_width = int(round((extent[2] - extent[0]) / resolution))
            expected_height = int(round((extent[3] - extent[1]) / resolution))
            if (dataset.RasterXSize, dataset.RasterYSize) != (expected_width, expected_height):
                raise ValueError(
                    f"{description} is {dataset.RasterXSize} x {dataset.RasterYSize} px; "
                    f"expected {expected_width} x {expected_height}: {path}"
                )
    if reference is not None:
        reference_dataset = open_raster(reference, f"reference raster for {description}")
        grid = (
            dataset.RasterXSize,
            dataset.RasterYSize,
            *dataset.GetGeoTransform(),
        )
        reference_grid = (
            reference_dataset.RasterXSize,
            reference_dataset.RasterYSize,
            *reference_dataset.GetGeoTransform(),
        )
        if any(abs(float(value) - float(expected)) > 1e-6 for value, expected in zip(grid, reference_grid)):
            raise ValueError(f"{description} is not aligned to {reference}: {path}")
    if content_kind is not None:
        validate_raster_content(dataset, description, path, content_kind)


def resolve_hyscores_tiff(config: dict) -> str:
    if config.get("hyscores_tiff_url"):
        return str(config["hyscores_tiff_url"])
    directory = str(config["hyscores_directory"]).rstrip("/") + "/"
    with urllib.request.urlopen(directory, timeout=60) as response:
        listing = response.read().decode("utf-8", errors="replace")
    candidates = [
        html.unescape(match)
        for match in re.findall(r'href="([^"]+MNTHS_flld[^"]+crop_TIFF\.tif)"', listing, flags=re.IGNORECASE)
    ]
    if not candidates:
        raise RuntimeError(f"No numeric HYSCORES GeoTIFF found in {directory}")
    return urllib.parse.urljoin(directory, candidates[0])


def extract_hyscores(source_url: str, extent: tuple[float, float, float, float], output: Path) -> None:
    min_x, min_y, max_x, max_y = extent
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = temporary_path(output)
    temporary.unlink(missing_ok=True)
    try:
        run(
            [
                "gdal_translate",
                "--config",
                "GDAL_DISABLE_READDIR_ON_OPEN",
                "EMPTY_DIR",
                "-projwin",
                str(min_x),
                str(max_y),
                str(max_x),
                str(min_y),
                "-of",
                "GTiff",
                "-co",
                "TILED=YES",
                "-co",
                "COMPRESS=DEFLATE",
                "-co",
                "PREDICTOR=3",
                f"/vsicurl/{source_url}",
                str(temporary),
            ]
        )
        validate_raster(
            temporary,
            "downloaded HYSCORES bathymetry",
            extent=extent,
            bands=1,
            content_kind="hyscores_raw",
        )
        os.replace(temporary, output)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def positive_depth(source: Path, output: Path) -> None:
    dataset = open_raster(source, "HYSCORES bathymetry")
    values = dataset.GetRasterBand(1).ReadAsArray().astype(np.float32)
    depth = np.where(np.isfinite(values) & (values >= -80.0) & (values <= 0.0), -values, -99999.0).astype(np.float32)

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = temporary_path(output)
    temporary.unlink(missing_ok=True)
    driver = gdal.GetDriverByName("GTiff")
    target = driver.Create(
        str(temporary),
        dataset.RasterXSize,
        dataset.RasterYSize,
        1,
        gdal.GDT_Float32,
        options=["TILED=YES", "COMPRESS=DEFLATE", "PREDICTOR=3"],
    )
    target.SetGeoTransform(dataset.GetGeoTransform())
    target.SetProjection(dataset.GetProjection())
    band = target.GetRasterBand(1)
    band.SetNoDataValue(-99999.0)
    band.WriteArray(depth)
    band.FlushCache()
    target = None
    validate_raster(
        temporary,
        "positive-depth bathymetry",
        bands=1,
        reference=source,
        content_kind="positive_depth",
    )
    os.replace(temporary, output)


def download_rge_alti(extent: tuple[float, float, float, float], resolution: float, output: Path) -> None:
    min_x, min_y, max_x, max_y = extent
    width = int(round((max_x - min_x) / resolution))
    height = int(round((max_y - min_y) / resolution))
    if width > 5000 or height > 5000:
        raise ValueError(f"RGE ALTI WMS request is too large: {width} x {height}; enlarge the resolution")
    query = urllib.parse.urlencode(
        {
            "SERVICE": "WMS",
            "VERSION": "1.3.0",
            "REQUEST": "GetMap",
            "LAYERS": RGE_ALTI_LAYER,
            "STYLES": "",
            "CRS": "EPSG:32740",
            "BBOX": f"{min_x},{min_y},{max_x},{max_y}",
            "WIDTH": width,
            "HEIGHT": height,
            "FORMAT": "image/geotiff",
        }
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = temporary_path(output)
    download_file(f"{RGE_ALTI_WMS}?{query}", temporary)
    try:
        validate_raster(
            temporary,
            "downloaded RGE ALTI topography",
            extent=extent,
            resolution=resolution,
            bands=1,
            exact_extent=True,
            content_kind="elevation",
        )
        os.replace(temporary, output)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def download_orthophoto(extent: tuple[float, float, float, float], resolution: float, layer: str, output: Path) -> None:
    min_x, min_y, max_x, max_y = extent
    width = int(round((max_x - min_x) / resolution))
    height = int(round((max_y - min_y) / resolution))
    if width > 5000 or height > 5000:
        raise ValueError(f"Orthophoto WMS request is too large: {width} x {height}; enlarge the resolution")
    query = urllib.parse.urlencode(
        {
            "SERVICE": "WMS",
            "VERSION": "1.3.0",
            "REQUEST": "GetMap",
            "LAYERS": layer,
            "STYLES": "",
            "CRS": "EPSG:32740",
            "BBOX": f"{min_x},{min_y},{max_x},{max_y}",
            "WIDTH": width,
            "HEIGHT": height,
            "FORMAT": "image/geotiff",
        }
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = temporary_path(output)
    download_file(f"{RGE_ALTI_WMS}?{query}", temporary)
    try:
        validate_raster(
            temporary,
            "downloaded IGN orthophoto",
            extent=extent,
            resolution=resolution,
            bands=3,
            exact_extent=True,
            content_kind="rgb",
        )
        os.replace(temporary, output)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def verify_orthophoto_capture_date(config: dict[str, Any]) -> None:
    marker_value = config.get("locator_marker_utm40s")
    if marker_value is None:
        min_x, min_y, max_x, max_y = bbox(config, "focus_bbox_utm40s")
        marker = ((min_x + max_x) / 2.0, (min_y + max_y) / 2.0)
    else:
        marker = tuple(map(float, marker_value))
    x, y = marker
    layer = str(config.get("orthophoto_layer", ORTHOPHOTO_LAYER))
    query = urllib.parse.urlencode(
        {
            "SERVICE": "WMS",
            "VERSION": "1.3.0",
            "REQUEST": "GetFeatureInfo",
            "LAYERS": layer,
            "QUERY_LAYERS": layer,
            "STYLES": "",
            "CRS": EXPECTED_CRS,
            "BBOX": f"{x - 1.0},{y - 1.0},{x + 1.0},{y + 1.0}",
            "WIDTH": 3,
            "HEIGHT": 3,
            "I": 1,
            "J": 1,
            "INFO_FORMAT": "application/json",
            "FEATURE_COUNT": 10,
        }
    )
    url = f"{RGE_ALTI_WMS}?{query}"
    with urllib.request.urlopen(url, timeout=60) as response:
        metadata = json.load(response)
    expected = str(config["orthophoto_capture_date"])
    properties = [
        feature.get("properties", {})
        for feature in metadata.get("features", [])
        if isinstance(feature, dict)
    ]
    dates = {
        match
        for prop in properties
        for match in re.findall(r"\d{4}-\d{2}-\d{2}", json.dumps(prop))
    }
    if expected not in dates:
        found = ", ".join(sorted(dates)) if dates else "no capture date"
        raise ValueError(
            f"IGN orthophoto metadata at the site reports {found}; "
            f"the configuration expects {expected}"
        )


def download_gebco_relief(
    extent_utm40s: tuple[float, float, float, float],
    target_width: int,
    target_height: int,
    request_width: int,
    layer: str,
    wms_url: str,
    output: Path,
) -> None:
    geographic = osr.SpatialReference()
    geographic.ImportFromEPSG(4326)
    geographic.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    projected = osr.SpatialReference()
    projected.ImportFromEPSG(32740)
    projected.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    to_wgs84 = osr.CoordinateTransformation(projected, geographic)
    min_x, min_y, max_x, max_y = extent_utm40s
    corners = [to_wgs84.TransformPoint(x, y) for x in (min_x, max_x) for y in (min_y, max_y)]
    longitudes = [point[0] for point in corners]
    latitudes = [point[1] for point in corners]
    min_lon, max_lon = min(longitudes), max(longitudes)
    min_lat, max_lat = min(latitudes), max(latitudes)
    mean_latitude = np.deg2rad((min_lat + max_lat) / 2.0)
    request_height = int(round(request_width * (max_lat - min_lat) / ((max_lon - min_lon) * np.cos(mean_latitude))))
    query = urllib.parse.urlencode(
        {
            "SERVICE": "WMS",
            "VERSION": "1.1.1",
            "REQUEST": "GetMap",
            "LAYERS": layer,
            "STYLES": "",
            "SRS": "EPSG:4326",
            "BBOX": f"{min_lon},{min_lat},{max_lon},{max_lat}",
            "WIDTH": request_width,
            "HEIGHT": request_height,
            "FORMAT": "image/tiff",
        }
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    geographic_tiff = output.with_suffix(".wgs84.part.tif")
    projected_tiff = temporary_path(output)
    geographic_tiff.unlink(missing_ok=True)
    projected_tiff.unlink(missing_ok=True)
    try:
        download_file(f"{wms_url}?{query}", geographic_tiff)
        result = gdal.Warp(
            str(projected_tiff),
            str(geographic_tiff),
            dstSRS=EXPECTED_CRS,
            outputBounds=extent_utm40s,
            width=target_width,
            height=target_height,
            resampleAlg=gdal.GRA_Cubic,
            creationOptions=["TILED=YES", "COMPRESS=DEFLATE"],
        )
        if result is None:
            raise RuntimeError("Failed to reproject the GEBCO locator relief")
        result = None
        validate_raster(
            projected_tiff,
            "GEBCO locator relief",
            extent=extent_utm40s,
            bands=3,
            exact_extent=True,
            content_kind="rgb",
        )
        os.replace(projected_tiff, output)
    finally:
        geographic_tiff.unlink(missing_ok=True)
        projected_tiff.unlink(missing_ok=True)


def crop_raster(
    source: Path,
    extent: tuple[float, float, float, float],
    output: Path,
    *,
    content_kind: str,
) -> None:
    min_x, min_y, max_x, max_y = extent
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = temporary_path(output)
    temporary.unlink(missing_ok=True)
    result = gdal.Translate(
        str(temporary),
        str(source),
        projWin=[min_x, max_y, max_x, min_y],
        creationOptions=["TILED=YES", "COMPRESS=DEFLATE", "PREDICTOR=3"],
    )
    if result is None:
        raise RuntimeError(f"Failed to crop {source}")
    result = None
    validate_raster(
        temporary,
        f"crop of {source.name}",
        extent=extent,
        bands=1,
        content_kind=content_kind,
    )
    os.replace(temporary, output)


def raster_summary(path: Path) -> str:
    try:
        dataset = open_raster(path, "raster")
    except (FileNotFoundError, ValueError):
        return f"missing: {path}"
    transform = dataset.GetGeoTransform()
    width_m = dataset.RasterXSize * abs(transform[1])
    height_m = dataset.RasterYSize * abs(transform[5])
    return f"{path.name}: {dataset.RasterXSize} x {dataset.RasterYSize} px, {width_m:.0f} x {height_m:.0f} m"


def acquire(config: dict, paths: dict[str, Path], refresh: bool) -> set[str]:
    """Acquire missing inputs and rebuild every derivative of a changed parent."""
    rebuilt: set[str] = set()
    focus = bbox(config, "focus_bbox_utm40s")
    context = bbox(config, "context_bbox_utm40s")
    if refresh or not paths["context_depth_raw"].exists():
        source_url = resolve_hyscores_tiff(config)
        extract_hyscores(source_url, context, paths["context_depth_raw"])
        rebuilt.add("context_depth_raw")
    if (
        refresh
        or "context_depth_raw" in rebuilt
        or not paths["context_depth"].exists()
    ):
        positive_depth(paths["context_depth_raw"], paths["context_depth"])
        rebuilt.add("context_depth")
    focus_resolution = float(config.get("topography_resolution_m", 0.5))
    context_resolution = float(config.get("context_topography_resolution_m", focus_resolution))
    if refresh or not paths["context_elevation"].exists():
        download_rge_alti(
            context,
            context_resolution,
            paths["context_elevation"],
        )
        rebuilt.add("context_elevation")
    if refresh or "context_depth" in rebuilt or not paths["focus_depth"].exists():
        crop_raster(
            paths["context_depth"],
            focus,
            paths["focus_depth"],
            content_kind="positive_depth",
        )
        rebuilt.add("focus_depth")
    if (
        refresh
        or "context_elevation" in rebuilt
        or not paths["focus_elevation"].exists()
    ):
        if abs(focus_resolution - context_resolution) <= 1e-9:
            crop_raster(
                paths["context_elevation"],
                focus,
                paths["focus_elevation"],
                content_kind="elevation",
            )
        else:
            download_rge_alti(focus, focus_resolution, paths["focus_elevation"])
        rebuilt.add("focus_elevation")
    orthophoto_enabled = bool(config.get("orthophoto_enabled", False))
    needs_focus_orthophoto = orthophoto_enabled and (
        refresh or not paths["focus_orthophoto"].exists()
    )
    needs_context_orthophoto = orthophoto_enabled and (
        refresh or not paths["context_orthophoto"].exists()
    )
    if needs_focus_orthophoto or needs_context_orthophoto:
        verify_orthophoto_capture_date(config)
        if needs_focus_orthophoto:
            download_orthophoto(
                focus,
                float(config.get("orthophoto_resolution_m", 0.2)),
                str(config.get("orthophoto_layer", ORTHOPHOTO_LAYER)),
                paths["focus_orthophoto"],
            )
            rebuilt.add("focus_orthophoto")
        if needs_context_orthophoto:
            download_orthophoto(
                context,
                float(config.get("orthophoto_3d_resolution_m", 0.4)),
                str(config.get("orthophoto_layer", ORTHOPHOTO_LAYER)),
                paths["context_orthophoto"],
            )
            rebuilt.add("context_orthophoto")
    if config.get("locator_map_enabled", False) and (refresh or not paths["locator_elevation"].exists()):
        download_rge_alti(
            bbox(config, "locator_bbox_utm40s"),
            float(config.get("locator_resolution_m", 20.0)),
            paths["locator_elevation"],
        )
        rebuilt.add("locator_elevation")
    if (
        config.get("locator_map_enabled", False)
        and config.get("locator_bathymetry_enabled", False)
        and (
            refresh
            or "locator_elevation" in rebuilt
            or not paths["locator_bathymetry"].exists()
        )
    ):
        locator_dataset = gdal.Open(str(paths["locator_elevation"]))
        if locator_dataset is None:
            raise RuntimeError(f"Cannot open {paths['locator_elevation']} for the GEBCO target grid")
        download_gebco_relief(
            bbox(config, "locator_bbox_utm40s"),
            locator_dataset.RasterXSize,
            locator_dataset.RasterYSize,
            int(config.get("locator_gebco_request_width_px", 2000)),
            str(config.get("locator_gebco_layer", GEBCO_LAYER)),
            str(config.get("locator_gebco_wms_url", GEBCO_WMS)),
            paths["locator_bathymetry"],
        )
        rebuilt.add("locator_bathymetry")
    return rebuilt


def validate_cached_inputs(config: dict, paths: dict[str, Path], *, include_raw: bool) -> None:
    focus = bbox(config, "focus_bbox_utm40s")
    context = bbox(config, "context_bbox_utm40s")
    focus_resolution = float(config.get("topography_resolution_m", 0.5))
    context_resolution = float(config.get("context_topography_resolution_m", focus_resolution))

    if include_raw:
        validate_raster(
            paths["context_depth_raw"],
            "context HYSCORES bathymetry",
            extent=context,
            bands=1,
            content_kind="hyscores_raw",
        )
    validate_raster(
        paths["context_depth"],
        "context positive-depth bathymetry",
        extent=context,
        bands=1,
        reference=paths["context_depth_raw"] if include_raw else None,
        content_kind="positive_depth",
    )
    validate_raster(
        paths["focus_depth"],
        "focus positive-depth bathymetry",
        extent=focus,
        bands=1,
        content_kind="positive_depth",
    )
    validate_raster(
        paths["context_elevation"],
        "context RGE ALTI topography",
        extent=context,
        resolution=context_resolution,
        bands=1,
        exact_extent=True,
        content_kind="elevation",
    )
    validate_raster(
        paths["focus_elevation"],
        "focus RGE ALTI topography",
        extent=focus,
        resolution=focus_resolution,
        bands=1,
        exact_extent=abs(focus_resolution - context_resolution) > 1e-9,
        content_kind="elevation",
    )
    if config.get("orthophoto_enabled", False):
        validate_raster(
            paths["focus_orthophoto"],
            "focus IGN orthophoto",
            extent=focus,
            resolution=float(config.get("orthophoto_resolution_m", 0.2)),
            bands=3,
            exact_extent=True,
            content_kind="rgb",
        )
        validate_raster(
            paths["context_orthophoto"],
            "context IGN orthophoto",
            extent=context,
            resolution=float(config.get("orthophoto_3d_resolution_m", 0.4)),
            bands=3,
            exact_extent=True,
            content_kind="rgb",
        )
    if config.get("locator_map_enabled", False):
        locator = bbox(config, "locator_bbox_utm40s")
        locator_resolution = float(config.get("locator_resolution_m", 20.0))
        validate_raster(
            paths["locator_elevation"],
            "locator RGE ALTI topography",
            extent=locator,
            resolution=locator_resolution,
            bands=1,
            exact_extent=True,
            content_kind="elevation",
        )
        if config.get("locator_bathymetry_enabled", False):
            validate_raster(
                paths["locator_bathymetry"],
                "locator GEBCO relief",
                extent=locator,
                bands=3,
                exact_extent=True,
                reference=paths["locator_elevation"],
                content_kind="rgb",
            )


def render(config: dict, paths: dict[str, Path]) -> None:
    title = str(config["title"])
    rotation_k = int(config.get("rotation_k", 0))
    author = str(config.get("plate_author", "")).strip()
    copyright_year = int(config.get("copyright_year", 2026))
    map_license = str(config.get("map_license", "")).strip()
    copyright_text = f"© {copyright_year} {author}" if author else None
    if copyright_text and map_license:
        copyright_text += f" · {map_license}"
    detailed_sources = (
        "Bathymétrie : Projet HYSCORES (Ifremer, UBO, Office de l'Eau Réunion), 2015, "
        "incluant Litto3D · Topographie : IGN RGE ALTI, mise à jour arrêtée en 2024"
    )
    orthophoto_sources = detailed_sources
    if config.get("orthophoto_enabled", False):
        capture_date = date.fromisoformat(str(config["orthophoto_capture_date"]))
        orthophoto_sources += (
            f" · Orthophoto : IGN BD ORTHO, prise de vue {capture_date.strftime('%d-%m-%Y')}"
        )
    focus_extent = bbox(config, "focus_bbox_utm40s")
    focus_width_m = focus_extent[2] - focus_extent[0]

    if config.get("locator_map_enabled", False):
        marker = tuple(map(float, config["locator_marker_utm40s"]))
        locator_attribution = "Topographie : IGN RGE ALTI, mise à jour arrêtée en 2024"
        if config.get("locator_bathymetry_enabled", False):
            locator_attribution += f" · {config['locator_gebco_attribution']}"
        make_locator_map(
            paths["locator_elevation"],
            paths["output_locator"],
            marker,
            str(config.get("locator_label", title)),
            output_width=int(config.get("locator_output_width_px", 2400)),
            bathymetry_path=paths["locator_bathymetry"] if config.get("locator_bathymetry_enabled", False) else None,
            bathymetry_blur_px=float(config.get("locator_gebco_blur_px", 8.0)),
            attribution_text=locator_attribution,
        )

    plan_options = {
        "max_depth": float(config.get("max_depth_m", 20)),
        "rotation_k": 0,
        "coast_mode": str(config.get("coast_mode", "profile")),
        "output_scale": float(config.get("plan_output_scale", config.get("output_scale", 1.0))),
        "copyright_text": copyright_text,
        "source_text": detailed_sources,
        "open_label_offsets_px": config.get("plan_open_label_offsets_px"),
        "final_output_size_px": config.get("final_output_size_px"),
        "land_sieve_threshold_px": int(config.get("land_sieve_threshold_px", 200)),
        "imagery_sea_depth_m": config.get("imagery_sea_depth_m"),
        "imagery_sea_feather_m": float(config.get("imagery_sea_feather_m", 0.6)),
        "imagery_sea_smoothing_m": float(config.get("imagery_sea_smoothing_m", 0.0)),
        "imagery_sea_full_depth_m": config.get("imagery_sea_full_depth_m"),
        "imagery_sea_max_depth_m": config.get("imagery_sea_max_depth_m"),
        "coastline_visible": bool(config.get("coastline_visible", True)),
        "final_style_scale": float(config.get("map_style_scale", 2.0)),
        "max_land_elevation_m": float(config.get("max_land_elevation_m", 55.0)),
    }
    make_clean_plan(
        paths["focus_depth"],
        paths["focus_elevation"],
        paths["output_2d"],
        **plan_options,
    )
    if config.get("orthophoto_enabled", False):
        orthophoto_plan_options = {
            **plan_options,
            "land_imagery_path": paths["focus_orthophoto"],
            "source_text": orthophoto_sources,
            "coastline_visible": bool(config.get("orthophoto_coastline_visible", False)),
        }
        make_clean_plan(
            paths["focus_depth"],
            paths["focus_elevation"],
            paths["output_2d_ortho"],
            **orthophoto_plan_options,
        )

    legacy_symmetric_crop = float(config.get("horizontal_crop_fraction", 0.0))
    left_crop = float(
        config.get(
            "view_left_crop_fraction",
            config.get("east_crop_fraction", legacy_symmetric_crop),
        )
    )
    right_crop = float(
        config.get(
            "view_right_crop_fraction",
            config.get("west_crop_fraction", legacy_symmetric_crop),
        )
    )
    top_crop = float(
        config.get("view_top_crop_fraction", config.get("south_crop_fraction", 0.0))
    )
    relief_options = {
        "max_depth": float(config.get("max_depth_m", 20)),
        "decorate": False,
        "rotation_k": rotation_k,
        "coast_mode": str(config.get("coast_mode", "profile")),
        "view_bearing_deg": config.get("view_bearing_deg"),
        "view_crop_width_m": config.get("view_crop_width_m"),
        "view_crop_depth_m": config.get("view_crop_depth_m"),
        "target_visible_width_m": float(config.get("view_visible_width_m", focus_width_m)),
        "canvas_width_px": int(config.get("view_canvas_width_px", 1455)),
        "canvas_height_px": int(config.get("view_canvas_height_px", 1069)),
        "camera_tilt": float(config.get("camera_tilt", 0.34)),
        "along_view_projection_scale": float(
            config.get(
                "along_view_projection_scale",
                config.get("north_south_projection_scale", 1.0),
            )
        ),
        "symmetric_crop_fraction": 0.0,
        "left_crop_fraction": left_crop,
        "right_crop_fraction": right_crop,
        "top_crop_fraction": top_crop,
        "coast_frame_fraction": float(config.get("coast_frame_fraction", 0.44)),
        "vertical_exaggeration": float(
            config.get("vertical_exaggeration", DEFAULT_VERTICAL_EXAGGERATION)
        ),
        "output_scale": float(config.get("relief_output_scale", config.get("output_scale", 1.0))),
        "bridge_decks": config.get("bridge_decks"),
        "copyright_text": copyright_text,
        "source_text": detailed_sources,
        "final_output_size_px": config.get("final_output_size_px"),
        "suppressed_label_levels": config.get("relief_suppressed_label_levels", []),
        "land_sieve_threshold_px": int(config.get("land_sieve_threshold_px", 200)),
        "horizon_cleanup_fraction": float(config.get("horizon_cleanup_fraction", 0.0)),
        "imagery_sea_depth_m": config.get("imagery_sea_depth_m"),
        "imagery_sea_feather_m": float(config.get("imagery_sea_feather_m", 0.6)),
        "imagery_sea_smoothing_m": float(config.get("imagery_sea_smoothing_m", 0.0)),
        "clip_rotated_outside": bool(config.get("clip_rotated_outside", True)),
        "imagery_sea_full_depth_m": config.get("imagery_sea_full_depth_m"),
        "imagery_sea_max_depth_m": config.get("imagery_sea_max_depth_m"),
        "view_center_offset_east_m": float(config.get("view_center_offset_east_m", 0.0)),
        "view_center_offset_north_m": float(config.get("view_center_offset_north_m", 0.0)),
        "coastline_visible": bool(config.get("coastline_visible", True)),
        "final_style_scale": float(config.get("map_style_scale", 2.0)),
        "max_land_elevation_m": float(config.get("max_land_elevation_m", 55.0)),
    }
    make_pretty_3d_from_offshore(
        paths["context_depth"],
        paths["context_elevation"],
        paths["output_3d"],
        title,
        **relief_options,
    )
    if config.get("orthophoto_enabled", False):
        orthophoto_relief_options = {
            **relief_options,
            "land_imagery_path": paths["context_orthophoto"],
            "source_text": orthophoto_sources,
            "coastline_visible": bool(config.get("orthophoto_coastline_visible", False)),
        }
        make_pretty_3d_from_offshore(
            paths["context_depth"],
            paths["context_elevation"],
            paths["output_3d_ortho"],
            title,
            **orthophoto_relief_options,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate 2D and 3D topo-bathymetric maps for a Reunion coastal site")
    parser.add_argument("config", type=Path, help="Site JSON configuration")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--refresh", action="store_true", help="Redownload and rebuild every source raster")
    mode.add_argument("--render-only", action="store_true", help="Reuse validated source rasters")
    mode.add_argument(
        "--check",
        action="store_true",
        help="Validate the configuration and cached rasters without downloading or rendering",
    )
    args = parser.parse_args()

    config_path = args.config.expanduser().resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    validate_config(config)
    paths = paths_for(config)
    try:
        existing_manifest = preflight_cache_manifest(
            config,
            paths,
            refresh=args.refresh,
        )
        if args.check:
            validate_cache_manifest(config, paths, verify_hashes=True)
            validate_cached_inputs(config, paths, include_raw=True)
            print(f"Configuration, provenance manifest, and source rasters are valid: {config_path}")
            return 0
        if args.render_only:
            validate_cache_manifest(config, paths, verify_hashes=True)
            validate_cached_inputs(config, paths, include_raw=False)
        else:
            rebuilt = acquire(config, paths, args.refresh)
            validate_cached_inputs(config, paths, include_raw=True)
            if args.refresh or rebuilt or existing_manifest is None:
                write_cache_manifest(config, paths)
            else:
                validate_cache_manifest(config, paths, verify_hashes=True)
    except (FileNotFoundError, ValueError) as error:
        suggestion = "Run with --refresh to rebuild the configured source rasters."
        raise type(error)(f"{error}\n{suggestion}") from error
    render(config, paths)

    print("\nSources")
    print(raster_summary(paths["focus_depth"]))
    print(raster_summary(paths["context_depth"]))
    print("\nOutputs")
    print(paths["output_2d"])
    if config.get("orthophoto_enabled", False):
        print(paths["output_2d_ortho"])
    print(paths["output_3d"])
    if config.get("orthophoto_enabled", False):
        print(paths["output_3d_ortho"])
    if config.get("locator_map_enabled", False):
        print(paths["output_locator"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
