from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import urllib.request
from typing import Any, Mapping

import numpy as np
from osgeo import gdal, osr
from PIL import Image


gdal.UseExceptions()
osr.UseExceptions()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download_pinned_archive(
    url: str,
    output: Path,
    expected_sha256: str,
) -> None:
    if output.exists() and _sha256_file(output) == expected_sha256:
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f"{output.name}.part")
    temporary.unlink(missing_ok=True)
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://diffusion.shom.fr/",
        },
    )
    try:
        with (
            urllib.request.urlopen(request, timeout=180) as response,
            temporary.open("wb") as handle,
        ):
            shutil.copyfileobj(response, handle)
        actual_sha256 = _sha256_file(temporary)
        if actual_sha256 != expected_sha256:
            raise ValueError(
                "Downloaded SHOM archive hash does not match the configured "
                f"SHA-256: expected {expected_sha256}, found {actual_sha256}"
            )
        os.replace(temporary, output)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _extract_xyz(archive: Path, member: str, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f"{output.name}.part")
    temporary.unlink(missing_ok=True)
    try:
        with temporary.open("wb") as handle:
            subprocess.run(
                ["bsdtar", "-xOf", str(archive), member],
                check=True,
                stdout=handle,
            )
        if temporary.stat().st_size == 0:
            raise ValueError(f"Empty SHOM survey member {member!r} in {archive}")
        os.replace(temporary, output)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _survey_points_utm40s(xyz_path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    points = np.loadtxt(
        xyz_path,
        delimiter=",",
        skiprows=3,
        dtype=np.float64,
    )
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError(f"Invalid SHOM XYZ survey: {xyz_path}")
    geographic = osr.SpatialReference()
    geographic.ImportFromEPSG(4326)
    geographic.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    utm = osr.SpatialReference()
    utm.ImportFromEPSG(32740)
    utm.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    transformer = osr.CoordinateTransformation(geographic, utm)
    transformed = np.asarray(
        transformer.TransformPoints(points[:, :2].tolist()),
        dtype=np.float64,
    )
    return transformed[:, 0], transformed[:, 1], points[:, 2]


def _grid_coordinates(
    transform: tuple[float, float, float, float, float, float],
    row0: int,
    row1: int,
    col0: int,
    col1: int,
) -> tuple[np.ndarray, np.ndarray]:
    pixel_cols = np.arange(col0, col1, dtype=np.float64) + 0.5
    pixel_rows = np.arange(row0, row1, dtype=np.float64) + 0.5
    columns, rows = np.meshgrid(pixel_cols, pixel_rows)
    east = transform[0] + columns * transform[1] + rows * transform[2]
    north = transform[3] + columns * transform[4] + rows * transform[5]
    return east, north


def _distance_to_polylines(
    grid_east: np.ndarray,
    grid_north: np.ndarray,
    polylines: list[list[list[float]]],
) -> np.ndarray:
    distance = np.full(grid_east.shape, np.inf, dtype=np.float64)
    for raw_polyline in polylines:
        polyline = np.asarray(raw_polyline, dtype=np.float64)
        for start, end in zip(polyline[:-1], polyline[1:]):
            vector = end - start
            length_squared = float(np.dot(vector, vector))
            if length_squared <= 0.0:
                continue
            fraction = np.clip(
                (
                    (grid_east - start[0]) * vector[0]
                    + (grid_north - start[1]) * vector[1]
                )
                / length_squared,
                0.0,
                1.0,
            )
            closest_east = start[0] + fraction * vector[0]
            closest_north = start[1] + fraction * vector[1]
            distance = np.minimum(
                distance,
                np.hypot(
                    grid_east - closest_east,
                    grid_north - closest_north,
                ),
            )
    return distance


def reconcile_false_edges(
    depth: np.ndarray,
    valid: np.ndarray,
    grid_east: np.ndarray,
    grid_north: np.ndarray,
    pixel_size_m: float,
    settings: Mapping[str, Any],
) -> tuple[np.ndarray, np.ndarray]:
    """Smooth a documented false survey edge inside a feathered local band."""
    smoothing_m = float(settings["smoothing_m"])
    factor = max(2, int(np.floor(smoothing_m / pixel_size_m + 0.5)))
    height, width = depth.shape
    fill = float(np.median(depth[valid])) if np.any(valid) else 0.0
    safe = np.where(valid, depth, fill).astype(np.float32)
    reduced = Image.fromarray(safe, mode="F").resize(
        (max(2, width // factor), max(2, height // factor)),
        Image.Resampling.BOX,
    )
    smooth = np.asarray(
        reduced.resize((width, height), Image.Resampling.BICUBIC),
        dtype=np.float64,
    )

    distance = _distance_to_polylines(
        grid_east,
        grid_north,
        settings["polylines_utm40s"],
    )
    inner_width = float(settings["inner_width_m"])
    outer_width = float(settings["outer_width_m"])
    weight = np.clip(
        (outer_width - distance) / (outer_width - inner_width),
        0.0,
        1.0,
    )
    weight = weight * weight * (3.0 - 2.0 * weight)
    minimum_depth = float(settings.get("minimum_depth_m", 0.0))
    weight = np.where(valid & (depth >= minimum_depth), weight, 0.0)
    return depth * (1.0 - weight) + smooth * weight, weight


def fuse_shom_points(
    source: Path,
    output: Path,
    east: np.ndarray,
    north: np.ndarray,
    shom_depth: np.ndarray,
    settings: Mapping[str, Any],
) -> dict[str, float | int]:
    dataset = gdal.Open(str(source), gdal.GA_ReadOnly)
    if dataset is None:
        raise ValueError(f"Cannot open positive-depth raster: {source}")
    band = dataset.GetRasterBand(1)
    nodata = float(band.GetNoDataValue())
    transform = dataset.GetGeoTransform()
    if transform[2] != 0.0 or transform[4] != 0.0:
        raise ValueError("SHOM local fusion requires a north-up raster")
    inverse = gdal.InvGeoTransform(transform)
    raster = band.ReadAsArray().astype(np.float64)

    cols = np.floor(
        inverse[0] + inverse[1] * east + inverse[2] * north
    ).astype(np.int64)
    rows = np.floor(
        inverse[3] + inverse[4] * east + inverse[5] * north
    ).astype(np.int64)
    on_grid = (
        (cols >= 0)
        & (cols < dataset.RasterXSize)
        & (rows >= 0)
        & (rows < dataset.RasterYSize)
    )
    hyscores = np.full(shom_depth.shape, nodata, dtype=np.float64)
    hyscores[on_grid] = raster[rows[on_grid], cols[on_grid]]
    valid_overlap = (
        on_grid
        & np.isfinite(hyscores)
        & (hyscores != nodata)
        & (hyscores >= 0.0)
    )

    datum_depth_range = tuple(
        map(float, settings["datum_fit_depth_range_m"])
    )
    datum_candidates = (
        valid_overlap
        & (shom_depth >= datum_depth_range[0])
        & (shom_depth <= datum_depth_range[1])
    )
    datum_delta = hyscores[datum_candidates] - shom_depth[datum_candidates]
    minimum_datum_points = int(settings.get("minimum_datum_points", 20))
    if datum_delta.size < minimum_datum_points:
        raise ValueError(
            "Too few SHOM/HYSCORES overlap points to align vertical levels: "
            f"{datum_delta.size} found, {minimum_datum_points} required"
        )
    datum_offset = float(np.median(datum_delta))
    datum_mad = float(np.median(np.abs(datum_delta - datum_offset)))
    datum_keep = np.abs(datum_delta - datum_offset) <= max(
        3.0 * datum_mad,
        2.0,
    )
    datum_offset = float(np.median(datum_delta[datum_keep]))

    control_bbox = tuple(map(float, settings["control_bbox_utm40s"]))
    control_candidates = (
        valid_overlap
        & (east >= control_bbox[0])
        & (east <= control_bbox[2])
        & (north >= control_bbox[1])
        & (north <= control_bbox[3])
    )
    target_correction = shom_depth + datum_offset - hyscores
    minimum_correction = float(settings["minimum_correction_m"])
    control_indices = np.flatnonzero(
        control_candidates & (target_correction >= minimum_correction)
    )
    minimum_control_points = int(settings.get("minimum_control_points", 4))
    if control_indices.size < minimum_control_points:
        raise ValueError(
            "Too few SHOM controls diagnose the configured HYSCORES error: "
            f"{control_indices.size} found, {minimum_control_points} required"
        )

    padding = float(settings["window_padding_m"])
    min_x = control_bbox[0] - padding
    min_y = control_bbox[1] - padding
    max_x = control_bbox[2] + padding
    max_y = control_bbox[3] + padding
    col0 = max(
        0,
        int(np.floor(inverse[0] + inverse[1] * min_x + inverse[2] * max_y)) - 2,
    )
    row0 = max(
        0,
        int(np.floor(inverse[3] + inverse[4] * min_x + inverse[5] * max_y)) - 2,
    )
    col1 = min(
        dataset.RasterXSize,
        int(np.ceil(inverse[0] + inverse[1] * max_x + inverse[2] * min_y)) + 2,
    )
    row1 = min(
        dataset.RasterYSize,
        int(np.ceil(inverse[3] + inverse[4] * max_x + inverse[5] * min_y)) + 2,
    )
    if col1 <= col0 or row1 <= row0:
        raise ValueError("Configured SHOM correction window does not meet the raster")

    window = raster[row0:row1, col0:col1]
    valid_window = np.isfinite(window) & (window != nodata)
    grid_east, grid_north = _grid_coordinates(
        transform,
        row0,
        row1,
        col0,
        col1,
    )
    correction_numerator = np.zeros(window.shape, dtype=np.float64)
    correction_denominator = np.zeros(window.shape, dtype=np.float64)
    maximum_kernel = np.zeros(window.shape, dtype=np.float64)
    kernel_sigma = float(settings["kernel_sigma_m"])
    for index in control_indices:
        squared_distance = (
            (grid_east - east[index]) ** 2
            + (grid_north - north[index]) ** 2
        )
        kernel = np.exp(-0.5 * squared_distance / (kernel_sigma**2))
        correction_numerator += kernel * target_correction[index]
        correction_denominator += kernel
        maximum_kernel = np.maximum(maximum_kernel, kernel)

    correction = np.divide(
        correction_numerator,
        correction_denominator,
        out=np.zeros_like(correction_numerator),
        where=correction_denominator > 1e-8,
    )
    influence_start = float(settings["influence_start"])
    influence_full = float(settings["influence_full"])
    influence = np.clip(
        (maximum_kernel - influence_start)
        / (influence_full - influence_start),
        0.0,
        1.0,
    )
    influence = influence * influence * (3.0 - 2.0 * influence)
    influence = np.where(valid_window, influence, 0.0)
    fused_window = window + correction * influence
    reconciliation = settings.get("false_edge_reconciliation")
    reconciliation_weight = np.zeros(window.shape, dtype=np.float64)
    if reconciliation is not None:
        pixel_size_m = float(
            np.sqrt(abs(transform[1] * transform[5]))
        )
        fused_window, reconciliation_weight = reconcile_false_edges(
            fused_window,
            valid_window,
            grid_east,
            grid_north,
            pixel_size_m,
            reconciliation,
        )

    temporary = output.with_name(f"{output.name}.part")
    temporary.unlink(missing_ok=True)
    driver = gdal.GetDriverByName("GTiff")
    try:
        target = driver.CreateCopy(
            str(temporary),
            dataset,
            strict=1,
            options=["TILED=YES", "COMPRESS=DEFLATE", "PREDICTOR=3"],
        )
        target.GetRasterBand(1).WriteArray(
            fused_window.astype(np.float32),
            col0,
            row0,
        )
        target.GetRasterBand(1).FlushCache()
        target = None
        dataset = None
        os.replace(temporary, output)
    except Exception:
        target = None
        dataset = None
        temporary.unlink(missing_ok=True)
        raise

    local_rows = rows[control_indices] - row0
    local_cols = cols[control_indices] - col0
    after = fused_window[local_rows, local_cols] - (
        shom_depth[control_indices] + datum_offset
    )
    changed = (influence > 1e-6) | (reconciliation_weight > 1e-6)
    difference = fused_window[changed] - window[changed]
    pixel_area = abs(transform[1] * transform[5])
    return {
        "datum_offset_m": datum_offset,
        "control_points": int(control_indices.size),
        "control_residual_median_m": float(np.median(after)),
        "control_residual_p05_m": float(np.percentile(after, 5)),
        "control_residual_p95_m": float(np.percentile(after, 95)),
        "changed_area_m2": float(changed.sum() * pixel_area),
        "difference_median_m": float(np.median(difference)),
        "difference_max_m": float(np.max(difference)),
    }


def apply_configured_shom_fusion(
    config: Mapping[str, Any],
    positive_depth_path: Path,
) -> dict[str, float | int] | None:
    raw_settings = config.get("shom_local_fusion")
    if raw_settings is None:
        return None
    if not isinstance(raw_settings, Mapping):
        raise ValueError("shom_local_fusion must be an object")
    settings = dict(raw_settings)
    survey_id = str(settings["survey_id"])
    archive = positive_depth_path.parent / f"{config['slug']}-{survey_id}.7z"
    xyz = positive_depth_path.parent / f"{config['slug']}-{survey_id}.xyz"
    _download_pinned_archive(
        str(settings["archive_url"]),
        archive,
        str(settings["archive_sha256"]),
    )
    _extract_xyz(archive, str(settings["archive_member"]), xyz)
    east, north, depth = _survey_points_utm40s(xyz)
    stats = fuse_shom_points(
        positive_depth_path,
        positive_depth_path,
        east,
        north,
        depth,
        settings,
    )
    print(
        "Applied local SHOM fusion "
        f"{survey_id}: {stats['control_points']} controls, "
        f"{stats['changed_area_m2']:.0f} m², "
        f"post-fusion median residual "
        f"{stats['control_residual_median_m']:.2f} m"
    )
    return stats
