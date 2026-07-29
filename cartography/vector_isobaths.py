"""Reusable extraction of vector isobaths in terrain-grid coordinates.

The output deliberately uses the same compact schema consumed by the
interactive terrain prototype::

    {"coordinateSpace": "grid-pixels", "levels": {"5": [[[x, y], ...]]}}

This module owns no site paths and performs no file I/O.  Callers are
responsible for serializing the returned payload alongside their terrain
package.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any, Literal

import numpy as np
from osgeo import gdal, ogr


gdal.UseExceptions()

GridKind = Literal["depth", "elevation"]
VectorPayload = dict[str, Any]
VectorDiagnostics = dict[str, Any]


def _as_grid(
    values: np.ndarray,
    sea_mask: np.ndarray,
    source_kind: GridKind,
) -> tuple[np.ndarray, np.ndarray]:
    grid = np.asarray(values, dtype=np.float64)
    mask = np.asarray(sea_mask, dtype=bool)
    if grid.ndim != 2:
        raise ValueError("values must be a two-dimensional grid")
    if mask.shape != grid.shape:
        raise ValueError("sea_mask must have the same shape as values")
    if grid.shape[0] < 2 or grid.shape[1] < 2:
        raise ValueError("values must contain at least two rows and columns")
    if source_kind not in ("depth", "elevation"):
        raise ValueError("source_kind must be 'depth' or 'elevation'")
    if not np.all(np.isfinite(grid[mask])):
        raise ValueError("values must be finite wherever sea_mask is true")

    depth = grid if source_kind == "depth" else -grid
    if np.any(depth[mask] < 0):
        raise ValueError("masked sea values must represent non-negative depths")
    return depth, mask


def _as_levels(levels: Iterable[float]) -> tuple[float, ...]:
    normalized = tuple(float(level) for level in levels)
    if not normalized:
        raise ValueError("levels must not be empty")
    if not all(np.isfinite(level) and level >= 0 for level in normalized):
        raise ValueError("levels must contain finite non-negative depths")
    if len(set(normalized)) != len(normalized):
        raise ValueError("levels must not contain duplicates")
    return tuple(sorted(normalized))


def _level_key(level: float) -> str:
    return str(int(level)) if level.is_integer() else format(level, ".15g")


def sample_bilinear(values: np.ndarray, points: np.ndarray) -> np.ndarray:
    """Sample a two-dimensional grid at ``(x, y)`` pixel coordinates."""
    height, width = values.shape
    x = np.clip(points[:, 0], 0, width - 1)
    y = np.clip(points[:, 1], 0, height - 1)
    x0 = np.floor(x).astype(np.int32)
    y0 = np.floor(y).astype(np.int32)
    x1 = np.minimum(x0 + 1, width - 1)
    y1 = np.minimum(y0 + 1, height - 1)
    tx = x - x0
    ty = y - y0
    return (
        values[y0, x0] * (1 - tx) * (1 - ty)
        + values[y0, x1] * tx * (1 - ty)
        + values[y1, x0] * (1 - tx) * ty
        + values[y1, x1] * tx * ty
    )


def _nearest_grid_edge_crossing(
    point: np.ndarray,
    depth: np.ndarray,
    level: float,
    *,
    radius: int = 3,
) -> np.ndarray | None:
    """Find the nearest exact isoline crossing on a local grid edge."""
    height, width = depth.shape
    center_x = int(np.floor(point[0]))
    center_y = int(np.floor(point[1]))
    candidates: list[np.ndarray] = []
    x_start = max(center_x - radius, 0)
    x_stop = min(center_x + radius + 1, width - 1)
    y_start = max(center_y - radius, 0)
    y_stop = min(center_y + radius + 1, height - 1)

    for y in range(y_start, y_stop + 1):
        for x in range(x_start, x_stop):
            first = float(depth[y, x])
            second = float(depth[y, x + 1])
            if (
                np.isfinite(first)
                and np.isfinite(second)
                and first != second
                and (first - level) * (second - level) <= 0
            ):
                fraction = (level - first) / (second - first)
                candidates.append(
                    np.asarray([x + fraction, y], dtype=np.float64)
                )
    for y in range(y_start, y_stop):
        for x in range(x_start, x_stop + 1):
            first = float(depth[y, x])
            second = float(depth[y + 1, x])
            if (
                np.isfinite(first)
                and np.isfinite(second)
                and first != second
                and (first - level) * (second - level) <= 0
            ):
                fraction = (level - first) / (second - first)
                candidates.append(
                    np.asarray([x, y + fraction], dtype=np.float64)
                )
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda candidate: float(np.linalg.norm(candidate - point)),
    )


def _reproject_to_isobath(
    points: np.ndarray,
    depth: np.ndarray,
    level: float,
) -> np.ndarray:
    """Return smoothed points reprojected onto the raw-depth isoline."""
    projected = points.copy()
    height, width = depth.shape
    epsilon = 0.25

    for _ in range(8):
        residual = sample_bilinear(depth, projected) - level
        gradient_x = (
            sample_bilinear(
                depth,
                projected + np.array([epsilon, 0.0]),
            )
            - sample_bilinear(
                depth,
                projected - np.array([epsilon, 0.0]),
            )
        ) / (2 * epsilon)
        gradient_y = (
            sample_bilinear(
                depth,
                projected + np.array([0.0, epsilon]),
            )
            - sample_bilinear(
                depth,
                projected - np.array([0.0, epsilon]),
            )
        ) / (2 * epsilon)
        denominator = gradient_x**2 + gradient_y**2
        movable = denominator > 1e-6
        correction = np.zeros_like(projected)
        correction[movable, 0] = (
            residual[movable] * gradient_x[movable] / denominator[movable]
        )
        correction[movable, 1] = (
            residual[movable] * gradient_y[movable] / denominator[movable]
        )
        correction_length = np.linalg.norm(correction, axis=1)
        correction_scale = np.minimum(
            1.0,
            0.75 / np.maximum(correction_length, 1e-9),
        )
        projected -= correction * correction_scale[:, None]
        projected[:, 0] = np.clip(projected[:, 0], 0, width - 1)
        projected[:, 1] = np.clip(projected[:, 1], 0, height - 1)

    # Finish with monotonic, sub-pixel corrections.  The first pass is
    # intentionally aggressive so smoothed vertices can cross cell boundaries;
    # near a bilinear saddle it may oscillate by a few centimetres.
    epsilon = 0.05
    for _ in range(24):
        residual = sample_bilinear(depth, projected) - level
        current_error = np.abs(residual)
        if np.all(current_error <= 0.01):
            break
        gradient_x = (
            sample_bilinear(
                depth,
                projected + np.array([epsilon, 0.0]),
            )
            - sample_bilinear(
                depth,
                projected - np.array([epsilon, 0.0]),
            )
        ) / (2 * epsilon)
        gradient_y = (
            sample_bilinear(
                depth,
                projected + np.array([0.0, epsilon]),
            )
            - sample_bilinear(
                depth,
                projected - np.array([0.0, epsilon]),
            )
        ) / (2 * epsilon)
        denominator = gradient_x**2 + gradient_y**2
        movable = denominator > 1e-6
        correction = np.zeros_like(projected)
        correction[movable, 0] = (
            residual[movable] * gradient_x[movable] / denominator[movable]
        )
        correction[movable, 1] = (
            residual[movable] * gradient_y[movable] / denominator[movable]
        )
        correction_length = np.linalg.norm(correction, axis=1)
        correction *= np.minimum(
            1.0,
            0.25 / np.maximum(correction_length, 1e-9),
        )[:, None]
        accepted = np.zeros(len(projected), dtype=bool)
        for step_scale in (1.0, 0.5, 0.25, 0.125, 0.0625):
            candidate = projected - correction * step_scale
            candidate[:, 0] = np.clip(candidate[:, 0], 0, width - 1)
            candidate[:, 1] = np.clip(candidate[:, 1], 0, height - 1)
            candidate_error = np.abs(
                sample_bilinear(depth, candidate) - level
            )
            improved = (~accepted) & (candidate_error < current_error)
            projected[improved] = candidate[improved]
            accepted[improved] = True

    remaining_error = np.abs(sample_bilinear(depth, projected) - level)
    for index in np.flatnonzero(remaining_error > 0.01):
        crossing = _nearest_grid_edge_crossing(
            projected[index],
            depth,
            level,
        )
        if crossing is not None:
            projected[index] = crossing

    return projected


def _adaptive_smooth_polyline(
    points: list[tuple[float, float]],
    depth: np.ndarray,
    slope: np.ndarray,
    level: float,
) -> list[tuple[float, float]]:
    if len(points) < 5:
        return points
    arr = np.asarray(points, dtype=np.float64)
    closed = np.linalg.norm(arr[0] - arr[-1]) < 2.0
    kernel = np.array([1, 4, 6, 4, 1], dtype=np.float64) / 16.0

    if closed:
        core = arr[:-1]
        padded = np.concatenate([core[-2:], core, core[:2]], axis=0)
        candidate = np.column_stack(
            [
                np.convolve(padded[:, axis], kernel, mode="valid")
                for axis in range(2)
            ]
        )
        local_slope = sample_bilinear(slope, core)
        weight = np.clip((4.0 - local_slope) / (4.0 - 0.08), 0, 1) ** 2
        core = core + weight[:, None] * (candidate - core)
        arr = np.vstack([core, core[0]])
    else:
        padded = np.pad(arr, ((2, 2), (0, 0)), mode="edge")
        candidate = np.column_stack(
            [
                np.convolve(padded[:, axis], kernel, mode="valid")
                for axis in range(2)
            ]
        )
        candidate[0], candidate[-1] = arr[0], arr[-1]
        local_slope = sample_bilinear(slope, arr)
        weight = np.clip((4.0 - local_slope) / (4.0 - 0.08), 0, 1) ** 2
        weight[[0, -1]] = 0
        arr = arr + weight[:, None] * (candidate - arr)

    arr = _reproject_to_isobath(arr, depth, level)
    if closed:
        core = arr[:-1]
        perimeter = float(
            np.linalg.norm(
                np.roll(core, -1, axis=0) - core,
                axis=1,
            ).sum()
        )
        if perimeter < 45:
            following = np.roll(core, -1, axis=0)
            first = 0.75 * core + 0.25 * following
            second = 0.25 * core + 0.75 * following
            core = np.column_stack([first, second]).reshape(-1, 2)
            core = _reproject_to_isobath(core, depth, level)
            arr = np.vstack([core, core[0]])
        arr[-1] = arr[0]

    return [(float(x), float(y)) for x, y in arr]


def _polygon_area(points: list[tuple[float, float]]) -> float:
    arr = np.asarray(points, dtype=np.float64)
    if len(arr) < 4:
        return 0.0
    return float(
        abs(
            np.dot(arr[:-1, 0], arr[1:, 1])
            - np.dot(arr[1:, 0], arr[:-1, 1])
        )
        * 0.5
    )


def _closed_loop_prominence(
    depth: np.ndarray,
    points: list[tuple[float, float]],
    level: float,
) -> float:
    arr = np.asarray(points, dtype=np.float64)
    x0 = max(int(np.floor(arr[:, 0].min())) - 1, 0)
    x1 = min(int(np.ceil(arr[:, 0].max())) + 2, depth.shape[1])
    y0 = max(int(np.floor(arr[:, 1].min())) - 1, 0)
    y1 = min(int(np.ceil(arr[:, 1].max())) + 2, depth.shape[0])
    window = depth[y0:y1, x0:x1]
    if not window.size:
        return 0.0
    return float(
        max(
            level - np.nanmin(window),
            np.nanmax(window) - level,
        )
    )


def _extract_lines(
    depth: np.ndarray,
    sea_mask: np.ndarray,
    levels: tuple[float, ...],
) -> dict[float, list[list[tuple[float, float]]]]:
    height, width = depth.shape
    nodata = -9999.0
    raster = gdal.GetDriverByName("MEM").Create(
        "",
        width,
        height,
        1,
        gdal.GDT_Float32,
    )
    raster.SetGeoTransform((0, 1, 0, 0, 0, 1))
    band = raster.GetRasterBand(1)
    band.WriteArray(np.where(sea_mask, depth, nodata).astype(np.float32))
    band.SetNoDataValue(nodata)

    finite_depth = np.where(np.isfinite(depth), depth, 0.0)
    gradient_y, gradient_x = np.gradient(finite_depth)
    slope = np.hypot(gradient_x, gradient_y)

    vectors = ogr.GetDriverByName("MEM").CreateDataSource("")
    layer = vectors.CreateLayer("isobaths", geom_type=ogr.wkbLineString)
    layer.CreateField(ogr.FieldDefn("level", ogr.OFTReal))
    options = [
        f"FIXED_LEVELS={','.join(format(level, '.15g') for level in levels)}",
        "ELEV_FIELD=0",
        f"NODATA={nodata}",
    ]
    gdal.ContourGenerateEx(band, layer, options)

    contours = {level: [] for level in levels}
    level_lookup = {_level_key(level): level for level in levels}
    for feature in layer:
        feature_level = float(feature["level"])
        lookup_key = _level_key(feature_level)
        if lookup_key not in level_lookup:
            continue
        level = level_lookup[lookup_key]
        geometry = feature.GetGeometryRef()
        parts = (
            [
                geometry.GetGeometryRef(index)
                for index in range(geometry.GetGeometryCount())
            ]
            if geometry.GetGeometryCount()
            else [geometry]
        )
        for part in parts:
            if part is None or part.GetPointCount() < 2:
                continue
            raw_start = np.array([part.GetX(0), part.GetY(0)])
            raw_end = np.array(
                [
                    part.GetX(part.GetPointCount() - 1),
                    part.GetY(part.GetPointCount() - 1),
                ]
            )
            raw_closed = np.linalg.norm(raw_start - raw_end) < 2.0
            simplify_tolerance = (
                0.05 if raw_closed and part.Length() < 45 else 0.08
            )
            simplified = part.Simplify(simplify_tolerance)
            if simplified is None:
                continue
            points = [
                (simplified.GetX(index), simplified.GetY(index))
                for index in range(simplified.GetPointCount())
            ]
            if len(points) < 4:
                continue
            closed = (
                np.linalg.norm(
                    np.asarray(points[0]) - np.asarray(points[-1])
                )
                < 2.0
            )
            length = float(
                np.linalg.norm(
                    np.diff(np.asarray(points), axis=0),
                    axis=1,
                ).sum()
            )
            area = _polygon_area(points) if closed else 0.0
            prominence = (
                _closed_loop_prominence(depth, points, level)
                if closed
                else 0.0
            )
            keep_closed_feature = (
                closed and area >= 8.0 and prominence >= 0.25
            )
            if length >= 45 or keep_closed_feature:
                smoothed = _adaptive_smooth_polyline(
                    points,
                    depth,
                    slope,
                    level,
                )
                smoothed = _adaptive_smooth_polyline(
                    smoothed,
                    depth,
                    slope,
                    level,
                )
                if len(smoothed) >= 6:
                    contours[level].append(smoothed)

    return contours


def _payload_points(
    payload: Mapping[str, Any],
) -> Iterable[tuple[float, Sequence[float]]]:
    levels = payload.get("levels")
    if not isinstance(levels, Mapping):
        raise ValueError("payload levels must be an object")
    for level_text, polylines in levels.items():
        try:
            level = float(level_text)
        except (TypeError, ValueError) as error:
            raise ValueError("payload level keys must be numeric") from error
        if not isinstance(polylines, list):
            raise ValueError("each payload level must contain a list")
        for polyline in polylines:
            if not isinstance(polyline, list) or len(polyline) < 2:
                raise ValueError("each polyline must contain at least two points")
            for point in polyline:
                if not isinstance(point, list) or len(point) != 2:
                    raise ValueError("each point must be an [x, y] pair")
                if not all(
                    isinstance(value, (int, float)) and np.isfinite(value)
                    for value in point
                ):
                    raise ValueError("point coordinates must be finite numbers")
                yield level, point


def validate_vector_isobath_payload(
    payload: Mapping[str, Any],
    *,
    width: int,
    height: int,
    depth: np.ndarray | None = None,
    residual_tolerance_m: float = 0.05,
) -> VectorDiagnostics:
    """Validate schema, grid bounds, and optional isobath residuals.

    Invalid schema or out-of-grid points raise ``ValueError``.  Reprojection
    residuals are reported rather than rejected so callers can apply an
    appropriate QA threshold for their source resolution.
    """
    if set(payload) != {"coordinateSpace", "levels"}:
        raise ValueError(
            "payload must contain only coordinateSpace and levels"
        )
    if payload["coordinateSpace"] != "grid-pixels":
        raise ValueError("payload coordinateSpace must be 'grid-pixels'")
    if width < 2 or height < 2:
        raise ValueError("width and height must both be at least 2")
    if not np.isfinite(residual_tolerance_m) or residual_tolerance_m < 0:
        raise ValueError("residual_tolerance_m must be finite and non-negative")

    depth_grid: np.ndarray | None = None
    if depth is not None:
        depth_grid = np.asarray(depth, dtype=np.float64)
        if depth_grid.shape != (height, width):
            raise ValueError("depth must match the declared width and height")

    level_stats: dict[str, dict[str, Any]] = {}
    all_residuals: list[float] = []
    worst_residual: dict[str, Any] | None = None
    total_polylines = 0
    total_points = 0
    levels = payload["levels"]
    validated_points = list(_payload_points(payload))
    for level_text, polylines in levels.items():
        point_count = sum(len(polyline) for polyline in polylines)
        total_polylines += len(polylines)
        total_points += point_count
        level_stats[str(level_text)] = {
            "polylines": len(polylines),
            "points": point_count,
        }

    for level, point in validated_points:
        x, y = float(point[0]), float(point[1])
        if x < 0 or x > width - 1 or y < 0 or y > height - 1:
            raise ValueError(
                f"point [{x}, {y}] lies outside the {width}x{height} grid"
            )
        if depth_grid is not None:
            residual = abs(
                float(
                    sample_bilinear(
                        depth_grid,
                        np.asarray([[x, y]], dtype=np.float64),
                    )[0]
                )
                - level
            )
            all_residuals.append(residual)
            if (
                worst_residual is None
                or residual > worst_residual["residualM"]
            ):
                worst_residual = {
                    "levelM": level,
                    "point": [x, y],
                    "residualM": residual,
                }

    residuals = np.asarray(all_residuals, dtype=np.float64)
    residual_diagnostics = {
        "samples": int(residuals.size),
        "mean": float(residuals.mean()) if residuals.size else 0.0,
        "p95": (
            float(np.percentile(residuals, 95)) if residuals.size else 0.0
        ),
        "max": float(residuals.max()) if residuals.size else 0.0,
    }
    residual_diagnostics["withinTolerance"] = (
        residual_diagnostics["max"] <= residual_tolerance_m
    )

    return {
        "schemaValid": True,
        "coordinateSpace": "grid-pixels",
        "grid": {"width": width, "height": height},
        "bounds": {"valid": True, "outOfBoundsPoints": 0},
        "levels": level_stats,
        "totals": {
            "levels": len(levels),
            "polylines": total_polylines,
            "points": total_points,
        },
        "reprojectionResidualM": residual_diagnostics,
        "worstResidualSample": worst_residual,
    }


def extract_vector_isobaths(
    values: np.ndarray,
    sea_mask: np.ndarray,
    levels: Iterable[float],
    *,
    source_kind: GridKind = "depth",
    residual_tolerance_m: float = 0.05,
) -> tuple[VectorPayload, VectorDiagnostics]:
    """Extract vector isobaths and return their payload plus QA diagnostics.

    ``source_kind="depth"`` expects positive-down depths.  With
    ``source_kind="elevation"``, negative sea elevations are converted to
    positive depths before extraction.  Coordinates in the payload are pixel
    coordinates in the input grid.
    """
    depth, mask = _as_grid(values, sea_mask, source_kind)
    normalized_levels = _as_levels(levels)
    contours = _extract_lines(depth, mask, normalized_levels)
    payload: VectorPayload = {
        "coordinateSpace": "grid-pixels",
        "levels": {
            _level_key(level): [
                [[float(x), float(y)] for x, y in polyline]
                for polyline in contours[level]
            ]
            for level in normalized_levels
        },
    }
    diagnostics = validate_vector_isobath_payload(
        payload,
        width=depth.shape[1],
        height=depth.shape[0],
        depth=depth,
        residual_tolerance_m=residual_tolerance_m,
    )
    return payload, diagnostics
