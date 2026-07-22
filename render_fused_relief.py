from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
from osgeo import gdal, ogr
from PIL import Image, ImageDraw, ImageFilter, ImageFont


def load_font(size: int, bold: bool = False):
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica.ttc",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default()


def palette(depth: np.ndarray, max_depth: float = 40) -> np.ndarray:
    stops = np.array([0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 30, 40], dtype=np.float32)
    colors = np.array(
        [
            [235, 35, 28], [246, 88, 28], [252, 154, 31], [250, 220, 42],
            [151, 226, 89], [67, 211, 199], [47, 170, 221], [39, 122, 210],
            [28, 82, 178], [16, 50, 135], [8, 31, 100], [4, 20, 78], [1, 9, 42],
        ],
        dtype=np.float32,
    )
    values = np.clip(depth, stops[0], min(max_depth, stops[-1]))
    result = np.zeros((*values.shape, 3), dtype=np.float32)
    for index in range(len(stops) - 1):
        low, high = stops[index], stops[index + 1]
        selected = (values >= low) & (values <= high)
        weight = ((values[selected] - low) / (high - low))[:, None]
        result[selected] = colors[index] * (1 - weight) + colors[index + 1] * weight
    result[values >= stops[-1]] = colors[-1]
    return result.astype(np.uint8)


def land_palette(elevation: np.ndarray) -> np.ndarray:
    stops = np.array([0, 5, 10, 20, 40, 80, 140, 220, 340], dtype=np.float32)
    colors = np.array(
        [
            [238, 220, 139], [214, 201, 116], [177, 188, 98],
            [119, 165, 83], [74, 136, 78], [107, 121, 83],
            [151, 126, 87], [178, 150, 111], [218, 199, 165],
        ],
        dtype=np.float32,
    )
    values = np.clip(elevation, stops[0], stops[-1])
    result = np.zeros((*values.shape, 3), dtype=np.float32)
    for index in range(len(stops) - 1):
        low, high = stops[index], stops[index + 1]
        selected = (values >= low) & (values <= high)
        weight = ((values[selected] - low) / (high - low))[:, None]
        result[selected] = colors[index] * (1 - weight) + colors[index + 1] * weight
    result[values >= stops[-1]] = colors[-1]
    return result.astype(np.uint8)


def hillshade(values: np.ndarray, mask: np.ndarray, strength: float) -> np.ndarray:
    filled = values.copy()
    fill_value = float(np.nanmedian(filled[mask])) if np.any(mask) else 0.0
    filled[~mask] = fill_value
    gradient_y, gradient_x = np.gradient(filled)
    shade = 1.0 - strength * gradient_x + strength * 0.75 * gradient_y
    return np.clip(shade, 0.62, 1.28)


def load_depth(path: Path, max_depth: float) -> tuple[np.ndarray, np.ndarray, tuple]:
    dataset = gdal.Open(str(path))
    values = dataset.GetRasterBand(1).ReadAsArray().astype(np.float32)
    transform = dataset.GetGeoTransform()
    mask = np.isfinite(values) & (values > -1000) & (values >= 0) & (values <= 80)
    depth = np.where(mask, np.clip(values, 0, max_depth), np.nan)
    return depth, mask, transform


def plan_cardinals(rotation_k: int) -> dict[str, str]:
    """Cardinal labels after orienting the source raster with np.rot90."""
    labels = {
        0: {"top": "N", "right": "E", "bottom": "S", "left": "O"},
        1: {"top": "E", "right": "S", "bottom": "O", "left": "N"},
        2: {"top": "S", "right": "O", "bottom": "N", "left": "E"},
        3: {"top": "O", "right": "N", "bottom": "E", "left": "S"},
    }
    return labels[rotation_k % 4]


def load_topography(path: Path, width: int, height: int) -> np.ndarray:
    ds = gdal.Open(str(path))
    band = ds.GetRasterBand(1)
    arr = band.ReadAsArray(buf_xsize=width, buf_ysize=height, resample_alg=gdal.GRIORA_Cubic).astype(np.float32)
    nodata = band.GetNoDataValue()
    if nodata is not None:
        arr = np.where(arr == nodata, np.nan, arr)
    # Cubic WMS resampling can turn -99999 nodata cells into nearby large
    # negative values. Those cells are not elevations.
    arr = np.where(arr < -1000, np.nan, arr)
    return arr


def soften_surface(z: np.ndarray, mask: np.ndarray, passes: int = 8) -> np.ndarray:
    out = np.where(mask, z, np.nan).astype(np.float32)
    fill = float(np.nanmedian(out)) if np.any(np.isfinite(out)) else 0.0
    out = np.where(np.isfinite(out), out, fill)
    for _ in range(passes):
        padded = np.pad(np.where(mask, out, 0), 1, mode="edge")
        mpad = np.pad(mask.astype(np.float32), 1, mode="edge")
        total = (
            padded[:-2, 1:-1]
            + padded[2:, 1:-1]
            + padded[1:-1, :-2]
            + padded[1:-1, 2:]
            + padded[:-2, :-2] * 0.5
            + padded[:-2, 2:] * 0.5
            + padded[2:, :-2] * 0.5
            + padded[2:, 2:] * 0.5
            + 4 * padded[1:-1, 1:-1]
        )
        weight = (
            mpad[:-2, 1:-1]
            + mpad[2:, 1:-1]
            + mpad[1:-1, :-2]
            + mpad[1:-1, 2:]
            + mpad[:-2, :-2] * 0.5
            + mpad[:-2, 2:] * 0.5
            + mpad[2:, :-2] * 0.5
            + mpad[2:, 2:] * 0.5
            + 4 * mpad[1:-1, 1:-1]
        )
        out = np.where(mask & (weight > 0), total / np.maximum(weight, 1), out)
    return out


def soften_rgb(rgb: np.ndarray, mask: np.ndarray, passes: int = 8) -> np.ndarray:
    out = rgb.astype(np.float32)
    for _ in range(passes):
        masked = np.where(mask[:, :, None], out, 0)
        padded = np.pad(masked, ((1, 1), (1, 1), (0, 0)), mode="edge")
        mpad = np.pad(mask.astype(np.float32), 1, mode="edge")
        total = (
            padded[:-2, 1:-1]
            + padded[2:, 1:-1]
            + padded[1:-1, :-2]
            + padded[1:-1, 2:]
            + padded[:-2, :-2] * 0.5
            + padded[:-2, 2:] * 0.5
            + padded[2:, :-2] * 0.5
            + padded[2:, 2:] * 0.5
            + 4 * padded[1:-1, 1:-1]
        )
        weight = (
            mpad[:-2, 1:-1]
            + mpad[2:, 1:-1]
            + mpad[1:-1, :-2]
            + mpad[1:-1, 2:]
            + mpad[:-2, :-2] * 0.5
            + mpad[:-2, 2:] * 0.5
            + mpad[2:, :-2] * 0.5
            + mpad[2:, 2:] * 0.5
            + 4 * mpad[1:-1, 1:-1]
        )
        out = np.where(mask[:, :, None] & (weight[:, :, None] > 0), total / np.maximum(weight[:, :, None], 1), out)
    return np.clip(out, 0, 255)


def resample_array(arr: np.ndarray, scale: int, mode: str = "F") -> np.ndarray:
    if scale == 1:
        return arr
    if arr.dtype == np.bool_:
        img = Image.fromarray((arr.astype(np.uint8) * 255), "L")
        return np.asarray(img.resize((arr.shape[1] * scale, arr.shape[0] * scale), Image.Resampling.LANCZOS)) > 127
    if arr.ndim == 3:
        img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")
        return np.asarray(img.resize((arr.shape[1] * scale, arr.shape[0] * scale), Image.Resampling.BICUBIC)).astype(np.float32)
    img = Image.fromarray(arr.astype(np.float32), mode)
    return np.asarray(img.resize((arr.shape[1] * scale, arr.shape[0] * scale), Image.Resampling.BICUBIC), dtype=np.float32)


def distance_from(mask: np.ndarray, max_steps: int) -> np.ndarray:
    reached = mask.copy()
    dist = np.full(mask.shape, max_steps + 1, dtype=np.float32)
    dist[mask] = 0
    frontier = mask.copy()
    for step in range(1, max_steps + 1):
        frontier = (
            np.pad(reached[:, 1:], ((0, 0), (0, 1)), constant_values=False)
            | np.pad(reached[:, :-1], ((0, 0), (1, 0)), constant_values=False)
            | np.pad(reached[1:, :], ((0, 1), (0, 0)), constant_values=False)
            | np.pad(reached[:-1, :], ((1, 0), (0, 0)), constant_values=False)
        ) & ~reached
        dist[frontier] = step
        reached |= frontier
    return dist


def interpolate_coast_polygon(elev: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Build a continuous land polygon from the terrestrial DEM's 0 m contour."""
    h, w = elev.shape
    coast_y = np.full(w, np.nan, dtype=np.float32)
    stable_kernel = np.ones(9, dtype=np.int16)

    # In this west-coast extent the sea is north (top) and the connected land
    # mass is south (bottom), so one sub-pixel crossing per column describes
    # the coastline without retaining the DEM's block-shaped raster edge.
    for x in range(w):
        column = elev[:, x]
        positive = np.isfinite(column) & (column >= 0.0)
        stable = np.convolve(positive.astype(np.int16), stable_kernel, mode="same") >= 6
        candidates = np.flatnonzero(stable)
        if not len(candidates):
            continue
        y1 = int(candidates[0])
        while y1 > 0 and column[y1 - 1] >= 0.0:
            y1 -= 1
        y0 = max(0, y1 - 1)
        z0 = float(column[y0])
        z1 = float(column[y1])
        if y1 > y0 and np.isfinite(z0) and np.isfinite(z1) and z0 < 0.0 <= z1 and z1 != z0:
            coast_y[x] = y0 + (-z0 / (z1 - z0))
        else:
            coast_y[x] = float(y1)

    known = np.isfinite(coast_y)
    if not np.any(known):
        raise ValueError("No 0 m coastline could be extracted from the elevation raster")
    coast_y = np.interp(np.arange(w), np.flatnonzero(known), coast_y[known]).astype(np.float32)

    # Median rejection removes isolated zero crossings; the Gaussian kernel
    # then interpolates the polygon vertices over about 5 m, preserving bays
    # and points while eliminating metre-scale square steps.
    radius = 6
    padded = np.pad(coast_y, radius, mode="edge")
    coast_y = np.array([np.median(padded[i : i + 2 * radius + 1]) for i in range(w)], dtype=np.float32)
    sigma = 4.5
    kradius = int(np.ceil(3 * sigma))
    xx = np.arange(-kradius, kradius + 1, dtype=np.float32)
    kernel = np.exp(-0.5 * (xx / sigma) ** 2)
    kernel /= kernel.sum()
    coast_y = np.convolve(np.pad(coast_y, kradius, mode="edge"), kernel, mode="valid").astype(np.float32)

    signed_distance = np.arange(h, dtype=np.float32)[:, None] - coast_y[None, :]
    land_mask = signed_distance >= 0.0
    land_weight = np.clip((signed_distance + 1.25) / 2.5, 0.0, 1.0)
    land_weight = land_weight * land_weight * (3.0 - 2.0 * land_weight)
    return coast_y, land_mask, land_weight


def fuse_bathymetry(depth: np.ndarray, bathy_mask: np.ndarray, elev: np.ndarray, land_mask: np.ndarray, max_depth: float) -> tuple[np.ndarray, np.ndarray]:
    """Blend HYSCORES into the negative-elevation surface without fake fills."""
    sea_mask = (np.isfinite(elev) | bathy_mask) & ~land_mask
    topo_depth = np.clip(-np.nan_to_num(elev, nan=-max_depth), 0.0, max_depth)
    source_mask = bathy_mask & sea_mask & np.isfinite(depth)

    # Fade HYSCORES over its first 4 m instead of exposing its pixel boundary.
    distance_inside_source = distance_from(~source_mask, 14)
    source_weight = np.clip(distance_inside_source / 10.0, 0.0, 1.0)
    source_weight *= source_mask
    fused = topo_depth * (1.0 - source_weight) + np.nan_to_num(depth, nan=max_depth) * source_weight
    return np.clip(fused, 0.0, max_depth), sea_mask


def edge_preserving_bathy(depth: np.ndarray, sea_mask: np.ndarray, passes: int = 6) -> np.ndarray:
    """Remove cell-scale spikes while preserving real multi-metre drop-offs."""
    out = depth.astype(np.float32).copy()
    padded = np.pad(out, 2, mode="edge")
    windows = np.lib.stride_tricks.sliding_window_view(padded, (5, 5))
    median = np.median(windows, axis=(-2, -1))
    out = np.where(sea_mask, median, out)

    for _ in range(passes):
        padded = np.pad(out, 1, mode="edge")
        total = np.zeros_like(out)
        weight = np.zeros_like(out)
        for neighbor in (padded[:-2, 1:-1], padded[2:, 1:-1], padded[1:-1, :-2], padded[1:-1, 2:]):
            delta = neighbor - out
            local_weight = np.exp(-((delta / 2.2) ** 2))
            total += local_weight * neighbor
            weight += local_weight
        filtered = (out * 2.0 + total) / (2.0 + weight)
        out = np.where(sea_mask, filtered, out)
    return out


def choose_plan_label(
    lines: list[list[tuple[float, float]]],
    coast_y: np.ndarray,
    width: int,
    height: int,
    occupied: list[tuple[float, float]],
) -> tuple[float, float] | None:
    best: tuple[float, float] | None = None
    best_score = -np.inf
    for line in lines:
        if len(line) < 5:
            continue
        stride = max(1, len(line) // 120)
        for index in range(2, len(line) - 2, stride):
            x, y = line[index]
            if not (45 < x < width - 95 and 25 < y < height - 30):
                continue
            dx = line[index + 2][0] - line[index - 2][0]
            dy = line[index + 2][1] - line[index - 2][1]
            horizontal = abs(dx) / (abs(dx) + abs(dy) + 1e-6)
            coast_gap = max(0.0, float(coast_y[int(np.clip(round(x), 0, width - 1))]) - y)
            edge_gap = min(x - 45, width - 95 - x, y - 25, height - 30 - y)
            separation = min((np.hypot(x - ox, y - oy) for ox, oy in occupied), default=200.0)
            focus_penalty = 0.35 * abs(x - width * 0.64)
            score = edge_gap + 0.55 * coast_gap + 35.0 * horizontal + min(separation, 120.0) - focus_penalty
            if score > best_score:
                best_score = score
                best = (x, y)
    return best


def isolated_contour_center(line: list[tuple[float, float]], min_width: float = 55.0, min_height: float = 28.0) -> tuple[float, float] | None:
    points = np.asarray(line, dtype=np.float32)
    if len(points) < 7 or np.linalg.norm(points[0] - points[-1]) >= 4.0:
        return None
    x0, y0 = points.min(axis=0)
    x1, y1 = points.max(axis=0)
    if x1 - x0 < min_width or y1 - y0 < min_height:
        return None
    return float((x0 + x1) / 2.0), float((y0 + y1) / 2.0)


def smooth_polyline(points: list[tuple[float, float]], passes: int = 3) -> list[tuple[float, float]]:
    if len(points) < 7:
        return points
    arr = np.asarray(points, dtype=np.float32)
    closed = np.linalg.norm(arr[0] - arr[-1]) < 2.0
    kernel = np.array([1, 4, 6, 4, 1], dtype=np.float32) / 16.0
    for _ in range(passes):
        if closed:
            core = arr[:-1]
            padded = np.concatenate([core[-2:], core, core[:2]], axis=0)
            arr = np.column_stack(
                [np.convolve(padded[:, axis], kernel, mode="valid") for axis in range(2)]
            )
            arr = np.vstack([arr, arr[0]])
        else:
            padded = np.pad(arr, ((2, 2), (0, 0)), mode="edge")
            smoothed = np.column_stack(
                [np.convolve(padded[:, axis], kernel, mode="valid") for axis in range(2)]
            )
            smoothed[0], smoothed[-1] = arr[0], arr[-1]
            arr = smoothed
    return [(float(x), float(y)) for x, y in arr]


def extract_isobaths(depth: np.ndarray, sea_mask: np.ndarray, levels: tuple[int, ...] = (5, 10, 15, 20)) -> dict[int, list[list[tuple[float, float]]]]:
    """Extract smooth vector contours in raster pixel coordinates."""
    h, w = depth.shape
    nodata = -9999.0
    raster = gdal.GetDriverByName("MEM").Create("", w, h, 1, gdal.GDT_Float32)
    raster.SetGeoTransform((0, 1, 0, 0, 0, 1))
    band = raster.GetRasterBand(1)
    band.WriteArray(np.where(sea_mask, depth, nodata).astype(np.float32))
    band.SetNoDataValue(nodata)

    vectors = ogr.GetDriverByName("MEM").CreateDataSource("")
    layer = vectors.CreateLayer("isobaths", geom_type=ogr.wkbLineString)
    layer.CreateField(ogr.FieldDefn("level", ogr.OFTReal))
    options = [f"FIXED_LEVELS={','.join(map(str, levels))}", "ELEV_FIELD=0", f"NODATA={nodata}"]
    gdal.ContourGenerateEx(band, layer, options)

    contours: dict[int, list[list[tuple[float, float]]]] = {level: [] for level in levels}
    for feature in layer:
        level = int(round(float(feature["level"])))
        geometry = feature.GetGeometryRef()
        parts = [geometry.GetGeometryRef(i) for i in range(geometry.GetGeometryCount())] if geometry.GetGeometryCount() else [geometry]
        for part in parts:
            simplified = part.Simplify(2.2)
            points = [(simplified.GetX(i), simplified.GetY(i)) for i in range(simplified.GetPointCount())]
            if len(points) < 7:
                continue
            length = float(np.linalg.norm(np.diff(np.asarray(points), axis=0), axis=1).sum())
            if length >= 45.0:
                contours[level].append(smooth_polyline(points, passes=5))
    return contours


@lru_cache(maxsize=4)
def build_fused_surface(depth_path: Path, elevation_path: Path, max_depth: float, rotation_k: int = 0) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict[int, list[list[tuple[float, float]]]]]:
    """Create the single continuous terrain model used by every renderer."""
    contour_ceiling = max_depth + 12.0
    source_depth, bathy_mask, _ = load_depth(depth_path, contour_ceiling)
    elev = load_topography(elevation_path, source_depth.shape[1], source_depth.shape[0])
    rotation_k %= 4
    if rotation_k:
        source_depth = np.rot90(source_depth, rotation_k).copy()
        bathy_mask = np.rot90(bathy_mask, rotation_k).copy()
        elev = np.rot90(elev, rotation_k).copy()
    coast_y, land_mask, land_weight = interpolate_coast_polygon(elev)
    fused_depth, sea_mask = fuse_bathymetry(source_depth, bathy_mask, elev, land_mask, contour_ceiling)
    fused_depth = edge_preserving_bathy(fused_depth, sea_mask)
    signed_coast_distance = np.arange(fused_depth.shape[0], dtype=np.float32)[:, None] - coast_y[None, :]
    sea_ramp = np.clip(-signed_coast_distance / 14.0, 0.0, 1.0)
    sea_ramp = sea_ramp * sea_ramp * (3.0 - 2.0 * sea_ramp)
    fused_depth = np.where(sea_mask, fused_depth * sea_ramp, fused_depth)
    contours = extract_isobaths(fused_depth, sea_mask)
    return elev, coast_y, land_mask, land_weight, fused_depth, contours



def make_clean_plan(depth_path: Path, elevation_path: Path, contours_path: Path, output: Path, title: str, max_depth: float = 20, rotation_k: int = 0) -> None:
    elev, coast_y, land_mask, land_weight, fused_depth, contours = build_fused_surface(depth_path, elevation_path, max_depth, rotation_k)
    d = np.clip(fused_depth, 0.0, max_depth)
    sea_mask = ~land_mask
    valid = sea_mask | land_mask

    sea_rgb = palette(np.nan_to_num(d, nan=max_depth), max_depth=max_depth).astype(np.float32)
    sea_rgb = np.clip(sea_rgb * hillshade(np.nan_to_num(d, nan=max_depth), sea_mask, 0.035)[:, :, None], 0, 255)
    land_color_z = soften_surface(np.clip(np.nan_to_num(elev, nan=0.0), 0, 55), land_mask, passes=2)
    land_rgb = land_palette(land_color_z).astype(np.float32)

    rgb = sea_rgb.copy()
    rgb[~sea_mask] = (7, 18, 55)
    rgb = rgb * (1 - land_weight[:, :, None]) + land_rgb * land_weight[:, :, None]
    rgb[~valid & (land_weight < 0.02)] = (7, 18, 55)

    img = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    draw = ImageDraw.Draw(img, "RGBA")

    label_font = load_font(18, True)
    occupied_labels: list[tuple[float, float]] = []
    for level, lines in contours.items():
        for line in lines:
            draw.line(line, fill=(242, 245, 230, 150), width=4, joint="curve")
            draw.line(line, fill=(10, 15, 22, 205), width=2, joint="curve")

        open_lines = []
        for line in lines:
            center = isolated_contour_center(line)
            is_closed = len(line) >= 2 and np.linalg.norm(np.asarray(line[0]) - np.asarray(line[-1])) < 4.0
            if is_closed:
                if center and all(np.hypot(center[0] - x, center[1] - y) > 70 for x, y in occupied_labels):
                    x, y = center
                    occupied_labels.append(center)
                    draw.text((x - 24, y - 11), f"-{level} m", font=label_font, fill=(5, 8, 15, 235), stroke_width=2, stroke_fill=(245, 244, 222, 230))
                continue
            open_lines.append(line)

        label_point = choose_plan_label(open_lines, coast_y, img.width, img.height, occupied_labels)
        if label_point:
            x, y = label_point
            occupied_labels.append(label_point)
            draw.text((x + 5, y - 11), f"-{level} m", font=label_font, fill=(5, 8, 15, 235), stroke_width=2, stroke_fill=(245, 244, 222, 230))

    coast_points = [(x, float(y)) for x, y in enumerate(coast_y)]
    draw.line(coast_points, fill=(238, 230, 194, 210), width=5, joint="curve")
    draw.line(coast_points, fill=(12, 12, 10, 245), width=3, joint="curve")

    # North-up orientation and a scale based on the raster geotransform.
    annotation_font = load_font(19, True)
    pixel_m = abs(gdal.Open(str(depth_path)).GetGeoTransform()[1])
    bar_px = 50.0 / pixel_m
    sx, sy = 48, img.height - 48
    draw.line((sx, sy, sx + bar_px, sy), fill=(244, 241, 218, 240), width=7)
    draw.line((sx, sy, sx + bar_px, sy), fill=(8, 10, 12, 250), width=3)
    draw.line((sx, sy - 8, sx, sy + 8), fill=(8, 10, 12, 250), width=3)
    draw.line((sx + bar_px, sy - 8, sx + bar_px, sy + 8), fill=(8, 10, 12, 250), width=3)
    draw.text((sx + bar_px / 2 - 22, sy - 31), "50 m", font=annotation_font, fill=(8, 10, 12, 250), stroke_width=2, stroke_fill=(244, 241, 218, 235))

    cx, cy = img.width - 76, 82
    halo = (244, 241, 218, 240)
    ink = (8, 10, 12, 250)
    draw.line((cx - 36, cy, cx + 36, cy), fill=halo, width=7)
    draw.line((cx, cy - 36, cx, cy + 36), fill=halo, width=7)
    draw.line((cx - 36, cy, cx + 36, cy), fill=ink, width=3)
    draw.line((cx, cy - 36, cx, cy + 36), fill=ink, width=3)
    draw.polygon([(cx, cy - 46), (cx - 8, cy - 29), (cx + 8, cy - 29)], fill=ink)
    cardinals = plan_cardinals(rotation_k)
    draw.text((cx, cy - 60), cardinals["top"], font=annotation_font, anchor="mm", fill=ink, stroke_width=2, stroke_fill=halo)
    draw.text((cx, cy + 54), cardinals["bottom"], font=annotation_font, anchor="mm", fill=ink, stroke_width=2, stroke_fill=halo)
    draw.text((cx - 52, cy), cardinals["left"], font=annotation_font, anchor="mm", fill=ink, stroke_width=2, stroke_fill=halo)
    draw.text((cx + 52, cy), cardinals["right"], font=annotation_font, anchor="mm", fill=ink, stroke_width=2, stroke_fill=halo)

    output.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(output, quality=96)



def make_pretty_3d_from_offshore(
    depth_path: Path,
    elevation_path: Path,
    contours_path: Path,
    output: Path,
    title: str,
    max_depth: float = 20,
    decorate: bool = True,
    rotation_k: int = 0,
    camera_tilt: float = 0.34,
    coast_frame_fraction: float = 0.44,
    vertical_exaggeration: float = 7.6,
) -> None:
    elev_full, coast_full, land_full, land_weight_full, fused_depth, contours_full = build_fused_surface(
        depth_path, elevation_path, max_depth, rotation_k
    )
    step = 2
    d = np.clip(fused_depth[::step, ::step], 0.0, max_depth)
    elev = elev_full[::step, ::step]
    land_mask = land_full[::step, ::step]
    land_weight = land_weight_full[::step, ::step]
    sea_mask = ~land_mask
    valid = sea_mask | land_mask
    coast_band = (land_weight > 0.02) & (land_weight < 0.98)

    sea_z = -np.nan_to_num(d, nan=max_depth)
    sea_z = soften_surface(sea_z, sea_mask, passes=2)
    land_z = np.clip(np.nan_to_num(elev, nan=0.0), 0, 55)
    land_z = soften_surface(land_z, land_mask, passes=10)
    coast_sampled = coast_full[::step][: land_z.shape[1]]
    signed_coast_distance = np.arange(land_z.shape[0], dtype=np.float32)[:, None] * step - coast_sampled[None, :]
    land_ramp = np.clip(signed_coast_distance / 14.0, 0.0, 1.0)
    land_ramp = land_ramp * land_ramp * (3.0 - 2.0 * land_ramp)
    land_z *= land_ramp
    z = sea_z * (1.0 - land_weight) + land_z * land_weight

    sea_rgb = palette(np.nan_to_num(d, nan=max_depth), max_depth=max_depth).astype(np.float32)
    land_color_z = soften_surface(np.clip(np.nan_to_num(elev, nan=0.0), 0, 55), land_mask, passes=10)
    land_rgb = land_palette(land_color_z).astype(np.float32)
    colors = np.zeros((*d.shape, 3), dtype=np.float32)
    colors[sea_mask] = sea_rgb[sea_mask]
    colors[land_mask] = land_rgb[land_mask]
    coastal_rgb = sea_rgb * (1 - land_weight[:, :, None]) + land_rgb * land_weight[:, :, None]
    colors[coast_band] = coastal_rgb[coast_band]
    colors = soften_rgb(colors, coast_band, passes=3)

    coast_points = [(x / step, float(y) / step) for x, y in enumerate(coast_full)]
    contour_points = {
        level: [[(x / step, y / step) for x, y in line] for line in lines]
        for level, lines in contours_full.items()
    }

    render_interp = 3 if not decorate else 2
    if render_interp > 1:
        z = resample_array(z, render_interp)
        colors = resample_array(colors, render_interp)
        valid = resample_array(valid, render_interp)
        land_mask = resample_array(land_mask, render_interp)
        coast_points = [(x * render_interp, y * render_interp) for x, y in coast_points]
        contour_points = {
            level: [[(x * render_interp, y * render_interp) for x, y in line] for line in lines]
            for level, lines in contour_points.items()
        }

    original_h, original_w = z.shape
    pad_x = 45 * render_interp
    pad_north = 24 * render_interp
    pad_south = 24 * render_interp
    # The foreground support lies outside the mapped footprint. Continue it
    # smoothly toward the deepest displayed colour instead of reflecting the
    # real relief, which would create false mirrored peaks at the bottom edge.
    z = np.pad(z, ((0, 0), (pad_x, pad_x)), mode="reflect")
    colors = np.pad(colors, ((0, 0), (pad_x, pad_x), (0, 0)), mode="reflect")
    valid = np.pad(valid, ((0, 0), (pad_x, pad_x)), mode="reflect")
    land_mask = np.pad(land_mask, ((0, 0), (pad_x, pad_x)), mode="reflect")

    blend = np.linspace(1.0, 0.0, pad_north, dtype=np.float32)[:, None]
    edge_weight = (1.0 - blend) ** 3
    kernel = np.ones(121, dtype=np.float32) / 121.0
    smooth_edge_z = np.convolve(np.pad(z[0], 60, mode="reflect"), kernel, mode="valid")[None, :]
    local_edge_weight = (1.0 - blend) ** 8
    support_edge_z = smooth_edge_z + (z[0:1] - smooth_edge_z) * local_edge_weight
    foreground_z = -max_depth * (1.0 - edge_weight) + support_edge_z * edge_weight
    deep_rgb = palette(np.array([max_depth], dtype=np.float32), max_depth=max_depth)[0]
    smooth_edge_colors = np.stack(
        [np.convolve(np.pad(colors[0, :, channel], 60, mode="reflect"), kernel, mode="valid") for channel in range(3)],
        axis=-1,
    )[None, :, :]
    support_edge_colors = smooth_edge_colors + (colors[0:1] - smooth_edge_colors) * local_edge_weight[:, :, None]
    foreground_colors = deep_rgb[None, None, :] * (1.0 - edge_weight[:, :, None]) + support_edge_colors * edge_weight[:, :, None]
    z = np.concatenate([foreground_z, z, np.pad(z[-1:], ((0, pad_south - 1), (0, 0)), mode="edge")], axis=0)
    colors = np.concatenate(
        [foreground_colors, colors, np.pad(colors[-1:], ((0, pad_south - 1), (0, 0), (0, 0)), mode="edge")],
        axis=0,
    )
    valid = np.concatenate(
        [np.ones((pad_north, valid.shape[1]), dtype=valid.dtype), valid, np.repeat(valid[-1:], pad_south, axis=0)],
        axis=0,
    )
    land_mask = np.concatenate(
        [np.zeros((pad_north, land_mask.shape[1]), dtype=land_mask.dtype), land_mask, np.repeat(land_mask[-1:], pad_south, axis=0)],
        axis=0,
    )
    coast_points = [(x + pad_x, y + pad_north) for x, y in coast_points]
    contour_points = {
        level: [[(x + pad_x, y + pad_north) for x, y in line] for line in lines]
        for level, lines in contour_points.items()
    }

    h, w = z.shape
    final_canvas_w, final_canvas_h = 1455, 1069
    aa = 2
    canvas_w, canvas_h = final_canvas_w * aa, final_canvas_h * aa
    sky = np.array((198, 219, 228), dtype=np.float32)
    abyss = deep_rgb.astype(np.float32)
    background_mix = np.linspace(0.0, 1.0, canvas_h, dtype=np.float32)[:, None, None]
    background = sky[None, None, :] * (1.0 - background_mix) + abyss[None, None, :] * background_mix
    background = np.repeat(background, canvas_w, axis=1).astype(np.uint8)
    canvas = Image.fromarray(background, "RGB").convert("RGBA")
    draw = ImageDraw.Draw(canvas, "RGBA")

    # Same east-west footprint and scale as the 2D map: one source pixel maps
    # to one final image pixel. North-south remains foreshortened by projection.
    zoom = 2.0
    scale = zoom * aa / render_interp
    tilt = camera_tilt
    zscale = vertical_exaggeration * aa
    original_valid = valid[pad_north : pad_north + original_h, pad_x : pad_x + original_w]
    yy, xx = np.where(original_valid)
    yy = yy + pad_north
    xx = xx + pad_x

    focus_x = pad_x + original_w * 0.50

    def raw_project(px: np.ndarray | float, py: np.ndarray | float, zv: np.ndarray | float):
        # Observer au nord regardant vers le sud: l'est est a gauche et
        # l'ouest a droite, contrairement au plan 2D nord en haut.
        x = -(px - focus_x) * scale
        y = -(py - h / 2) * tilt * scale - zv * zscale
        return x, y

    rx, ry = raw_project(xx, yy, z[yy, xx])
    ox = canvas_w / 2
    coast_xs = np.asarray([point[0] for point in coast_points], dtype=np.float32)
    coast_ys = np.asarray([point[1] for point in coast_points], dtype=np.float32)
    _, raw_coast_y = raw_project(coast_xs, coast_ys, np.zeros_like(coast_xs))
    oy = canvas_h * coast_frame_fraction - float(np.median(raw_coast_y))

    def project(px: float, py: float, zv: float) -> tuple[float, float]:
        x, y = raw_project(px, py, zv)
        return ox + float(x), oy + float(y)

    gy, gx = np.gradient(z)
    nx = -gx * 0.52
    ny = -gy * 0.52
    nz = np.ones_like(z)
    norm = np.sqrt(nx * nx + ny * ny + nz * nz)
    nx, ny, nz = nx / norm, ny / norm, nz / norm
    light = np.array([-0.55, -0.45, 0.70], dtype=np.float32)
    light = light / np.linalg.norm(light)
    diffuse = np.clip(nx * light[0] + ny * light[1] + nz * light[2], 0, 1)
    relief_shade = np.clip(0.35 + 0.93 * diffuse, 0.35, 1.28)
    cast_shadow = np.clip(1.0 - 0.032 * np.maximum(gy, 0) - 0.020 * np.maximum(gx, 0), 0.70, 1.0)
    relief_shade *= cast_shadow
    for j in range(h - 2, -1, -1):
        for i in range(w - 1):
            if not (valid[j, i] and valid[j + 1, i] and valid[j, i + 1] and valid[j + 1, i + 1]):
                continue
            pts = [
                project(i, j, float(z[j, i])),
                project(i + 1, j, float(z[j, i + 1])),
                project(i + 1, j + 1, float(z[j + 1, i + 1])),
                project(i, j + 1, float(z[j + 1, i])),
            ]
            c = colors[j, i].astype(np.float32)
            shade = float(relief_shade[j, i])
            if land_mask[j, i]:
                shade = np.clip(shade * 1.05, 0.48, 1.28)
            draw.polygon(pts, fill=tuple(np.clip(c * shade, 0, 255).astype(np.uint8).tolist()) + (255,))

    # Vector lines are projected on the same surface after the mesh, so they
    # remain smooth and readable even across steep submarine walls.
    projected_contours: dict[int, list[list[tuple[float, float]]]] = {level: [] for level in contour_points}
    for level, lines in contour_points.items():
        for line in lines:
            points = [project(x, y, -float(level)) for x, y in line]
            if len(points) >= 2:
                projected_contours[level].append(points)
                draw.line(points, fill=(242, 235, 204, 205), width=4 * aa, joint="curve")
                draw.line(points, fill=(5, 7, 10, 235), width=2 * aa, joint="curve")

    projected_coast = [project(x, y, 0.0) for x, y in coast_points]
    draw.line(projected_coast, fill=(242, 235, 204, 230), width=8 * aa, joint="curve")
    draw.line(projected_coast, fill=(3, 3, 3, 255), width=4 * aa, joint="curve")

    canvas = canvas.resize((final_canvas_w, final_canvas_h), Image.Resampling.LANCZOS)
    crop_left = 0
    crop_top = 0
    draw = ImageDraw.Draw(canvas, "RGBA")

    if not decorate:
        label_font = load_font(20, True)
        occupied: list[tuple[float, float]] = []
        for level in (5, 10, 15, 20):
            transformed_lines = [
                [(x / aa - crop_left, y / aa - crop_top) for x, y in line]
                for line in projected_contours.get(level, [])
            ]
            open_lines = []
            for line in transformed_lines:
                center = isolated_contour_center(line, min_width=70.0, min_height=30.0)
                is_closed = len(line) >= 2 and np.linalg.norm(np.asarray(line[0]) - np.asarray(line[-1])) < 4.0
                if is_closed:
                    placed = False
                    if center and 55 < center[0] < canvas.width - 100 and 35 < center[1] < canvas.height - 35:
                        if all(np.hypot(center[0] - x, center[1] - y) > 80 for x, y in occupied):
                            x, y = center
                            occupied.append(center)
                            draw.text((x - 27, y - 13), f"-{level} m", font=label_font, fill=(3, 4, 6, 245), stroke_width=2, stroke_fill=(245, 239, 210, 235))
                            placed = True
                    if placed:
                        continue
                open_lines.append(line)

            best = None
            best_score = -np.inf
            for line in open_lines:
                stride = max(1, len(line) // 100)
                for index in range(2, len(line) - 2, stride):
                    x, y = line[index]
                    if not (55 < x < canvas.width - 100 and 35 < y < canvas.height - 35):
                        continue
                    dx = line[index + 2][0] - line[index - 2][0]
                    dy = line[index + 2][1] - line[index - 2][1]
                    horizontal = abs(dx) / (abs(dx) + abs(dy) + 1e-6)
                    edge_gap = min(x - 55, canvas.width - 100 - x, y - 35, canvas.height - 35 - y)
                    separation = min((np.hypot(x - ox, y - oy) for ox, oy in occupied), default=250.0)
                    focus_penalty = 0.32 * abs(x - canvas.width * 0.48)
                    score = edge_gap + 55.0 * horizontal + min(separation, 160.0) - focus_penalty
                    if score > best_score:
                        best_score = score
                        best = (x, y)
            if best is None:
                near_frame = [
                    (x, y)
                    for line in open_lines
                    for x, y in line
                    if 55 < x < canvas.width - 100 and -25 < y < canvas.height + 25
                ]
                if near_frame:
                    x, y = min(near_frame, key=lambda point: abs(point[0] - canvas.width / 2))
                    best = (x, float(np.clip(y, 35, canvas.height - 35)))
            if best:
                x, y = best
                occupied.append(best)
                draw.text((x + 6, y - 13), f"-{level} m", font=label_font, fill=(3, 4, 6, 245), stroke_width=2, stroke_fill=(245, 239, 210, 235))

        annotation_font = load_font(20, True)
        pixel_m = abs(gdal.Open(str(depth_path)).GetGeoTransform()[1])
        bar_px = 50.0 * zoom / step / pixel_m
        sx, sy = 55, canvas.height - 50
        draw.line((sx, sy, sx + bar_px, sy), fill=(245, 239, 210, 245), width=8)
        draw.line((sx, sy, sx + bar_px, sy), fill=(5, 7, 10, 255), width=3)
        draw.line((sx, sy - 9, sx, sy + 9), fill=(5, 7, 10, 255), width=3)
        draw.line((sx + bar_px, sy - 9, sx + bar_px, sy + 9), fill=(5, 7, 10, 255), width=3)
        draw.text((sx + bar_px / 2 - 24, sy - 34), "50 m", font=annotation_font, fill=(5, 7, 10, 255), stroke_width=2, stroke_fill=(245, 239, 210, 235))

        # The observer is offshore: oriented-raster top is foreground/down;
        # horizontal directions are mirrored by the view toward land.
        cx, cy = canvas.width - 92, 84
        halo = (245, 239, 210, 240)
        ink = (5, 7, 10, 255)
        draw.line((cx - 42, cy, cx + 42, cy), fill=halo, width=8)
        draw.line((cx, cy - 42, cx, cy + 42), fill=halo, width=8)
        draw.line((cx - 42, cy, cx + 42, cy), fill=ink, width=3)
        draw.line((cx, cy - 42, cx, cy + 42), fill=ink, width=3)
        draw.polygon([(cx, cy + 51), (cx - 9, cy + 34), (cx + 9, cy + 34)], fill=ink)
        cardinals = plan_cardinals(rotation_k)
        draw.text((cx, cy + 64), cardinals["top"], font=annotation_font, anchor="mm", fill=ink, stroke_width=2, stroke_fill=halo)
        draw.text((cx, cy - 60), cardinals["bottom"], font=annotation_font, anchor="mm", fill=ink, stroke_width=2, stroke_fill=halo)
        draw.text((cx - 60, cy), cardinals["right"], font=annotation_font, anchor="mm", fill=ink, stroke_width=2, stroke_fill=halo)
        draw.text((cx + 60, cy), cardinals["left"], font=annotation_font, anchor="mm", fill=ink, stroke_width=2, stroke_fill=halo)

    if decorate:
        title_font = load_font(44, True)
        sub_font = load_font(22, True)
        text_font = load_font(20)
        draw.rounded_rectangle((48, 42, 1170, 160), radius=12, fill=(7, 18, 55, 215), outline=(220, 240, 255, 90), width=2)
        draw.text((74, 58), f"{title} - vue 3D depuis le nord", font=title_font, fill=(255, 255, 255, 255))
        draw.text((76, 111), "Rendu lisse: topo IGN RGE ALTI + bathymetrie HYSCORES, ombrage de relief", font=sub_font, fill=(215, 238, 255, 245))

        lx, ly = 70, 1245
        draw.rounded_rectangle((lx - 22, ly - 34, lx + 585, ly + 92), radius=12, fill=(7, 18, 55, 220))
        draw.text((lx, ly - 20), "Profondeur / altitude", font=sub_font, fill=(255, 255, 255, 255))
        vals = [0, 5, 10, 15, 20]
        cols = palette(np.array(vals, dtype=np.float32), max_depth=max_depth)
        for idx, (val, col) in enumerate(zip(vals, cols)):
            x = lx + idx * 82
            y = ly + 18
            draw.rectangle((x, y, x + 76, y + 23), fill=tuple(map(int, col)) + (255,))
            draw.text((x + 4, y + 27), f"{-val if val else 0} m", font=text_font, fill=(238, 244, 255, 245))
        land_vals = [0, 10, 30, 50]
        land_cols = land_palette(np.array(land_vals, dtype=np.float32))
        for idx, (val, col) in enumerate(zip(land_vals, land_cols)):
            x = lx + idx * 82
            y = ly + 70
            draw.rectangle((x, y, x + 76, y + 23), fill=tuple(map(int, col)) + (255,))
            draw.text((x + 4, y + 27), f"+{val} m", font=text_font, fill=(238, 244, 255, 245))

        draw.text((1640, 1215), "observateur au nord, regard vers le sud", font=text_font, fill=(235, 243, 255, 235))
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(output, quality=95)


def main() -> int:
    if len(sys.argv) == 6 and sys.argv[1] == "all":
        depth_path = Path(sys.argv[2])
        elevation_path = Path(sys.argv[3])
        output_prefix = Path(sys.argv[4])
        title = sys.argv[5]
        plan_output = output_prefix.with_name(output_prefix.name + "-2d.jpg")
        relief_output = output_prefix.with_name(output_prefix.name + "-3d.jpg")
        unused_contours = Path("-")
        make_clean_plan(depth_path, elevation_path, unused_contours, plan_output, title)
        make_pretty_3d_from_offshore(depth_path, elevation_path, unused_contours, relief_output, title, decorate=False)
        print(plan_output)
        print(relief_output)
        return 0
    if len(sys.argv) != 7:
        print("usage: render_fused_relief.py all depth-positive.tif elevation.tif output-prefix title", file=sys.stderr)
        print("legacy: render_fused_relief.py mode depth-positive.tif elevation.tif contours.geojson output.jpg title", file=sys.stderr)
        return 2
    mode = sys.argv[1]
    depth_path, elevation_path, contours_path, output = map(Path, sys.argv[2:6])
    title = sys.argv[6]
    if mode == "cleanplan":
        make_clean_plan(depth_path, elevation_path, contours_path, output, title)
    elif mode == "pretty3d":
        make_pretty_3d_from_offshore(depth_path, elevation_path, contours_path, output, title)
    elif mode == "clean3d":
        make_pretty_3d_from_offshore(depth_path, elevation_path, contours_path, output, title, decorate=False)
    else:
        raise ValueError(mode)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
