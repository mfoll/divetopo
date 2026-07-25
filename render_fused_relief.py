from __future__ import annotations

import argparse
import warnings
from collections import deque
from functools import lru_cache
from pathlib import Path

import numpy as np
from osgeo import gdal, ogr, osr
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from site_config import DEFAULT_RELIEF_EXPOSURE, DEFAULT_VERTICAL_EXAGGERATION


gdal.UseExceptions()
osr.UseExceptions()

NO_DATA_RGB = np.array([69, 78, 82], dtype=np.float32)
MAP_FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
MAP_FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
WEBGL_MATERIAL_RGB = (216, 224, 213)
WEBGL_HEMISPHERE_SKY_RGB = (223, 251, 255)
WEBGL_HEMISPHERE_GROUND_RGB = (16, 38, 45)
WEBGL_KEY_LIGHT_RGB = (255, 242, 216)


def load_font(size: int, bold: bool = False):
    path = MAP_FONT_BOLD if bold else MAP_FONT
    try:
        return ImageFont.truetype(path, size)
    except OSError as error:
        raise RuntimeError(f"Unable to load the required map font {path!r}") from error


def resize_exact_without_distortion(image: Image.Image, size: tuple[int, int] | list[int]) -> Image.Image:
    """Resize to exact dimensions with one uniform scale factor.

    Image.resize() accepts independent horizontal and vertical factors, which
    silently distorted an oblique view when its post-crop aspect ratio did not
    match the configured final size. ImageOps.fit preserves geometry and only
    crops the minimum excess needed to reach the exact output dimensions.
    """
    width, height = map(int, size)
    if width <= 0 or height <= 0:
        raise ValueError("Final output dimensions must be positive")
    return ImageOps.fit(
        image,
        (width, height),
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )


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
    # The standard orthophoto treatment is opaque to 1.5 m and fades out at
    # 2 m. Make 2 m the chromatic zero so the first fully bathymetric pixels
    # are red, while preserving the original colour at each site's maximum
    # displayed depth.
    shallow_red_depth = 2.0
    if max_depth > shallow_red_depth:
        remapped_depth = np.maximum(depth - shallow_red_depth, 0.0) * max_depth / (max_depth - shallow_red_depth)
    else:
        remapped_depth = np.maximum(depth - shallow_red_depth, 0.0)
    values = np.clip(remapped_depth, stops[0], min(max_depth, stops[-1]))
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


def deep_edge_nodata_display_mask(
    depth: np.ndarray,
    surface_valid: np.ndarray,
    land_mask: np.ndarray,
    max_depth: float,
    *,
    deep_fraction: float = 0.9,
    min_boundary_pixels: int = 8,
    component_diagnostics: list[dict[str, float | int | bool]] | None = None,
) -> np.ndarray:
    """Identify offshore edge gaps that may use the maximum-depth colour.

    This mask is deliberately display-only. It never changes surface validity,
    bathymetry, contours, or the 3D terrain. An invalid component qualifies
    only when it reaches the map edge, has a sufficiently long boundary with
    known sea, never touches known land, and every known sea neighbour is
    already within the deepest 10% of the displayed scale.
    """
    if depth.shape != surface_valid.shape or land_mask.shape != surface_valid.shape:
        raise ValueError("Depth, validity, and land masks must have identical shapes")
    if max_depth <= 0.0:
        raise ValueError("Maximum depth must be positive")
    if not 0.0 < deep_fraction <= 1.0:
        raise ValueError("Deep-edge fraction must be in (0, 1]")
    if min_boundary_pixels <= 0:
        raise ValueError("Minimum boundary length must be positive")

    invalid = ~surface_valid
    display_mask = np.zeros_like(invalid)
    visited = np.zeros_like(invalid)
    height, width = invalid.shape
    if height == 0 or width == 0:
        return display_mask

    edge_seeds = [
        *((0, x) for x in range(width)),
        *((height - 1, x) for x in range(width)),
        *((y, 0) for y in range(1, height - 1)),
        *((y, width - 1) for y in range(1, height - 1)),
    ]
    deep_threshold = max_depth * deep_fraction

    for seed_y, seed_x in edge_seeds:
        if visited[seed_y, seed_x] or not invalid[seed_y, seed_x]:
            continue

        queue = deque([(seed_y, seed_x)])
        visited[seed_y, seed_x] = True
        component_y: list[int] = []
        component_x: list[int] = []
        sea_boundary_depths: list[float] = []
        touches_land = False

        while queue:
            y, x = queue.popleft()
            component_y.append(y)
            component_x.append(x)
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                neighbor_y = y + dy
                neighbor_x = x + dx
                if not (0 <= neighbor_y < height and 0 <= neighbor_x < width):
                    continue
                if invalid[neighbor_y, neighbor_x]:
                    if not visited[neighbor_y, neighbor_x]:
                        visited[neighbor_y, neighbor_x] = True
                        queue.append((neighbor_y, neighbor_x))
                    continue
                if land_mask[neighbor_y, neighbor_x]:
                    touches_land = True
                    continue
                neighbor_depth = float(depth[neighbor_y, neighbor_x])
                if np.isfinite(neighbor_depth):
                    sea_boundary_depths.append(neighbor_depth)

        qualifies = (
            not touches_land
            and len(sea_boundary_depths) >= min_boundary_pixels
            and min(sea_boundary_depths) >= deep_threshold
        )
        if component_diagnostics is not None:
            component_diagnostics.append(
                {
                    "cells": len(component_y),
                    "boundary_pixels": len(sea_boundary_depths),
                    "boundary_min_depth_m": (
                        min(sea_boundary_depths)
                        if sea_boundary_depths
                        else float("nan")
                    ),
                    "boundary_max_depth_m": (
                        max(sea_boundary_depths)
                        if sea_boundary_depths
                        else float("nan")
                    ),
                    "touches_land": touches_land,
                    "qualifies": qualifies,
                }
            )
        if qualifies:
            display_mask[component_y, component_x] = True

    return display_mask


def fill_deep_edge_nodata_at_maximum(
    depth: np.ndarray,
    surface_valid: np.ndarray,
    land_mask: np.ndarray,
    max_depth: float,
    *,
    min_boundary_depth_m: float | None = None,
    component_diagnostics: list[dict[str, float | int | bool]] | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Fill qualifying deep edge gaps with a flat maximum-depth surface.

    This is intentionally more explicit than the display-only 2D convention:
    callers opt in before using the returned validity mask for terrain. The
    source arrays remain unchanged, contours remain source-derived, and the
    fill has no intermediate relief. Shallow, internal, and land-adjacent gaps
    are rejected by :func:`deep_edge_nodata_display_mask`. The default keeps
    the display rule's deepest-10% boundary; a site may set an explicit
    minimum known-sea boundary depth when source coverage ends earlier.
    """
    if min_boundary_depth_m is None:
        deep_fraction = 0.9
    else:
        if not 0.0 < min_boundary_depth_m <= max_depth:
            raise ValueError(
                "Minimum deep-edge boundary depth must be in (0, max_depth]"
            )
        deep_fraction = min_boundary_depth_m / max_depth
    fill_mask = deep_edge_nodata_display_mask(
        depth,
        surface_valid,
        land_mask,
        max_depth,
        deep_fraction=deep_fraction,
        component_diagnostics=component_diagnostics,
    )
    filled_depth = depth.copy()
    filled_depth[fill_mask] = max_depth
    return filled_depth, surface_valid | fill_mask, fill_mask


def small_internal_mesh_gap_mask(
    surface_valid: np.ndarray,
    land_mask: np.ndarray,
    max_component_pixels: int,
) -> np.ndarray:
    """Select tiny enclosed sea-data gaps that may be interpolated for 3D only.

    Edge-connected gaps, large components, and gaps adjoining known land stay
    invalid. The returned mask is intended for the relief mesh after contours
    have already been extracted from the unmodified source surface.
    """
    if surface_valid.shape != land_mask.shape:
        raise ValueError("Validity and land masks must have identical shapes")
    if max_component_pixels <= 0:
        raise ValueError("Maximum component size must be positive")

    invalid = ~surface_valid
    selected = np.zeros_like(invalid)
    visited = np.zeros_like(invalid)
    height, width = invalid.shape

    for seed_y, seed_x in zip(*np.nonzero(invalid)):
        if visited[seed_y, seed_x]:
            continue
        queue = deque([(int(seed_y), int(seed_x))])
        visited[seed_y, seed_x] = True
        component: list[tuple[int, int]] = []
        touches_edge = False
        touches_land = False
        has_valid_boundary = False

        while queue:
            y, x = queue.popleft()
            component.append((y, x))
            touches_edge |= y in (0, height - 1) or x in (0, width - 1)
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                neighbor_y = y + dy
                neighbor_x = x + dx
                if not (0 <= neighbor_y < height and 0 <= neighbor_x < width):
                    continue
                if invalid[neighbor_y, neighbor_x]:
                    if not visited[neighbor_y, neighbor_x]:
                        visited[neighbor_y, neighbor_x] = True
                        queue.append((neighbor_y, neighbor_x))
                    continue
                has_valid_boundary = True
                touches_land |= bool(land_mask[neighbor_y, neighbor_x])

        if (
            len(component) <= max_component_pixels
            and not touches_edge
            and not touches_land
            and has_valid_boundary
        ):
            ys, xs = zip(*component)
            selected[ys, xs] = True

    return selected


def interpolate_mesh_gaps(
    values: np.ndarray,
    fill_mask: np.ndarray,
    source_valid: np.ndarray,
) -> np.ndarray:
    """Interpolate selected mesh gaps from their valid four-neighbour boundary."""
    if values.shape[:2] != fill_mask.shape or fill_mask.shape != source_valid.shape:
        raise ValueError("Values, fill mask, and validity mask must share a grid")
    result = values.copy()
    visited = np.zeros_like(fill_mask)
    height, width = fill_mask.shape

    for seed_y, seed_x in zip(*np.nonzero(fill_mask)):
        if visited[seed_y, seed_x]:
            continue
        queue = deque([(int(seed_y), int(seed_x))])
        visited[seed_y, seed_x] = True
        component: list[tuple[int, int]] = []
        boundary: set[tuple[int, int]] = set()

        while queue:
            y, x = queue.popleft()
            component.append((y, x))
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                neighbor_y = y + dy
                neighbor_x = x + dx
                if not (0 <= neighbor_y < height and 0 <= neighbor_x < width):
                    continue
                if fill_mask[neighbor_y, neighbor_x]:
                    if not visited[neighbor_y, neighbor_x]:
                        visited[neighbor_y, neighbor_x] = True
                        queue.append((neighbor_y, neighbor_x))
                elif source_valid[neighbor_y, neighbor_x]:
                    boundary.add((neighbor_y, neighbor_x))

        if not boundary:
            continue
        boundary_coordinates = np.asarray(sorted(boundary), dtype=np.float32)
        boundary_values = result[
            boundary_coordinates[:, 0].astype(int),
            boundary_coordinates[:, 1].astype(int),
        ]
        for y, x in component:
            squared_distance = (
                (boundary_coordinates[:, 0] - y) ** 2
                + (boundary_coordinates[:, 1] - x) ** 2
            )
            weights = 1.0 / np.maximum(squared_distance, 0.25)
            if values.ndim == 2:
                result[y, x] = np.average(boundary_values, weights=weights)
            else:
                result[y, x] = np.average(
                    boundary_values,
                    axis=0,
                    weights=weights,
                )

    return result


def island_palette(elevation: np.ndarray) -> np.ndarray:
    stops = np.array([0, 150, 400, 800, 1300, 1900, 2500, 3100], dtype=np.float32)
    colors = np.array(
        [
            [105, 174, 116], [137, 190, 126], [184, 204, 139], [222, 211, 151],
            [205, 178, 125], [171, 137, 103], [137, 111, 94], [222, 215, 197],
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


def make_locator_map(
    elevation_path: Path,
    output: Path,
    marker_utm40s: tuple[float, float],
    marker_label: str,
    output_width: int = 2400,
    bathymetry_path: Path | None = None,
    bathymetry_blur_px: float = 8.0,
    attribution_text: str = "Topographie : IGN RGE ALTI",
) -> None:
    """Render an island-wide relief map with a geographic grid and site marker."""
    dataset = gdal.Open(str(elevation_path))
    if dataset is None:
        raise RuntimeError(f"Cannot open locator elevation raster {elevation_path}")
    elevation = dataset.GetRasterBand(1).ReadAsArray().astype(np.float32)
    transform = dataset.GetGeoTransform()
    land = np.isfinite(elevation) & (elevation > -1000.0) & (elevation >= 0.0)
    terrain = np.where(land, np.clip(elevation, 0.0, 3200.0), 0.0)

    gradient_row, gradient_col = np.gradient(terrain, abs(transform[5]), abs(transform[1]))
    dz_east = gradient_col
    dz_north = -gradient_row
    nx, ny, nz = -dz_east, -dz_north, np.ones_like(terrain)
    norm = np.sqrt(nx * nx + ny * ny + nz * nz)
    nx, ny, nz = nx / norm, ny / norm, nz / norm
    light = np.array([-0.48, 0.48, 0.73], dtype=np.float32)
    light /= np.linalg.norm(light)
    shade = np.clip(0.46 + 0.78 * np.clip(nx * light[0] + ny * light[1] + nz * light[2], 0.0, 1.0), 0.46, 1.22)

    height, width = elevation.shape
    ocean_y = np.linspace(0.0, 1.0, height, dtype=np.float32)[:, None, None]
    ocean_top = np.array([100, 184, 218], dtype=np.float32)
    ocean_bottom = np.array([60, 139, 187], dtype=np.float32)
    ocean_gradient = np.repeat(ocean_top[None, None, :] * (1.0 - ocean_y) + ocean_bottom[None, None, :] * ocean_y, width, axis=1)
    if bathymetry_path is None:
        rgb = ocean_gradient
    else:
        bathymetry = load_rgb_raster(bathymetry_path, elevation_path)
        bathymetry_image = Image.fromarray(np.clip(bathymetry, 0, 255).astype(np.uint8), "RGB")
        bathymetry = np.asarray(bathymetry_image.filter(ImageFilter.GaussianBlur(bathymetry_blur_px)), dtype=np.float32)
        rgb = bathymetry * 0.82 + ocean_gradient * 0.18

    land_mask_image = Image.fromarray((land.astype(np.uint8) * 255), "L")
    coastal_glow = np.asarray(land_mask_image.filter(ImageFilter.GaussianBlur(45)), dtype=np.float32) / 255.0
    coastal_glow = np.clip(coastal_glow - land.astype(np.float32), 0.0, 1.0)
    rgb += coastal_glow[:, :, None] * np.array([35.0, 40.0, 28.0], dtype=np.float32)

    land_rgb = island_palette(terrain).astype(np.float32) * shade[:, :, None]
    rgb[land] = np.clip(land_rgb[land], 0, 255)
    image = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB")

    output_height = int(round(output_width * height / width))
    image = image.resize((output_width, output_height), Image.Resampling.LANCZOS).convert("RGBA")
    scale_x = output_width / width
    scale_y = output_height / height

    coast_edge = land_mask_image.filter(ImageFilter.FIND_EDGES).resize(image.size, Image.Resampling.LANCZOS)
    coast_alpha = coast_edge.point(lambda value: min(210, value * 2))
    coast_layer = Image.new("RGBA", image.size, (23, 91, 102, 0))
    coast_layer.putalpha(coast_alpha)
    image = Image.alpha_composite(image, coast_layer)
    draw = ImageDraw.Draw(image, "RGBA")

    min_x = transform[0]
    max_y = transform[3]

    def map_xy(easting: float, northing: float) -> tuple[float, float]:
        return (easting - min_x) / transform[1] * scale_x, (northing - max_y) / transform[5] * scale_y

    geographic = osr.SpatialReference()
    geographic.ImportFromEPSG(4326)
    geographic.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    projected = osr.SpatialReference()
    projected.ImportFromEPSG(32740)
    projected.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    to_utm = osr.CoordinateTransformation(geographic, projected)

    grid_color = (26, 84, 104, 78)
    grid_width = max(1, round(output_width / 1200))
    longitude_ticks = [55.0 + minute / 60.0 for minute in (10, 20, 30, 40, 50)]
    latitude_ticks = [-(20.0 + minute / 60.0) for minute in (50, 60, 70, 80)]
    for longitude in longitude_ticks:
        points = []
        for latitude in np.linspace(-21.48, -20.75, 160):
            easting, northing, _ = to_utm.TransformPoint(longitude, float(latitude))
            points.append(map_xy(easting, northing))
        draw.line(points, fill=grid_color, width=grid_width)
    for latitude in latitude_ticks:
        points = []
        for longitude in np.linspace(55.05, 55.98, 180):
            easting, northing, _ = to_utm.TransformPoint(float(longitude), latitude)
            points.append(map_xy(easting, northing))
        draw.line(points, fill=grid_color, width=grid_width)

    label_font = load_font(round(output_width * 0.015), True)
    small_font = load_font(round(output_width * 0.013), True)
    halo = (236, 244, 238, 235)
    ink = (10, 39, 52, 240)
    stroke = max(2, round(output_width / 1000))
    for longitude in longitude_ticks:
        easting, northing, _ = to_utm.TransformPoint(longitude, -20.80)
        x, _ = map_xy(easting, northing)
        degrees = int(longitude)
        minutes = int(round((longitude - degrees) * 60))
        draw.text((x, 18), f"{degrees}°{minutes:02d}′ E", anchor="ma", font=small_font, fill=ink, stroke_width=stroke, stroke_fill=halo)
    for latitude in latitude_ticks:
        easting, northing, _ = to_utm.TransformPoint(55.08, latitude)
        _, y = map_xy(easting, northing)
        absolute = abs(latitude)
        degrees = int(absolute)
        minutes = int(round((absolute - degrees) * 60))
        y = max(34.0, min(output_height - 34.0, y))
        draw.text((output_width - 18, y), f"{degrees}°{minutes:02d}′ S", anchor="rm", font=small_font, fill=ink, stroke_width=stroke, stroke_fill=halo)

    marker_x, marker_y = map_xy(float(marker_utm40s[0]), float(marker_utm40s[1]))
    radius = output_width * 0.012
    draw.ellipse((marker_x - radius - 4, marker_y - radius - 4, marker_x + radius + 4, marker_y + radius + 4), fill=(8, 20, 25, 155))
    draw.ellipse((marker_x - radius, marker_y - radius, marker_x + radius, marker_y + radius), fill=(220, 38, 38, 255), outline=(255, 247, 227, 255), width=max(4, round(output_width / 500)))
    draw.ellipse((marker_x - radius * 0.40, marker_y - radius * 0.50, marker_x - radius * 0.05, marker_y - radius * 0.15), fill=(255, 155, 145, 220))
    draw.text((marker_x + radius * 1.45, marker_y), marker_label, anchor="lm", font=label_font, fill=(13, 25, 26, 255), stroke_width=stroke + 1, stroke_fill=(249, 245, 224, 245))

    metres_per_output_pixel = abs(transform[1]) / scale_x
    bar_length = 20_000.0 / metres_per_output_pixel
    bar_x = output_width * 0.055
    bar_y = output_height * 0.935
    segment = bar_length / 4.0
    bar_h = max(14, round(output_width * 0.009))
    for index in range(4):
        fill = (8, 15, 18, 255) if index % 2 == 0 else (247, 243, 221, 255)
        draw.rectangle((bar_x + index * segment, bar_y, bar_x + (index + 1) * segment, bar_y + bar_h), fill=fill, outline=(8, 15, 18, 255), width=2)
    draw.text((bar_x, bar_y - 8), "0", anchor="ls", font=small_font, fill=ink, stroke_width=stroke, stroke_fill=halo)
    draw.text((bar_x + bar_length, bar_y - 8), "20 km", anchor="rs", font=small_font, fill=ink, stroke_width=stroke, stroke_fill=halo)

    compass_x, compass_y = output_width * 0.91, output_height * 0.115
    arm = output_width * 0.032
    compass_halo = max(8, round(output_width / 230))
    compass_ink = max(3, round(output_width / 620))
    draw.line((compass_x - arm, compass_y, compass_x + arm, compass_y), fill=halo, width=compass_halo)
    draw.line((compass_x, compass_y - arm, compass_x, compass_y + arm), fill=halo, width=compass_halo)
    draw.line((compass_x - arm, compass_y, compass_x + arm, compass_y), fill=ink, width=compass_ink)
    draw.line((compass_x, compass_y - arm, compass_x, compass_y + arm), fill=ink, width=compass_ink)
    draw.polygon([(compass_x, compass_y - arm * 1.30), (compass_x - arm * 0.24, compass_y - arm * 0.62), (compass_x + arm * 0.24, compass_y - arm * 0.62)], fill=ink)
    draw.text((compass_x, compass_y - arm * 1.62), "N", anchor="mm", font=label_font, fill=ink, stroke_width=stroke, stroke_fill=halo)
    draw.text((compass_x, compass_y + arm * 1.50), "S", anchor="mm", font=label_font, fill=ink, stroke_width=stroke, stroke_fill=halo)
    draw.text((compass_x - arm * 1.48, compass_y), "O", anchor="mm", font=label_font, fill=ink, stroke_width=stroke, stroke_fill=halo)
    draw.text((compass_x + arm * 1.48, compass_y), "E", anchor="mm", font=label_font, fill=ink, stroke_width=stroke, stroke_fill=halo)

    attribution_font = load_font(round(output_width * 0.010), False)
    draw.text(
        (output_width - 24, output_height - 20),
        attribution_text,
        anchor="rs",
        font=attribution_font,
        fill=ink,
        stroke_width=max(1, stroke - 1),
        stroke_fill=halo,
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(output, quality=98, subsampling=0, optimize=True)


def hillshade(values: np.ndarray, mask: np.ndarray, strength: float) -> np.ndarray:
    filled = values.copy()
    fill_value = float(np.nanmedian(filled[mask])) if np.any(mask) else 0.0
    filled[~mask] = fill_value
    gradient_y, gradient_x = np.gradient(filled)
    shade = 1.0 - strength * gradient_x + strength * 0.75 * gradient_y
    return np.clip(shade, 0.62, 1.28)


def srgb_to_linear(rgb: np.ndarray) -> np.ndarray:
    """Convert 0..255 sRGB values to the linear-light domain used by WebGL."""
    values = np.clip(rgb.astype(np.float32) / 255.0, 0.0, 1.0)
    return np.where(
        values <= 0.04045,
        values / 12.92,
        ((values + 0.055) / 1.055) ** 2.4,
    )


def linear_to_srgb(rgb: np.ndarray) -> np.ndarray:
    """Convert linear RGB values to 0..255 display-referred sRGB."""
    values = np.clip(rgb.astype(np.float32), 0.0, 1.0)
    encoded = np.where(
        values <= 0.0031308,
        values * 12.92,
        1.055 * np.power(values, 1.0 / 2.4) - 0.055,
    )
    return encoded * 255.0


def smooth_surface_for_normals(
    z: np.ndarray,
    pixel_size_m: float,
    sample_spacing_m: float,
) -> np.ndarray:
    """Low-pass only the lighting normals to match the WebGL heightfield mesh."""
    if pixel_size_m <= 0.0:
        raise ValueError("pixel_size_m must be positive")
    if sample_spacing_m <= pixel_size_m:
        return z.astype(np.float32, copy=True)
    factor = max(2, int(np.floor(sample_spacing_m / pixel_size_m + 0.5)))
    height, width = z.shape
    reduced = Image.fromarray(z.astype(np.float32), mode="F").resize(
        (max(2, width // factor), max(2, height // factor)),
        Image.Resampling.BOX,
    )
    return np.asarray(
        reduced.resize((width, height), Image.Resampling.BICUBIC),
        dtype=np.float32,
    )


def webgl_lit_colors(
    colors: np.ndarray,
    z: np.ndarray,
    *,
    pixel_size_m: float,
    vertical_exaggeration: float,
    view_bearing_deg: float,
    hemisphere_intensity: float = 1.7,
    key_light_intensity: float = 2.1,
    key_light_bearing_deg: float = 45.0,
    key_light_elevation_deg: float = 58.0,
    normal_sample_spacing_m: float = 2.0,
    exposure: float = DEFAULT_RELIEF_EXPOSURE,
    material_rgb: tuple[int, int, int] = WEBGL_MATERIAL_RGB,
    hemisphere_sky_rgb: tuple[int, int, int] = WEBGL_HEMISPHERE_SKY_RGB,
    hemisphere_ground_rgb: tuple[int, int, int] = WEBGL_HEMISPHERE_GROUND_RGB,
    key_light_rgb: tuple[int, int, int] = WEBGL_KEY_LIGHT_RGB,
) -> np.ndarray:
    """Approximate TerrainViewer's MeshStandardMaterial lighting in linear RGB.

    The static renderer keeps its cartographic texture and projection, but uses
    the same cool hemisphere / warm directional-light language as Three.js.
    Normals are derived from metric horizontal spacing and the displayed
    vertical exaggeration instead of arbitrary array-gradient coefficients.
    """
    if colors.shape[:2] != z.shape or colors.shape[-1] != 3:
        raise ValueError("colors and z must describe the same RGB surface")
    for value, name in (
        (vertical_exaggeration, "vertical_exaggeration"),
        (hemisphere_intensity, "hemisphere_intensity"),
        (key_light_intensity, "key_light_intensity"),
        (normal_sample_spacing_m, "normal_sample_spacing_m"),
        (exposure, "exposure"),
    ):
        if value <= 0.0:
            raise ValueError(f"{name} must be positive")
    if not 0.0 < key_light_elevation_deg < 90.0:
        raise ValueError("key_light_elevation_deg must be between 0 and 90 degrees")

    normal_z = smooth_surface_for_normals(
        z,
        pixel_size_m,
        normal_sample_spacing_m,
    )
    gradient_y, gradient_x = np.gradient(
        normal_z * vertical_exaggeration,
        pixel_size_m,
        pixel_size_m,
    )
    nx = -gradient_x
    ny = -gradient_y
    nz = np.ones_like(normal_z)
    norm = np.sqrt(nx * nx + ny * ny + nz * nz)
    nx, ny, nz = nx / norm, ny / norm, nz / norm

    # Rows point toward the selected bearing; columns point 90 degrees to its
    # left in geographic space. Rotate the fixed north-east WebGL key light
    # into these view-relative axes so every site azimuth stays coherent.
    bearing = np.deg2rad(float(view_bearing_deg) % 360.0)
    light_bearing = np.deg2rad(float(key_light_bearing_deg) % 360.0)
    elevation = np.deg2rad(key_light_elevation_deg)
    horizontal = np.cos(elevation)
    light_x = horizontal * np.cos(light_bearing - (bearing - np.pi / 2.0))
    light_y = horizontal * np.cos(light_bearing - bearing)
    light_z = np.sin(elevation)
    diffuse = np.clip(nx * light_x + ny * light_y + nz * light_z, 0.0, 1.0)

    sky = srgb_to_linear(np.asarray(hemisphere_sky_rgb, dtype=np.float32))
    ground = srgb_to_linear(np.asarray(hemisphere_ground_rgb, dtype=np.float32))
    key = srgb_to_linear(np.asarray(key_light_rgb, dtype=np.float32))
    material = srgb_to_linear(np.asarray(material_rgb, dtype=np.float32))
    sky_weight = np.clip(nz * 0.5 + 0.5, 0.0, 1.0)
    hemisphere = (
        ground[None, None, :] * (1.0 - sky_weight[:, :, None])
        + sky[None, None, :] * sky_weight[:, :, None]
    ) * hemisphere_intensity
    direct = key[None, None, :] * (
        key_light_intensity * diffuse[:, :, None]
    )
    irradiance = (hemisphere + direct) / np.pi

    texture = srgb_to_linear(colors)
    radiance = texture * material[None, None, :] * irradiance
    return linear_to_srgb(radiance * exposure)


def open_raster(path: Path, description: str = "raster"):
    dataset = gdal.Open(str(path))
    if dataset is None:
        raise RuntimeError(f"Cannot open {description} {path}")
    return dataset


def raster_bounds(dataset) -> tuple[float, float, float, float]:
    transform = dataset.GetGeoTransform()
    if abs(transform[2]) > 1e-10 or abs(transform[4]) > 1e-10:
        raise ValueError("Rotated raster grids are not supported")
    x1 = transform[0] + dataset.RasterXSize * transform[1]
    y1 = transform[3] + dataset.RasterYSize * transform[5]
    return min(transform[0], x1), min(transform[3], y1), max(transform[0], x1), max(transform[3], y1)


def warp_to_reference(
    path: Path,
    reference_path: Path,
    *,
    width: int | None = None,
    height: int | None = None,
    resample_alg: int = gdal.GRA_Cubic,
    ignore_nodata: bool = False,
):
    """Reproject and align a raster to the geographic footprint of a reference."""
    source = open_raster(path)
    reference = open_raster(reference_path, "reference raster")
    target_width = reference.RasterXSize if width is None else int(width)
    target_height = reference.RasterYSize if height is None else int(height)
    if target_width <= 0 or target_height <= 0:
        raise ValueError("Aligned raster dimensions must be positive")
    options = {
        "format": "MEM",
        "dstSRS": reference.GetProjection(),
        "outputBounds": raster_bounds(reference),
        "width": target_width,
        "height": target_height,
        "resampleAlg": resample_alg,
        "errorThreshold": 0.0,
    }
    if ignore_nodata:
        # IGN byte imagery declares 255 as nodata even though white is also a
        # legitimate pixel value. Treat all RGB bytes as data and initialise
        # any area outside the source footprint to white.
        options.update(
            srcNodata="None",
            dstNodata="None",
            warpOptions=["INIT_DEST=255"],
        )
    result = gdal.Warp("", source, **options)
    if result is None:
        raise RuntimeError(f"Could not align {path} to {reference_path}")
    return result


def load_depth(path: Path, max_depth: float) -> tuple[np.ndarray, np.ndarray, tuple]:
    dataset = open_raster(path, "depth raster")
    values = dataset.GetRasterBand(1).ReadAsArray().astype(np.float32)
    transform = dataset.GetGeoTransform()
    mask = np.isfinite(values) & (values > -1000) & (values >= 0) & (values <= 80)
    depth = np.where(mask, np.clip(values, 0, max_depth), np.nan)
    return depth, mask, transform


def default_view_bearing(rotation_k: int) -> float:
    """Bearing, in degrees clockwise from north, at the top of the 3D view."""
    return (180.0 + 90.0 * (rotation_k % 4)) % 360.0


def compass_point(
    center: tuple[float, float],
    frame_bearing_deg: float,
    cardinal_bearing_deg: float,
    distance: float,
) -> tuple[float, float]:
    """Project a geographic bearing into the image plane."""
    angle = np.deg2rad(cardinal_bearing_deg - frame_bearing_deg)
    return (
        center[0] + float(np.sin(angle)) * distance,
        center[1] - float(np.cos(angle)) * distance,
    )


def draw_compass_rose(
    draw: ImageDraw.ImageDraw,
    center: tuple[float, float],
    frame_bearing_deg: float,
    font: ImageFont.ImageFont,
    style: float,
) -> None:
    """Draw the static counterpart of the interactive geographic compass."""
    cx, cy = center
    radius = 64.0 * style
    background = (6, 28, 36, 189)
    border = (205, 244, 239, 133)
    cream = (245, 239, 218, 255)
    outline = (2, 4, 5, 252)
    border_width = max(1, int(np.floor(1.2 * style + 0.5)))
    outline_width = max(1, int(np.floor(5.0 * style + 0.5)))
    core_width = max(1, int(np.floor(2.0 * style + 0.5)))

    draw.ellipse(
        (cx - radius, cy - radius, cx + radius, cy + radius),
        fill=background,
        outline=border,
        width=border_width,
    )

    axis_radius = 28.0 * style
    cardinal_bearings = (0.0, 90.0, 180.0, 270.0)
    axis_points = {
        bearing: compass_point(center, frame_bearing_deg, bearing, axis_radius)
        for bearing in cardinal_bearings
    }
    for start, end in (
        (axis_points[0.0], axis_points[180.0]),
        (axis_points[90.0], axis_points[270.0]),
    ):
        draw.line((*start, *end), fill=outline, width=outline_width)
        draw.line((*start, *end), fill=cream, width=core_width)

    north_tip = compass_point(center, frame_bearing_deg, 0.0, 34.0 * style)
    north_left = compass_point(center, frame_bearing_deg, -13.0, 23.0 * style)
    north_right = compass_point(center, frame_bearing_deg, 13.0, 23.0 * style)
    draw.polygon(
        [north_tip, north_left, north_right],
        fill=cream,
        outline=outline,
        width=max(1, int(np.floor(2.0 * style + 0.5))),
    )

    text_stroke = max(1, int(np.floor(1.5 * style + 0.5)))
    for label, bearing in (("N", 0.0), ("E", 90.0), ("S", 180.0), ("O", 270.0)):
        draw.text(
            compass_point(center, frame_bearing_deg, bearing, 50.0 * style),
            label,
            font=font,
            anchor="mm",
            fill=cream,
            stroke_width=text_stroke,
            stroke_fill=outline,
        )


def rotate_surface_for_view(
    z: np.ndarray,
    colors: np.ndarray,
    valid: np.ndarray,
    land_mask: np.ndarray,
    coast_points: list[list[tuple[float, float]]],
    contour_points: dict[int, list[list[tuple[float, float]]]],
    angle_deg: float,
    deep_rgb: np.ndarray,
    clip_outside: bool = False,
) -> tuple[
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    list[list[tuple[float, float]]],
    dict[int, list[list[tuple[float, float]]]],
]:
    """Rotate a prepared surface so the requested bearing points down-frame."""
    angle_deg = ((angle_deg + 180.0) % 360.0) - 180.0
    if abs(angle_deg) < 1e-8:
        return z, colors, valid, land_mask, coast_points, contour_points

    source_h, source_w = z.shape
    z_image = Image.fromarray(z.astype(np.float32), mode="F")
    z_rotated = np.asarray(
        z_image.rotate(
            angle_deg,
            resample=Image.Resampling.BICUBIC,
            expand=True,
            fillcolor=float(np.nanmin(z)),
        ),
        dtype=np.float32,
    )
    output_h, output_w = z_rotated.shape

    color_image = Image.fromarray(np.clip(colors, 0, 255).astype(np.uint8), mode="RGB")
    color_rotated = np.asarray(
        color_image.rotate(
            angle_deg,
            resample=Image.Resampling.BICUBIC,
            expand=True,
            fillcolor=tuple(int(value) for value in deep_rgb),
        ),
        dtype=np.float32,
    )
    valid_rotated = np.asarray(
        Image.fromarray((valid > 0.5).astype(np.uint8) * 255, mode="L").rotate(
            angle_deg,
            resample=Image.Resampling.NEAREST,
            expand=True,
            fillcolor=0 if clip_outside else 255,
        )
    ) > 127
    land_rotated = np.asarray(
        Image.fromarray((land_mask > 0.5).astype(np.uint8) * 255, mode="L").rotate(
            angle_deg,
            # Keep the binary shoreline aligned with the smoothly rotated
            # vector coastline. Nearest-neighbour rotation leaves a staircase
            # mask that exposes shallow-water facets on the landward side.
            resample=Image.Resampling.BICUBIC,
            expand=True,
            fillcolor=0,
        )
    ) > 127

    radians = np.deg2rad(angle_deg)
    cosine = float(np.cos(radians))
    sine = float(np.sin(radians))
    source_cx = source_w / 2.0
    source_cy = source_h / 2.0
    output_cx = output_w / 2.0
    output_cy = output_h / 2.0

    def rotate_point(point: tuple[float, float]) -> tuple[float, float]:
        dx = point[0] - source_cx
        dy = point[1] - source_cy
        return (
            cosine * dx + sine * dy + output_cx,
            -sine * dx + cosine * dy + output_cy,
        )

    coast_rotated = [[rotate_point(point) for point in line] for line in coast_points]
    contours_rotated = {
        level: [[rotate_point(point) for point in line] for line in lines]
        for level, lines in contour_points.items()
    }
    return z_rotated, color_rotated, valid_rotated, land_rotated, coast_rotated, contours_rotated


def rotate_rgb_for_view(
    rgb: np.ndarray,
    angle_deg: float,
    fill_rgb: tuple[int, int, int],
) -> np.ndarray:
    """Rotate an RGB texture with the exact raster geometry used by the mesh."""
    angle_deg = ((angle_deg + 180.0) % 360.0) - 180.0
    if abs(angle_deg) < 1e-8:
        return rgb.copy()
    image = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), mode="RGB")
    return np.asarray(
        image.rotate(
            angle_deg,
            resample=Image.Resampling.BICUBIC,
            expand=True,
            fillcolor=fill_rgb,
        ),
        dtype=np.float32,
    )


def rotate_scalar_for_view(values: np.ndarray, angle_deg: float) -> np.ndarray:
    """Rotate a scalar texture mask with the mesh's expanded geometry."""
    angle_deg = ((angle_deg + 180.0) % 360.0) - 180.0
    if abs(angle_deg) < 1e-8:
        return values.copy()
    return np.asarray(
        Image.fromarray(values.astype(np.float32), mode="F").rotate(
            angle_deg,
            resample=Image.Resampling.BICUBIC,
            expand=True,
            fillcolor=0.0,
        ),
        dtype=np.float32,
    )


def load_topography(path: Path, reference_path: Path) -> np.ndarray:
    dataset = warp_to_reference(path, reference_path)
    band = dataset.GetRasterBand(1)
    arr = band.ReadAsArray().astype(np.float32)
    nodata = band.GetNoDataValue()
    if nodata is not None:
        arr = np.where(arr == nodata, np.nan, arr)
    # Cubic WMS resampling can turn -99999 nodata cells into nearby large
    # negative values. Those cells are not elevations.
    arr = np.where(arr < -1000, np.nan, arr)
    return arr


def load_rgb_raster(
    path: Path,
    reference_path: Path,
    *,
    width: int | None = None,
    height: int | None = None,
) -> np.ndarray:
    dataset = warp_to_reference(
        path,
        reference_path,
        width=width,
        height=height,
        ignore_nodata=True,
    )
    bands = min(dataset.RasterCount, 3)
    if bands < 1:
        raise ValueError(f"RGB raster has no bands: {path}")
    values = [
        dataset.GetRasterBand(index).ReadAsArray()
        for index in range(1, bands + 1)
    ]
    if bands == 1:
        values *= 3
    return np.stack(values[:3], axis=-1).astype(np.float32)


def resize_rgb(rgb: np.ndarray, width: int, height: int) -> np.ndarray:
    """Resize an RGB texture without quantizing its geometry arrays."""
    if width <= 0 or height <= 0:
        raise ValueError("RGB target dimensions must be positive")
    if rgb.shape[:2] == (height, width):
        return rgb.astype(np.float32, copy=True)
    image = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), mode="RGB")
    return np.asarray(
        image.resize((width, height), Image.Resampling.LANCZOS),
        dtype=np.float32,
    )


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


def smooth_depth_mask(depth: np.ndarray, smoothing_m: float, pixel_m: float) -> np.ndarray:
    """Low-pass a depth field for a clean thematic boundary, not for relief."""
    if smoothing_m <= 0.0 or pixel_m <= 0.0:
        return depth
    factor = max(2, int(np.floor(smoothing_m / pixel_m + 0.5)))
    height, width = depth.shape
    reduced = Image.fromarray(depth.astype(np.float32), mode="F").resize(
        (max(1, width // factor), max(1, height // factor)),
        Image.Resampling.BOX,
    )
    return np.asarray(reduced.resize((width, height), Image.Resampling.BICUBIC), dtype=np.float32)


def imagery_depth_alpha(
    depth: np.ndarray,
    legacy_limit_m: float | None,
    legacy_feather_m: float,
    full_depth_m: float | None,
    max_depth_m: float | None,
) -> np.ndarray | None:
    """Return a smooth alpha that is opaque shallow and transparent deep."""
    if full_depth_m is not None or max_depth_m is not None:
        if full_depth_m is None or max_depth_m is None:
            raise ValueError("imagery_sea_full_depth_m and imagery_sea_max_depth_m must be set together")
        if max_depth_m <= full_depth_m:
            raise ValueError("imagery_sea_max_depth_m must be greater than imagery_sea_full_depth_m")
        alpha = np.clip((max_depth_m - depth) / (max_depth_m - full_depth_m), 0.0, 1.0)
    elif legacy_limit_m is not None:
        if legacy_feather_m <= 0.0:
            raise ValueError("imagery_sea_feather_m must be positive")
        alpha = np.clip((legacy_limit_m - depth) / legacy_feather_m, 0.0, 1.0)
    else:
        return None
    return alpha * alpha * (3.0 - 2.0 * alpha)


def imagery_alpha_across_shore(
    land_mask: np.ndarray,
    sea_alpha: np.ndarray,
) -> np.ndarray:
    """Keep imagery opaque on land while the depth mask remains authoritative at sea."""
    if land_mask.shape != sea_alpha.shape:
        raise ValueError("Land mask and sea imagery alpha must share the same shape")
    return np.where(
        land_mask,
        1.0,
        np.clip(sea_alpha, 0.0, 1.0),
    ).astype(np.float32)


def blend_texture(
    base_rgb: np.ndarray,
    texture_rgb: np.ndarray,
    alpha: np.ndarray,
) -> np.ndarray:
    """Composite a texture exactly once with a scalar alpha mask."""
    return (
        base_rgb * (1.0 - alpha[:, :, None])
        + texture_rgb * alpha[:, :, None]
    )


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


def apply_bridge_decks(
    surface: np.ndarray,
    source_transform: tuple,
    source_width: int,
    source_height: int,
    rotation_k: int,
    sample_step: int,
    bridges: list[dict] | None,
) -> np.ndarray:
    """Replace terrain below bridge decks with narrow interpolated surfaces."""
    if not bridges:
        return surface

    inverse = gdal.InvGeoTransform(source_transform)
    if inverse is None:
        raise ValueError("Could not invert the source raster geotransform")

    def oriented_pixel(easting: float, northing: float) -> tuple[float, float]:
        x = inverse[0] + inverse[1] * easting + inverse[2] * northing
        y = inverse[3] + inverse[4] * easting + inverse[5] * northing
        k = rotation_k % 4
        if k == 1:
            x, y = y, source_width - 1 - x
        elif k == 2:
            x, y = source_width - 1 - x, source_height - 1 - y
        elif k == 3:
            x, y = source_height - 1 - y, x
        return x / sample_step, y / sample_step

    pixel_m = abs(source_transform[1]) * sample_step
    yy, xx = np.indices(surface.shape, dtype=np.float32)
    corrected = surface.copy()
    for bridge in bridges:
        start = bridge["start_utm40s"]
        end = bridge["end_utm40s"]
        x0, y0 = oriented_pixel(float(start[0]), float(start[1]))
        x1, y1 = oriented_pixel(float(end[0]), float(end[1]))
        vx, vy = x1 - x0, y1 - y0
        length2 = vx * vx + vy * vy
        if length2 <= 0:
            raise ValueError("Bridge deck endpoints must be distinct")

        t = np.clip(((xx - x0) * vx + (yy - y0) * vy) / length2, 0.0, 1.0)
        nearest_x = x0 + t * vx
        nearest_y = y0 + t * vy
        distance_m = np.hypot(xx - nearest_x, yy - nearest_y) * pixel_m
        inner = float(bridge.get("half_width_m", 5.0))
        feather = float(bridge.get("feather_m", 2.0))
        if inner <= 0.0 or feather <= 0.0:
            raise ValueError("Bridge deck width and feather must be positive")

        ix0 = int(np.clip(round(x0), 0, corrected.shape[1] - 1))
        iy0 = int(np.clip(round(y0), 0, corrected.shape[0] - 1))
        ix1 = int(np.clip(round(x1), 0, corrected.shape[1] - 1))
        iy1 = int(np.clip(round(y1), 0, corrected.shape[0] - 1))
        z0 = float(corrected[iy0, ix0])
        z1 = float(corrected[iy1, ix1])
        deck = z0 + t * (z1 - z0)

        weight = np.clip((inner + feather - distance_m) / feather, 0.0, 1.0)
        weight = weight * weight * (3.0 - 2.0 * weight)
        corrected = corrected * (1.0 - weight) + deck * weight
    return corrected


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


def draw_interpolated_triangle(
    canvas: Image.Image,
    points: list[tuple[float, float]],
    colors: np.ndarray,
) -> None:
    """Rasterize one orthographic triangle with barycentric RGB interpolation."""
    if len(points) != 3 or colors.shape != (3, 3):
        raise ValueError("A textured triangle needs three points and three RGB colors")
    xs = np.asarray([point[0] for point in points], dtype=np.float32)
    ys = np.asarray([point[1] for point in points], dtype=np.float32)
    x0 = max(0, int(np.floor(float(np.min(xs)))))
    y0 = max(0, int(np.floor(float(np.min(ys)))))
    x1 = min(canvas.width, int(np.ceil(float(np.max(xs)))) + 1)
    y1 = min(canvas.height, int(np.ceil(float(np.max(ys)))) + 1)
    if x1 <= x0 or y1 <= y0:
        return
    denominator = (
        (ys[1] - ys[2]) * (xs[0] - xs[2])
        + (xs[2] - xs[1]) * (ys[0] - ys[2])
    )
    if abs(float(denominator)) < 1e-8:
        return
    sample_x, sample_y = np.meshgrid(
        np.arange(x0, x1, dtype=np.float32) + 0.5,
        np.arange(y0, y1, dtype=np.float32) + 0.5,
    )
    weight0 = (
        (ys[1] - ys[2]) * (sample_x - xs[2])
        + (xs[2] - xs[1]) * (sample_y - ys[2])
    ) / denominator
    weight1 = (
        (ys[2] - ys[0]) * (sample_x - xs[2])
        + (xs[0] - xs[2]) * (sample_y - ys[2])
    ) / denominator
    weight2 = 1.0 - weight0 - weight1
    inside = (weight0 >= -1e-5) & (weight1 >= -1e-5) & (weight2 >= -1e-5)
    if not np.any(inside):
        return
    interpolated = (
        weight0[:, :, None] * colors[0]
        + weight1[:, :, None] * colors[1]
        + weight2[:, :, None] * colors[2]
    )
    patch = Image.fromarray(
        np.clip(interpolated, 0, 255).astype(np.uint8),
        mode="RGB",
    )
    mask = Image.fromarray(inside.astype(np.uint8) * 255, mode="L")
    canvas.paste(patch, (x0, y0), mask)


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


def strict_land_imagery_mask(land_mask: np.ndarray, inset_pixels: int = 2) -> np.ndarray:
    """Inset land imagery so a smoothed coastline can never expose it at sea."""
    if inset_pixels <= 0:
        return land_mask.copy()
    return land_mask & (distance_from(~land_mask, inset_pixels) >= inset_pixels)


def interpolate_coast_polygon(elev: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Build a continuous land polygon from the terrestrial DEM's 0 m contour."""
    h, w = elev.shape
    coast_y = np.full(w, np.nan, dtype=np.float32)
    stable_kernel = np.ones(9, dtype=np.int16)

    # In the simple profile mode, the sea is north (top) and the connected land
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


def sieve_land_components(raw_land: np.ndarray, threshold_px: int) -> np.ndarray:
    """Remove small land components without ever turning water into land."""
    height, width = raw_land.shape
    source = gdal.GetDriverByName("MEM").Create("", width, height, 1, gdal.GDT_Byte)
    target = gdal.GetDriverByName("MEM").Create("", width, height, 1, gdal.GDT_Byte)
    source.GetRasterBand(1).WriteArray(raw_land.astype(np.uint8))
    gdal.SieveFilter(source.GetRasterBand(1), None, target.GetRasterBand(1), threshold_px, 8)
    # SieveFilter acts on every raster class. Preserve every original water
    # cell so removing small land components can never fill pools or channels.
    return target.GetRasterBand(1).ReadAsArray().astype(bool) & raw_land


def interpolate_coast_mask(elev: np.ndarray, sieve_threshold_px: int = 200) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Build a two-dimensional coast mask for bays, pool walls and islets."""
    raw_land = np.isfinite(elev) & (elev >= 0.0)
    sieved_land = sieve_land_components(raw_land, sieve_threshold_px)

    # Use one continuous, sub-pixel coastline for both the terrestrial fill
    # and its vector outline. Keeping the fill strictly inside the 0.5 contour
    # prevents square DEM cells from protruding beyond the smoothed line.
    smoothed_land = np.asarray(
        Image.fromarray(sieved_land.astype(np.uint8) * 255, "L").filter(
            ImageFilter.GaussianBlur(radius=10.0)
        ),
        dtype=np.float32,
    ) / 255.0
    land_mask = smoothed_land >= 0.5
    land_weight = smoothed_land * smoothed_land * (3.0 - 2.0 * smoothed_land)

    coast_y = np.full(land_mask.shape[1], np.nan, dtype=np.float32)
    for x in range(land_mask.shape[1]):
        candidates = np.flatnonzero(land_mask[:, x])
        if len(candidates):
            y = int(candidates[-1])
            while y > 0 and land_mask[y - 1, x]:
                y -= 1
            coast_y[x] = float(y)
    known = np.isfinite(coast_y)
    coast_y = np.interp(np.arange(len(coast_y)), np.flatnonzero(known), coast_y[known]).astype(np.float32)
    return coast_y, land_mask, land_weight


def extract_coastlines(land_surface: np.ndarray) -> list[list[tuple[float, float]]]:
    """Extract all meaningful smoothed boundaries from a filtered land mask."""
    h, w = land_surface.shape
    nodata = -9999.0
    raster = gdal.GetDriverByName("MEM").Create("", w, h, 1, gdal.GDT_Float32)
    raster.SetGeoTransform((0, 1, 0, 0, 0, 1))
    band = raster.GetRasterBand(1)
    band.WriteArray(land_surface.astype(np.float32))
    band.SetNoDataValue(nodata)
    vectors = ogr.GetDriverByName("MEM").CreateDataSource("")
    layer = vectors.CreateLayer("coast", geom_type=ogr.wkbLineString)
    gdal.ContourGenerateEx(band, layer, ["FIXED_LEVELS=0.5", f"NODATA={nodata}"])

    coastlines: list[list[tuple[float, float]]] = []
    for feature in layer:
        geometry = feature.GetGeometryRef()
        parts = [geometry.GetGeometryRef(i) for i in range(geometry.GetGeometryCount())] if geometry.GetGeometryCount() else [geometry]
        for part in parts:
            # The raster surface has already been Gaussian-interpolated.
            # Preserve its 0.5 contour exactly: another geometric smoothing
            # pass would move the line away from the fill it is meant to bound.
            points = [(part.GetX(i), part.GetY(i)) for i in range(part.GetPointCount())]
            if len(points) < 7:
                continue
            length = float(np.linalg.norm(np.diff(np.asarray(points), axis=0), axis=1).sum())
            if length >= 35.0:
                coastlines.append(points)
    return coastlines


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
    padded = np.pad(np.where(sea_mask, out, np.nan), 2, mode="constant", constant_values=np.nan)
    median = np.empty_like(out)
    # A full sliding-window median can expose billions of logical values on a
    # context raster. Row blocks preserve the exact result while bounding peak
    # memory independently of site size.
    block_rows = 256
    for start in range(0, out.shape[0], block_rows):
        stop = min(out.shape[0], start + block_rows)
        windows = np.lib.stride_tricks.sliding_window_view(
            padded[start : stop + 4],
            (5, 5),
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
            median[start:stop] = np.nanmedian(windows, axis=(-2, -1))
    out = np.where(sea_mask, median, out)

    for _ in range(passes):
        padded = np.pad(out, 1, mode="edge")
        mask_padded = np.pad(sea_mask, 1, mode="constant", constant_values=False)
        total = np.zeros_like(out)
        weight = np.zeros_like(out)
        neighbors = (
            (padded[:-2, 1:-1], mask_padded[:-2, 1:-1]),
            (padded[2:, 1:-1], mask_padded[2:, 1:-1]),
            (padded[1:-1, :-2], mask_padded[1:-1, :-2]),
            (padded[1:-1, 2:], mask_padded[1:-1, 2:]),
        )
        for neighbor, neighbor_valid in neighbors:
            delta = neighbor - out
            local_weight = np.exp(-((delta / 2.2) ** 2)) * neighbor_valid
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
    ui_scale: float = 1.0,
) -> tuple[float, float] | None:
    best: tuple[float, float] | None = None
    best_score = -np.inf
    for line in lines:
        if len(line) < 5:
            continue
        stride = max(1, len(line) // 120)
        for index in range(2, len(line) - 2, stride):
            x, y = line[index]
            if not (45 * ui_scale < x < width - 95 * ui_scale and 25 * ui_scale < y < height - 30 * ui_scale):
                continue
            dx = line[index + 2][0] - line[index - 2][0]
            dy = line[index + 2][1] - line[index - 2][1]
            horizontal = abs(dx) / (abs(dx) + abs(dy) + 1e-6)
            coast_gap = max(0.0, float(coast_y[int(np.clip(round(x), 0, width - 1))]) - y)
            edge_gap = min(x - 45 * ui_scale, width - 95 * ui_scale - x, y - 25 * ui_scale, height - 30 * ui_scale - y)
            separation = min((np.hypot(x - ox, y - oy) for ox, oy in occupied), default=200.0 * ui_scale)
            focus_penalty = 0.35 * abs(x - width * 0.64)
            score = edge_gap + 0.55 * coast_gap + 35.0 * ui_scale * horizontal + min(separation, 120.0 * ui_scale) - focus_penalty
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


def expanded_bbox(
    bbox: tuple[float, float, float, float],
    padding: float,
) -> tuple[float, float, float, float]:
    left, top, right, bottom = bbox
    return left - padding, top - padding, right + padding, bottom + padding


def bboxes_intersect(
    first: tuple[float, float, float, float],
    second: tuple[float, float, float, float],
) -> bool:
    return not (
        first[2] <= second[0]
        or second[2] <= first[0]
        or first[3] <= second[1]
        or second[3] <= first[1]
    )


def segment_intersects_bbox(
    start: tuple[float, float],
    end: tuple[float, float],
    bbox: tuple[float, float, float, float],
) -> bool:
    """Return whether a segment crosses an axis-aligned rectangle."""
    left, top, right, bottom = bbox
    x0, y0 = start
    x1, y1 = end
    dx = x1 - x0
    dy = y1 - y0
    t_min = 0.0
    t_max = 1.0
    for origin, delta, low, high in (
        (x0, dx, left, right),
        (y0, dy, top, bottom),
    ):
        if abs(delta) < 1e-12:
            if origin < low or origin > high:
                return False
            continue
        t0 = (low - origin) / delta
        t1 = (high - origin) / delta
        if t0 > t1:
            t0, t1 = t1, t0
        t_min = max(t_min, t0)
        t_max = min(t_max, t1)
        if t_min > t_max:
            return False
    return True


def polyline_intersects_bbox(
    line: list[tuple[float, float]],
    bbox: tuple[float, float, float, float],
) -> bool:
    return any(
        segment_intersects_bbox(start, end, bbox)
        for start, end in zip(line, line[1:])
    )


def clip_polyline_to_bbox(
    line: list[tuple[float, float]],
    bbox: tuple[float, float, float, float],
) -> list[list[tuple[float, float]]]:
    """Clip a polyline to an axis-aligned data footprint."""
    if len(line) < 2:
        return []
    left, top, right, bottom = bbox
    clipped_lines: list[list[tuple[float, float]]] = []
    current: list[tuple[float, float]] = []

    for start, end in zip(line, line[1:]):
        x0, y0 = start
        dx = end[0] - x0
        dy = end[1] - y0
        t_min = 0.0
        t_max = 1.0
        accepted = True
        for origin, delta, low, high in (
            (x0, dx, left, right),
            (y0, dy, top, bottom),
        ):
            if abs(delta) < 1e-12:
                if origin < low or origin > high:
                    accepted = False
                    break
                continue
            t0 = (low - origin) / delta
            t1 = (high - origin) / delta
            if t0 > t1:
                t0, t1 = t1, t0
            t_min = max(t_min, t0)
            t_max = min(t_max, t1)
            if t_min > t_max:
                accepted = False
                break

        if not accepted:
            if len(current) >= 2:
                clipped_lines.append(current)
            current = []
            continue

        clipped_start = (x0 + t_min * dx, y0 + t_min * dy)
        clipped_end = (x0 + t_max * dx, y0 + t_max * dy)
        if current and np.hypot(
            current[-1][0] - clipped_start[0],
            current[-1][1] - clipped_start[1],
        ) < 1e-6:
            current.append(clipped_end)
        else:
            if len(current) >= 2:
                clipped_lines.append(current)
            current = [clipped_start, clipped_end]

    if len(current) >= 2:
        clipped_lines.append(current)
    return clipped_lines


def clip_polylines_to_bbox(
    lines: list[list[tuple[float, float]]],
    bbox: tuple[float, float, float, float],
) -> list[list[tuple[float, float]]]:
    return [
        clipped
        for line in lines
        for clipped in clip_polyline_to_bbox(line, bbox)
    ]


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


@lru_cache(maxsize=2)
def build_fused_surface(
    depth_path: Path,
    elevation_path: Path,
    max_depth: float,
    rotation_k: int = 0,
    coast_mode: str = "profile",
    land_sieve_threshold_px: int = 200,
) -> tuple[
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    dict[int, list[list[tuple[float, float]]]],
    list[list[tuple[float, float]]],
]:
    """Create the single continuous terrain model used by every renderer."""
    contour_ceiling = max_depth + 12.0
    source_depth, bathy_mask, _ = load_depth(depth_path, contour_ceiling)
    elev = load_topography(elevation_path, depth_path)
    rotation_k %= 4
    if rotation_k:
        source_depth = np.rot90(source_depth, rotation_k).copy()
        bathy_mask = np.rot90(bathy_mask, rotation_k).copy()
        elev = np.rot90(elev, rotation_k).copy()
    if coast_mode == "profile":
        coast_y, land_mask, land_weight = interpolate_coast_polygon(elev)
        coastlines = [[(float(x), float(y)) for x, y in enumerate(coast_y)]]
    elif coast_mode == "mask":
        coast_y, land_mask, land_weight = interpolate_coast_mask(elev, land_sieve_threshold_px)
        coastlines = extract_coastlines(land_weight)
    else:
        raise ValueError("coast_mode must be 'profile' or 'mask'")
    fused_depth, sea_mask = fuse_bathymetry(source_depth, bathy_mask, elev, land_mask, contour_ceiling)
    fused_depth = edge_preserving_bathy(fused_depth, sea_mask)
    if coast_mode == "profile":
        signed_coast_distance = np.arange(fused_depth.shape[0], dtype=np.float32)[:, None] - coast_y[None, :]
        sea_ramp = np.clip(-signed_coast_distance / 14.0, 0.0, 1.0)
    else:
        sea_ramp = np.clip(distance_from(land_mask, 14) / 14.0, 0.0, 1.0)
    sea_ramp = sea_ramp * sea_ramp * (3.0 - 2.0 * sea_ramp)
    fused_depth = np.where(sea_mask, fused_depth * sea_ramp, fused_depth)
    contour_levels = tuple(range(5, int(max_depth // 5) * 5 + 1, 5))
    contours = extract_isobaths(fused_depth, sea_mask, levels=contour_levels)
    surface_valid = land_mask | sea_mask
    return elev, coast_y, land_mask, land_weight, surface_valid, fused_depth, contours, coastlines



def make_clean_plan(
    depth_path: Path,
    elevation_path: Path,
    output: Path,
    max_depth: float = 20,
    rotation_k: int = 0,
    coast_mode: str = "profile",
    output_scale: float = 1.0,
    land_imagery_path: Path | None = None,
    copyright_text: str | None = None,
    source_text: str | None = None,
    open_label_offsets_px: dict[str, list[float]] | None = None,
    final_output_size_px: tuple[int, int] | list[int] | None = None,
    land_sieve_threshold_px: int = 200,
    imagery_sea_depth_m: float | None = None,
    imagery_sea_feather_m: float = 0.6,
    imagery_sea_smoothing_m: float = 0.0,
    imagery_sea_full_depth_m: float | None = None,
    imagery_sea_max_depth_m: float | None = None,
    coastline_visible: bool = True,
    final_style_scale: float = 2.0,
    max_land_elevation_m: float = 55.0,
) -> None:
    if output_scale <= 0.0:
        raise ValueError("output_scale must be positive")
    if final_style_scale <= 0.0:
        raise ValueError("final_style_scale must be positive")
    if max_land_elevation_m <= 0.0:
        raise ValueError("max_land_elevation_m must be positive")
    ui = output_scale
    elev, coast_y, land_mask, land_weight, surface_valid, fused_depth, contours, coastlines = build_fused_surface(
        depth_path, elevation_path, max_depth, rotation_k, coast_mode, land_sieve_threshold_px
    )
    d = np.clip(fused_depth, 0.0, max_depth)
    sea_mask = surface_valid & ~land_mask
    valid = surface_valid
    land_blend = np.where(land_mask, land_weight, 0.0)
    deep_edge_nodata = deep_edge_nodata_display_mask(
        fused_depth,
        valid,
        land_mask,
        max_depth,
    )
    invalid_fraction = float(np.count_nonzero(~valid) / valid.size)
    if invalid_fraction > 0.001:
        deep_edge_fraction = float(np.count_nonzero(deep_edge_nodata) / valid.size)
        warning = (
            f"{invalid_fraction:.1%} of the 2D footprint has neither bathymetry nor elevation"
        )
        if deep_edge_fraction > 0.0:
            warning += (
                f"; {deep_edge_fraction:.1%} is a deep offshore edge gap shown with the "
                "maximum-depth colour while remaining excluded from contours and terrain"
            )
        else:
            warning += "; those cells are rendered as no-data"
        warnings.warn(warning, stacklevel=2)

    sea_rgb = palette(np.nan_to_num(d, nan=max_depth), max_depth=max_depth).astype(np.float32)
    sea_rgb = np.clip(sea_rgb * hillshade(np.nan_to_num(d, nan=max_depth), sea_mask, 0.035)[:, :, None], 0, 255)
    land_color_z = soften_surface(
        np.clip(np.nan_to_num(elev, nan=0.0), 0, max_land_elevation_m),
        land_mask,
        passes=2,
    )
    land_rgb = land_palette(land_color_z).astype(np.float32)

    rgb = np.broadcast_to(NO_DATA_RGB, (*d.shape, 3)).copy()
    rgb[sea_mask] = sea_rgb[sea_mask]
    rgb = rgb * (1 - land_blend[:, :, None]) + land_rgb * land_blend[:, :, None]
    rgb[~valid] = NO_DATA_RGB
    rgb[deep_edge_nodata] = palette(
        np.asarray(max_depth, dtype=np.float32),
        max_depth=max_depth,
    )

    img = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB")
    if ui != 1.0:
        img = img.resize(
            (int(np.floor(img.width * ui + 0.5)), int(np.floor(img.height * ui + 0.5))),
            Image.Resampling.LANCZOS,
        )
    img = img.convert("RGBA")
    if land_imagery_path is not None:
        source_dataset = open_raster(depth_path, "depth raster")
        target_width = int(np.floor(source_dataset.RasterXSize * ui + 0.5))
        target_height = int(np.floor(source_dataset.RasterYSize * ui + 0.5))
        orthophoto_array = load_rgb_raster(
            land_imagery_path,
            depth_path,
            width=target_width,
            height=target_height,
        )
        if rotation_k % 4:
            orthophoto_array = np.rot90(orthophoto_array, rotation_k).copy()
        orthophoto = Image.fromarray(np.clip(orthophoto_array, 0, 255).astype(np.uint8), "RGB")
        if orthophoto.size != img.size:
            orthophoto = orthophoto.resize(img.size, Image.Resampling.LANCZOS)
        # Fade in strictly from the terrestrial side of the interpolated 0 m
        # coastline. The binary mask prevents any orthophoto pixel from
        # altering the bathymetric sea rendering.
        land_alpha = np.where(land_mask, np.clip((land_weight - 0.5) * 2.0, 0.0, 1.0), 0.0)
        imagery_alpha = land_alpha
        if imagery_sea_depth_m is not None or imagery_sea_full_depth_m is not None or imagery_sea_max_depth_m is not None:
            depth_dataset = gdal.Open(str(depth_path))
            pixel_m = abs(depth_dataset.GetGeoTransform()[1]) if depth_dataset is not None else 1.0
            imagery_depth = smooth_depth_mask(d, imagery_sea_smoothing_m, pixel_m)
            sea_alpha = imagery_depth_alpha(
                imagery_depth,
                imagery_sea_depth_m,
                imagery_sea_feather_m,
                imagery_sea_full_depth_m,
                imagery_sea_max_depth_m,
            )
            assert sea_alpha is not None
            # The depth alpha is the sole authority offshore. This preserves a
            # continuous shallow-water texture without leaking imagery below
            # the configured maximum depth on steep coasts.
            imagery_alpha = imagery_alpha_across_shore(land_mask, sea_alpha)
        imagery_alpha = np.where(valid, imagery_alpha, 0.0)
        alpha = Image.fromarray(np.uint8(np.clip(imagery_alpha * 255.0, 0, 255)), "L").resize(img.size, Image.Resampling.LANCZOS)
        if imagery_sea_depth_m is None and imagery_sea_full_depth_m is None and imagery_sea_max_depth_m is None:
            strict_land_mask = strict_land_imagery_mask(land_mask)
            strict_land = Image.fromarray(np.uint8(strict_land_mask) * 255, "L").resize(img.size, Image.Resampling.NEAREST)
            alpha = Image.fromarray(np.minimum(np.asarray(alpha), np.asarray(strict_land)).astype(np.uint8), "L")
        img = Image.composite(orthophoto.convert("RGBA"), img, alpha)
    if final_output_size_px is None:
        final_resize_scale = 1.0
    else:
        final_width, final_height = map(int, final_output_size_px)
        final_resize_scale = np.sqrt((final_width / img.width) * (final_height / img.height))
    style = final_style_scale / final_resize_scale
    draw = ImageDraw.Draw(img, "RGBA")

    scaled_contours = {
        level: [[(x * ui, y * ui) for x, y in line] for line in lines]
        for level, lines in contours.items()
    }
    if coast_mode == "profile":
        coast_y_scaled = np.interp(
            np.arange(img.width, dtype=np.float32) / ui,
            np.arange(len(coast_y), dtype=np.float32),
            coast_y,
        ) * ui
    else:
        # A 2D coastline can cross a column several times, so the profile-only
        # coast-distance heuristic is deliberately disabled for label scoring.
        coast_y_scaled = np.zeros(img.width, dtype=np.float32)

    label_font = load_font(int(np.floor(18 * style + 0.5)), True)
    label_draws: list[tuple[float, float, int]] = []
    occupied_labels: list[tuple[float, float]] = []
    open_label_offsets_px = open_label_offsets_px or {}

    # Draw every depth line first. Labels are collected below and painted only
    # after all isobaths and the coastline, so no vector line can cross text.
    for level, lines in scaled_contours.items():
        for line in lines:
            draw.line(line, fill=(242, 245, 230, 150), width=max(1, int(np.floor(4 * style + 0.5))), joint="curve")
            draw.line(line, fill=(10, 15, 22, 205), width=max(1, int(np.floor(2 * style + 0.5))), joint="curve")

    if coast_mode == "profile":
        scaled_coastlines = [[(float(x), float(y)) for x, y in enumerate(coast_y_scaled)]]
    else:
        scaled_coastlines = [[(x * ui, y * ui) for x, y in line] for line in coastlines]
    if coastline_visible:
        for coast_line in scaled_coastlines:
            draw.line(coast_line, fill=(238, 230, 194, 210), width=max(1, int(np.floor(5 * style + 0.5))), joint="curve")
            draw.line(coast_line, fill=(12, 12, 10, 245), width=max(1, int(np.floor(3 * style + 0.5))), joint="curve")

    for level, lines in scaled_contours.items():
        open_lines = []
        for line in lines:
            center = isolated_contour_center(line, min_width=55.0 * ui, min_height=28.0 * ui)
            is_closed = len(line) >= 2 and np.linalg.norm(np.asarray(line[0]) - np.asarray(line[-1])) < 4.0 * ui
            if is_closed:
                if center and all(np.hypot(center[0] - x, center[1] - y) > 70 * style for x, y in occupied_labels):
                    x, y = center
                    occupied_labels.append(center)
                    label_draws.append((x - 24 * style, y - 11 * style, level))
                continue
            open_lines.append(line)

        label_point = choose_plan_label(open_lines, coast_y_scaled, img.width, img.height, occupied_labels, ui_scale=style)
        if label_point:
            x, y = label_point
            offset = open_label_offsets_px.get(str(level), (0.0, 0.0))
            x += float(offset[0]) * style
            y += float(offset[1]) * style
            occupied_labels.append((x, y))
            label_draws.append((x + 5 * style, y - 11 * style, level))

    for x, y, level in label_draws:
        draw.text(
            (x, y),
            f"-{level} m",
            font=label_font,
            fill=(5, 8, 15, 235),
            stroke_width=max(1, int(np.floor(2 * style + 0.5))),
            stroke_fill=(245, 244, 222, 230),
        )

    # North-up orientation and a scale based on the raster geotransform.
    annotation_font = load_font(int(np.floor(19 * style + 0.5)), True)
    pixel_m = abs(gdal.Open(str(depth_path)).GetGeoTransform()[1])
    bar_px = 50.0 / pixel_m * ui
    sx, sy = 48 * style, img.height - 48 * style
    draw.line((sx, sy, sx + bar_px, sy), fill=(244, 241, 218, 240), width=max(1, int(np.floor(7 * style + 0.5))))
    draw.line((sx, sy, sx + bar_px, sy), fill=(8, 10, 12, 250), width=max(1, int(np.floor(3 * style + 0.5))))
    draw.line((sx, sy - 8 * style, sx, sy + 8 * style), fill=(8, 10, 12, 250), width=max(1, int(np.floor(3 * style + 0.5))))
    draw.line((sx + bar_px, sy - 8 * style, sx + bar_px, sy + 8 * style), fill=(8, 10, 12, 250), width=max(1, int(np.floor(3 * style + 0.5))))
    draw.text((sx + bar_px / 2 - 22 * style, sy - 31 * style), "50 m", font=annotation_font, fill=(8, 10, 12, 250), stroke_width=max(1, int(np.floor(2 * style + 0.5))), stroke_fill=(244, 241, 218, 235))

    draw_compass_rose(
        draw,
        (76.0 * style, 76.0 * style),
        90.0 * (rotation_k % 4),
        annotation_font,
        style,
    )
    if copyright_text:
        copyright_font = load_font(int(np.floor(13 * style + 0.5)), True)
        draw.text(
            (img.width - 16 * style, img.height - 12 * style),
            copyright_text,
            anchor="rb",
            font=copyright_font,
            fill=(245, 239, 218, 235),
            stroke_width=max(1, int(np.floor(2 * style + 0.5))),
            stroke_fill=(5, 9, 13, 225),
        )
    if source_text:
        source_font = load_font(int(np.floor(10 * style + 0.5)), False)
        draw.text(
            (16 * style, img.height - 12 * style),
            source_text,
            anchor="lb",
            font=source_font,
            fill=(245, 239, 218, 225),
            stroke_width=max(1, int(np.floor(1.5 * style + 0.5))),
            stroke_fill=(5, 9, 13, 215),
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    rendered = img.convert("RGB")
    if final_output_size_px is not None:
        rendered = resize_exact_without_distortion(rendered, final_output_size_px)
    rendered.save(output, quality=98, subsampling=0, optimize=True)



def make_pretty_3d_from_offshore(
    depth_path: Path,
    elevation_path: Path,
    output: Path,
    title: str,
    max_depth: float = 20,
    decorate: bool = True,
    rotation_k: int = 0,
    coast_mode: str = "profile",
    view_bearing_deg: float | None = None,
    view_crop_width_m: float | None = None,
    view_crop_depth_m: float | None = None,
    target_visible_width_m: float | None = None,
    canvas_width_px: int = 1455,
    canvas_height_px: int = 1069,
    camera_tilt: float = 0.34,
    along_view_projection_scale: float = 1.0,
    symmetric_crop_fraction: float = 0.0,
    left_crop_fraction: float | None = None,
    right_crop_fraction: float | None = None,
    top_crop_fraction: float = 0.0,
    coast_frame_fraction: float = 0.44,
    vertical_exaggeration: float = DEFAULT_VERTICAL_EXAGGERATION,
    output_scale: float = 1.0,
    land_imagery_path: Path | None = None,
    bridge_decks: list[dict] | None = None,
    copyright_text: str | None = None,
    source_text: str | None = None,
    final_output_size_px: tuple[int, int] | list[int] | None = None,
    suppressed_label_levels: tuple[int, ...] | list[int] = (),
    land_sieve_threshold_px: int = 200,
    horizon_cleanup_fraction: float = 0.0,
    imagery_sea_depth_m: float | None = None,
    imagery_sea_feather_m: float = 0.6,
    imagery_sea_smoothing_m: float = 0.0,
    clip_rotated_outside: bool = True,
    imagery_sea_full_depth_m: float | None = None,
    imagery_sea_max_depth_m: float | None = None,
    view_center_offset_east_m: float = 0.0,
    view_center_offset_north_m: float = 0.0,
    coastline_visible: bool = True,
    final_style_scale: float = 2.0,
    max_land_elevation_m: float = 55.0,
    hemisphere_intensity: float = 1.7,
    key_light_intensity: float = 2.1,
    key_light_bearing_deg: float = 45.0,
    key_light_elevation_deg: float = 58.0,
    normal_sample_spacing_m: float = 2.0,
    exposure: float = DEFAULT_RELIEF_EXPOSURE,
    texture_triangle_min_area_px: float = 12.0,
    mesh_gap_fill_max_area_m2: float | None = None,
    deep_edge_nodata_fill: bool = False,
    deep_edge_nodata_min_depth_m: float | None = None,
) -> None:
    (
        elev_full,
        coast_full,
        land_full,
        land_weight_full,
        surface_valid_full,
        fused_depth,
        contours_full,
        coastlines_full,
    ) = build_fused_surface(
        depth_path, elevation_path, max_depth, rotation_k, coast_mode, land_sieve_threshold_px
    )
    step = 2
    d = np.clip(fused_depth[::step, ::step], 0.0, max_depth)
    elev = elev_full[::step, ::step]
    land_mask = land_full[::step, ::step]
    land_weight = land_weight_full[::step, ::step]
    surface_valid = surface_valid_full[::step, ::step]
    source_dataset = open_raster(depth_path, "source raster")
    source_pixel_m = abs(source_dataset.GetGeoTransform()[1]) * step
    if mesh_gap_fill_max_area_m2 is not None:
        if mesh_gap_fill_max_area_m2 <= 0.0:
            raise ValueError("Mesh gap fill maximum area must be positive")
        max_component_pixels = int(
            np.floor(mesh_gap_fill_max_area_m2 / (source_pixel_m**2))
        )
        if max_component_pixels >= 1:
            mesh_gap_fill = small_internal_mesh_gap_mask(
                surface_valid,
                land_mask,
                max_component_pixels,
            )
            if np.any(mesh_gap_fill):
                original_valid = surface_valid.copy()
                d = interpolate_mesh_gaps(d, mesh_gap_fill, original_valid)
                surface_valid = surface_valid | mesh_gap_fill
                filled_cells = int(np.count_nonzero(mesh_gap_fill))
                warnings.warn(
                    f"Interpolated {filled_cells} cells "
                    f"({filled_cells * source_pixel_m**2:.1f} m²) in the static "
                    "3D mesh only; contours remain source-derived",
                    stacklevel=2,
                )
    land_blend = np.where(land_mask, land_weight, 0.0)
    land_imagery = None
    orthophoto_texture = None
    orthophoto_alpha = None
    if land_imagery_path is not None:
        source_dataset = open_raster(depth_path, "source raster")
        imagery_dataset = open_raster(land_imagery_path, "land imagery")
        orthophoto_texture = load_rgb_raster(
            land_imagery_path,
            depth_path,
            width=imagery_dataset.RasterXSize,
            height=imagery_dataset.RasterYSize,
        )
        imagery_full = resize_rgb(
            orthophoto_texture,
            fused_depth.shape[1],
            fused_depth.shape[0],
        )
        if rotation_k % 4:
            imagery_full = np.rot90(imagery_full, rotation_k).copy()
            orthophoto_texture = np.rot90(
                orthophoto_texture,
                rotation_k,
            ).copy()
        if imagery_full.shape[:2] != fused_depth.shape:
            raise ValueError("Land imagery and fused relief do not share the same oriented dimensions")
        land_imagery = imagery_full[::step, ::step]
    sea_mask = surface_valid & ~land_mask
    valid = surface_valid
    coast_band = land_mask & (land_blend > 0.02) & (land_blend < 0.98)

    sea_z = -np.nan_to_num(d, nan=max_depth)
    sea_z = soften_surface(sea_z, sea_mask, passes=2)
    if max_land_elevation_m <= 0.0:
        raise ValueError("max_land_elevation_m must be positive")
    land_z = np.clip(np.nan_to_num(elev, nan=0.0), 0, max_land_elevation_m)
    land_z = soften_surface(land_z, land_mask, passes=10)
    land_z = apply_bridge_decks(
        land_z,
        source_dataset.GetGeoTransform(),
        source_dataset.RasterXSize,
        source_dataset.RasterYSize,
        rotation_k,
        step,
        bridge_decks,
    )
    if coast_mode == "profile":
        coast_sampled = coast_full[::step][: land_z.shape[1]]
        signed_coast_distance = np.arange(land_z.shape[0], dtype=np.float32)[:, None] * step - coast_sampled[None, :]
        land_ramp = np.clip(signed_coast_distance / 14.0, 0.0, 1.0)
    else:
        # Follow the same continuous surface as the sub-pixel coastline.
        # A binary distance ramp creates cell-by-cell height jumps; mixed
        # shoreline facets then rise as red teeth on the topographic render.
        land_ramp = np.clip((land_weight - 0.5) / 0.5, 0.0, 1.0)
    land_ramp = land_ramp * land_ramp * (3.0 - 2.0 * land_ramp)
    land_z *= land_ramp
    z = sea_z * (1.0 - land_blend) + land_z * land_blend

    sea_rgb = palette(np.nan_to_num(d, nan=max_depth), max_depth=max_depth).astype(np.float32)
    if land_imagery is None:
        land_color_z = soften_surface(
            np.clip(np.nan_to_num(elev, nan=0.0), 0, max_land_elevation_m),
            land_mask,
            passes=10,
        )
        land_rgb = land_palette(land_color_z).astype(np.float32)
    else:
        land_rgb = land_imagery.astype(np.float32)
    colors = np.zeros((*d.shape, 3), dtype=np.float32)
    colors[sea_mask] = sea_rgb[sea_mask]
    colors[land_mask] = land_rgb[land_mask]
    coastal_rgb = sea_rgb * (1 - land_blend[:, :, None]) + land_rgb * land_blend[:, :, None]
    colors[coast_band] = coastal_rgb[coast_band]
    colors = soften_rgb(colors, coast_band, passes=3)
    sea_imagery_enabled = (
        imagery_sea_depth_m is not None
        or imagery_sea_full_depth_m is not None
        or imagery_sea_max_depth_m is not None
    )
    if land_imagery is not None and sea_imagery_enabled:
        imagery_depth = smooth_depth_mask(d, imagery_sea_smoothing_m, source_pixel_m)
        sea_imagery_alpha = imagery_depth_alpha(
            imagery_depth,
            imagery_sea_depth_m,
            imagery_sea_feather_m,
            imagery_sea_full_depth_m,
            imagery_sea_max_depth_m,
        )
        assert sea_imagery_alpha is not None
        sea_imagery_alpha = np.where(
            sea_mask,
            sea_imagery_alpha,
            0.0,
        )
        orthophoto_alpha = imagery_alpha_across_shore(
            land_mask,
            sea_imagery_alpha,
        )
    elif land_imagery is not None:
        colors[sea_mask] = sea_rgb[sea_mask]
        # The displayed coastline is a smoothed vector. Pull the orthophoto a
        # metre inside its raw raster boundary so corners cannot protrude past
        # that line after perspective projection.
        strict_land = strict_land_imagery_mask(land_mask)
        coast_inset = land_mask & ~strict_land
        colors[coast_inset] = sea_rgb[coast_inset]
        orthophoto_alpha = strict_land.astype(np.float32)
    if orthophoto_alpha is not None:
        orthophoto_alpha = np.where(valid, orthophoto_alpha, 0.0).astype(np.float32)

    coast_points = [
        [(x / step, y / step) for x, y in line]
        for line in coastlines_full
    ]
    contour_points = {
        level: [[(x / step, y / step) for x, y in line] for line in lines]
        for level, lines in contours_full.items()
    }

    bearing = default_view_bearing(rotation_k) if view_bearing_deg is None else float(view_bearing_deg) % 360.0
    view_rotation = bearing - default_view_bearing(rotation_k)
    deep_rgb = palette(np.array([max_depth], dtype=np.float32), max_depth=max_depth)[0]
    z, colors, valid, land_mask, coast_points, contour_points = rotate_surface_for_view(
        z,
        colors,
        valid,
        land_mask,
        coast_points,
        contour_points,
        view_rotation,
        deep_rgb,
        clip_rotated_outside,
    )
    if orthophoto_texture is not None:
        orthophoto_texture = rotate_rgb_for_view(
            orthophoto_texture,
            view_rotation,
            tuple(int(value) for value in deep_rgb),
        )
    if orthophoto_alpha is not None:
        orthophoto_alpha = rotate_scalar_for_view(orthophoto_alpha, view_rotation)
        if orthophoto_alpha.shape != z.shape:
            raise ValueError("Rotated orthophoto alpha and relief mesh do not share the same dimensions")
    # Bicubic rotation can overshoot across the sharp zero-elevation
    # transition and give shallow-water cells positive heights. Reassert the
    # physical domains before projection so those cells cannot become red
    # spikes on the landward side of the coastline.
    z = np.where(land_mask, np.maximum(z, 0.0), np.minimum(z, 0.0))

    if view_crop_width_m is not None or view_crop_depth_m is not None:
        pixel_m = abs(source_dataset.GetGeoTransform()[1]) * step
        crop_w = z.shape[1] if view_crop_width_m is None else min(z.shape[1], int(round(float(view_crop_width_m) / pixel_m)))
        crop_h = z.shape[0] if view_crop_depth_m is None else min(z.shape[0], int(round(float(view_crop_depth_m) / pixel_m)))
        if crop_w <= 0 or crop_h <= 0:
            raise ValueError("view crop dimensions must be positive")
        source_dx = view_center_offset_east_m / pixel_m
        source_dy = -view_center_offset_north_m / pixel_m
        radians = np.deg2rad(view_rotation)
        rotated_dx = np.cos(radians) * source_dx + np.sin(radians) * source_dy
        rotated_dy = -np.sin(radians) * source_dx + np.cos(radians) * source_dy
        crop_x = (z.shape[1] - crop_w) // 2 + int(np.floor(rotated_dx + 0.5))
        crop_y = (z.shape[0] - crop_h) // 2 + int(np.floor(rotated_dy + 0.5))
        crop_x = int(np.clip(crop_x, 0, z.shape[1] - crop_w))
        crop_y = int(np.clip(crop_y, 0, z.shape[0] - crop_h))
        mesh_height, mesh_width = z.shape
        z = z[crop_y : crop_y + crop_h, crop_x : crop_x + crop_w]
        colors = colors[crop_y : crop_y + crop_h, crop_x : crop_x + crop_w]
        if orthophoto_texture is not None:
            texture_height, texture_width = orthophoto_texture.shape[:2]
            texture_x0 = int(np.floor(crop_x * texture_width / mesh_width))
            texture_x1 = int(np.ceil((crop_x + crop_w) * texture_width / mesh_width))
            texture_y0 = int(np.floor(crop_y * texture_height / mesh_height))
            texture_y1 = int(np.ceil((crop_y + crop_h) * texture_height / mesh_height))
            orthophoto_texture = orthophoto_texture[
                texture_y0:texture_y1,
                texture_x0:texture_x1,
            ]
        if orthophoto_alpha is not None:
            orthophoto_alpha = orthophoto_alpha[crop_y : crop_y + crop_h, crop_x : crop_x + crop_w]
        valid = valid[crop_y : crop_y + crop_h, crop_x : crop_x + crop_w]
        land_mask = land_mask[crop_y : crop_y + crop_h, crop_x : crop_x + crop_w]
        coast_points = [
            [(x - crop_x, y - crop_y) for x, y in line]
            for line in coast_points
        ]
        contour_points = {
            level: [[(x - crop_x, y - crop_y) for x, y in line] for line in lines]
            for level, lines in contour_points.items()
        }
        crop_bbox = (0.0, 0.0, float(crop_w - 1), float(crop_h - 1))
        coast_points = clip_polylines_to_bbox(coast_points, crop_bbox)
        contour_points = {
            level: clip_polylines_to_bbox(lines, crop_bbox)
            for level, lines in contour_points.items()
        }

    if deep_edge_nodata_fill:
        display_depth = np.clip(-z, 0.0, max_depth)
        component_diagnostics: list[dict[str, float | int | bool]] = []
        _, valid, deep_edge_fill = fill_deep_edge_nodata_at_maximum(
            display_depth,
            valid,
            land_mask,
            max_depth,
            min_boundary_depth_m=deep_edge_nodata_min_depth_m,
            component_diagnostics=component_diagnostics,
        )
        rejected = sorted(
            (
                item
                for item in component_diagnostics
                if not bool(item["qualifies"])
            ),
            key=lambda item: int(item["cells"]),
            reverse=True,
        )
        if rejected:
            summary = "; ".join(
                (
                    f"{int(item['cells'])} cells, "
                    f"{int(item['boundary_pixels'])} sea-boundary px, "
                    f"min {float(item['boundary_min_depth_m']):.1f} m, "
                    f"land={bool(item['touches_land'])}"
                )
                for item in rejected[:3]
            )
            warnings.warn(
                f"Rejected deep edge gap component(s): {summary}",
                stacklevel=2,
            )
        if np.any(deep_edge_fill):
            z[deep_edge_fill] = -max_depth
            colors[deep_edge_fill] = deep_rgb
            if orthophoto_alpha is not None:
                orthophoto_alpha = orthophoto_alpha.copy()
                orthophoto_alpha[deep_edge_fill] = 0.0
            filled_cells = int(np.count_nonzero(deep_edge_fill))
            warnings.warn(
                f"Filled {filled_cells} deep edge cells "
                f"({filled_cells * source_pixel_m**2:.1f} m²) with a flat "
                "maximum-depth surface in the static 3D crop; contours remain "
                "source-derived",
                stacklevel=2,
            )
    if mesh_gap_fill_max_area_m2 is not None:
        max_component_pixels = int(
            np.floor(mesh_gap_fill_max_area_m2 / (source_pixel_m**2))
        )
        if max_component_pixels >= 1:
            post_transform_gap_fill = small_internal_mesh_gap_mask(
                valid,
                land_mask,
                max_component_pixels,
            )
            if np.any(post_transform_gap_fill):
                original_valid = valid.copy()
                z = interpolate_mesh_gaps(
                    z,
                    post_transform_gap_fill,
                    original_valid,
                )
                colors = interpolate_mesh_gaps(
                    colors,
                    post_transform_gap_fill,
                    original_valid,
                )
                if orthophoto_alpha is not None:
                    orthophoto_alpha = interpolate_mesh_gaps(
                        orthophoto_alpha,
                        post_transform_gap_fill,
                        original_valid,
                    )
                valid = valid | post_transform_gap_fill
                filled_cells = int(np.count_nonzero(post_transform_gap_fill))
                warnings.warn(
                    f"Interpolated {filled_cells} post-transform cells "
                    f"({filled_cells * source_pixel_m**2:.1f} m²) in the "
                    "static 3D mesh only",
                    stacklevel=2,
                )

    if deep_edge_nodata_fill:
        remaining_invalid_cells = int(np.count_nonzero(~valid))
        if remaining_invalid_cells:
            warnings.warn(
                f"{remaining_invalid_cells} cells "
                f"({remaining_invalid_cells * source_pixel_m**2:.1f} m²) "
                "remain invalid after static 3D deep-edge completion",
                stacklevel=2,
            )

    invalid_fraction = float(np.count_nonzero(~valid) / valid.size)
    if invalid_fraction > 0.01:
        warnings.warn(
            f"{invalid_fraction:.1%} of the 3D crop has neither bathymetry nor elevation; "
            "invalid facets are omitted",
            stacklevel=2,
        )

    render_interp = 3 if not decorate else 2
    if render_interp > 1:
        z = resample_array(z, render_interp)
        colors = resample_array(colors, render_interp)
        if orthophoto_alpha is not None:
            orthophoto_alpha = resample_array(orthophoto_alpha, render_interp)
            orthophoto_alpha = np.clip(orthophoto_alpha, 0.0, 1.0)
        valid = resample_array(valid, render_interp)
        land_mask = resample_array(land_mask, render_interp)
        # Bicubic enlargement can reintroduce the same shoreline overshoot.
        z = np.where(land_mask, np.maximum(z, 0.0), np.minimum(z, 0.0))
        coast_points = [
            [(x * render_interp, y * render_interp) for x, y in line]
            for line in coast_points
        ]
        contour_points = {
            level: [[(x * render_interp, y * render_interp) for x, y in line] for line in lines]
            for level, lines in contour_points.items()
        }

    if orthophoto_texture is not None and orthophoto_alpha is not None:
        orthophoto_texture = resize_rgb(
            orthophoto_texture,
            z.shape[1],
            z.shape[0],
        )
        colors = blend_texture(colors, orthophoto_texture, orthophoto_alpha)

    original_w = z.shape[1]
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
    # This skirt is a visual continuation outside the mapped footprint, not a
    # data-bearing surface. Keep it in the deepest display colour and stop it
    # before shallow cells can project as narrow spires at a clipped or rotated
    # raster edge.
    foreground_colors = np.broadcast_to(
        deep_rgb,
        (*foreground_z.shape, 3),
    ).astype(np.float32).copy()
    foreground_valid = foreground_z <= -min(5.0, max_depth * 0.25)
    z = np.concatenate([foreground_z, z, np.pad(z[-1:], ((0, pad_south - 1), (0, 0)), mode="edge")], axis=0)
    colors = np.concatenate(
        [foreground_colors, colors, np.pad(colors[-1:], ((0, pad_south - 1), (0, 0), (0, 0)), mode="edge")],
        axis=0,
    )
    valid = np.concatenate(
        [foreground_valid, valid, np.repeat(valid[-1:], pad_south, axis=0)],
        axis=0,
    )
    land_mask = np.concatenate(
        [np.zeros((pad_north, land_mask.shape[1]), dtype=land_mask.dtype), land_mask, np.repeat(land_mask[-1:], pad_south, axis=0)],
        axis=0,
    )
    coast_points = [
        [(x + pad_x, y + pad_north) for x, y in line]
        for line in coast_points
    ]
    contour_points = {
        level: [[(x + pad_x, y + pad_north) for x, y in line] for line in lines]
        for level, lines in contour_points.items()
    }

    h, w = z.shape
    if not 0.0 <= symmetric_crop_fraction < 0.5:
        raise ValueError("symmetric_crop_fraction must be between 0 and 0.5")
    left_crop_fraction = symmetric_crop_fraction if left_crop_fraction is None else left_crop_fraction
    right_crop_fraction = symmetric_crop_fraction if right_crop_fraction is None else right_crop_fraction
    if not 0.0 <= left_crop_fraction < 1.0 or not 0.0 <= right_crop_fraction < 1.0:
        raise ValueError("left_crop_fraction and right_crop_fraction must be between 0 and 1")
    if left_crop_fraction + right_crop_fraction >= 1.0:
        raise ValueError("left and right crop fractions must retain a positive width")
    if not 0.0 <= top_crop_fraction < 1.0:
        raise ValueError("top_crop_fraction must be between 0 and 1")
    if along_view_projection_scale <= 0.0:
        raise ValueError("along_view_projection_scale must be positive")
    if vertical_exaggeration <= 0.0:
        raise ValueError("vertical_exaggeration must be positive")
    if output_scale <= 0.0:
        raise ValueError("output_scale must be positive")
    if final_style_scale <= 0.0:
        raise ValueError("final_style_scale must be positive")
    if texture_triangle_min_area_px <= 0.0:
        raise ValueError("texture_triangle_min_area_px must be positive")
    ui = output_scale
    base_canvas_w = int(canvas_width_px)
    base_canvas_h = int(canvas_height_px)
    if base_canvas_w <= 0 or base_canvas_h <= 0:
        raise ValueError("3D canvas dimensions must be positive")
    final_canvas_w = base_canvas_w
    final_canvas_h = base_canvas_h
    aa = 2
    pre_final_width = base_canvas_w * (1.0 - left_crop_fraction - right_crop_fraction) * ui
    pre_final_height = base_canvas_h * (1.0 - top_crop_fraction) * ui
    if final_output_size_px is None:
        final_resize_scale = 1.0
    else:
        final_width, final_height = map(int, final_output_size_px)
        final_resize_scale = np.sqrt(
            (final_width / pre_final_width) * (final_height / pre_final_height)
        )
    style = final_style_scale / final_resize_scale
    internal_style = style * aa / ui
    canvas_w, canvas_h = final_canvas_w * aa, final_canvas_h * aa
    sky = np.array((198, 219, 228), dtype=np.float32)
    abyss = deep_rgb.astype(np.float32)
    background_mix = np.linspace(0.0, 1.0, canvas_h, dtype=np.float32)[:, None, None]
    background = sky[None, None, :] * (1.0 - background_mix) + abyss[None, None, :] * background_mix
    background = np.repeat(background, canvas_w, axis=1).astype(np.uint8)
    canvas = Image.fromarray(background, "RGB").convert("RGBA")
    draw = ImageDraw.Draw(canvas, "RGBA")

    # Match the transverse 3D scale to the 2D footprint when requested. The
    # previous fixed zoom happened to match the Cap but over-zoomed wider sites.
    retained_canvas_width = base_canvas_w * (1.0 - left_crop_fraction - right_crop_fraction)
    source_pixel_m = abs(source_dataset.GetGeoTransform()[1])
    if target_visible_width_m is not None:
        if target_visible_width_m <= 0.0:
            raise ValueError("target_visible_width_m must be positive")
        zoom = retained_canvas_width * step * source_pixel_m / target_visible_width_m
    else:
        zoom = 2.0
    scale = zoom * aa / render_interp
    tilt = camera_tilt
    horizontal_pixels_per_m = zoom * aa / (step * source_pixel_m)
    zscale = vertical_exaggeration * horizontal_pixels_per_m

    focus_x = pad_x + original_w * 0.50

    def raw_project(px: np.ndarray | float, py: np.ndarray | float, zv: np.ndarray | float):
        # Observer au nord regardant vers le sud: l'est est a gauche et
        # l'ouest a droite, contrairement au plan 2D nord en haut.
        x = -(px - focus_x) * scale
        y = -(py - h / 2) * tilt * scale * along_view_projection_scale - zv * zscale
        return x, y

    ox = canvas_w / 2
    flat_coast = [
        point
        for line in coast_points
        for point in line
        if 0 <= point[0] < w and 0 <= point[1] < h
    ]
    if not flat_coast:
        raise ValueError("No coastline remains inside the 3D view crop")
    coast_xs = np.asarray([point[0] for point in flat_coast], dtype=np.float32)
    coast_ys = np.asarray([point[1] for point in flat_coast], dtype=np.float32)
    _, raw_coast_y = raw_project(coast_xs, coast_ys, np.zeros_like(coast_xs))
    oy = canvas_h * coast_frame_fraction - float(np.median(raw_coast_y))

    def project(px: float, py: float, zv: float) -> tuple[float, float]:
        x, y = raw_project(px, py, zv)
        return ox + float(x), oy + float(y)

    lighting_pixel_m = source_pixel_m * step / render_interp
    lit_colors = webgl_lit_colors(
        colors,
        z,
        pixel_size_m=lighting_pixel_m,
        vertical_exaggeration=vertical_exaggeration,
        view_bearing_deg=bearing,
        hemisphere_intensity=hemisphere_intensity,
        key_light_intensity=key_light_intensity,
        key_light_bearing_deg=key_light_bearing_deg,
        key_light_elevation_deg=key_light_elevation_deg,
        normal_sample_spacing_m=normal_sample_spacing_m,
        exposure=exposure,
    )
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
            corner_land = np.array([
                land_mask[j, i],
                land_mask[j, i + 1],
                land_mask[j + 1, i + 1],
                land_mask[j + 1, i],
            ], dtype=bool)
            corner_colors = np.stack([
                lit_colors[j, i],
                lit_colors[j, i + 1],
                lit_colors[j + 1, i + 1],
                lit_colors[j + 1, i],
            ])
            if np.any(corner_land) and not np.all(corner_land):
                # A shoreline quad must not inherit the red shallow-water
                # colour from whichever corner happens to be visited first.
                c = np.mean(corner_colors[corner_land], axis=0).astype(np.float32)
                draw.polygon(
                    pts,
                    fill=tuple(np.clip(c, 0, 255).astype(np.uint8).tolist()) + (255,),
                )
            else:
                span_x = max(point[0] for point in pts) - min(point[0] for point in pts)
                span_y = max(point[1] for point in pts) - min(point[1] for point in pts)
                if (
                    land_imagery_path is not None
                    and span_x * span_y >= texture_triangle_min_area_px
                ):
                    # The camera is orthographic, so barycentric interpolation
                    # across the two projected triangles is the exact texture
                    # mapping needed here. Restrict it to facets spanning
                    # several internal pixels; sub-pixel facets are correctly
                    # represented by their area-average and stay much faster.
                    draw_interpolated_triangle(
                        canvas,
                        [pts[0], pts[1], pts[2]],
                        corner_colors[[0, 1, 2]],
                    )
                    draw_interpolated_triangle(
                        canvas,
                        [pts[0], pts[2], pts[3]],
                        corner_colors[[0, 2, 3]],
                    )
                else:
                    c = np.mean(corner_colors, axis=0).astype(np.float32)
                    draw.polygon(
                        pts,
                        fill=tuple(np.clip(c, 0, 255).astype(np.uint8).tolist()) + (255,),
                    )

    # Vector lines are projected on the same surface after the mesh, so they
    # remain smooth and readable even across steep submarine walls.
    projected_contours: dict[int, list[list[tuple[float, float]]]] = {level: [] for level in contour_points}
    for level, lines in contour_points.items():
        for line in lines:
            points = [project(x, y, -float(level)) for x, y in line]
            if len(points) >= 2:
                projected_contours[level].append(points)
                draw.line(
                    points,
                    fill=(242, 235, 204, 205),
                    width=max(1, int(np.floor(4 * internal_style + 0.5))),
                    joint="curve",
                )
                draw.line(
                    points,
                    fill=(5, 7, 10, 235),
                    width=max(1, int(np.floor(2 * internal_style + 0.5))),
                    joint="curve",
                )

    projected_coastlines = [[project(x, y, 0.0) for x, y in line] for line in coast_points]
    if coastline_visible:
        for projected_coast in projected_coastlines:
            # Cover the last sub-pixel mismatch between the smooth vector
            # coastline and the rotated raster mesh before drawing the crisp
            # cartographic stroke. This prevents shallow red facets from
            # peeking through on the landward side.
            draw.line(
                projected_coast,
                fill=(242, 235, 204, 230),
                width=max(1, int(np.floor(12 * internal_style + 0.5))),
                joint="curve",
            )
            draw.line(
                projected_coast,
                fill=(3, 3, 3, 255),
                width=max(1, int(np.floor(4 * internal_style + 0.5))),
                joint="curve",
            )

    full_output_w = int(np.floor(base_canvas_w * ui + 0.5))
    full_output_h = int(np.floor(base_canvas_h * ui + 0.5))
    canvas = canvas.resize((full_output_w, full_output_h), Image.Resampling.LANCZOS)
    projection_to_output = ui / aa
    crop_left_base = int(np.floor(base_canvas_w * left_crop_fraction + 0.5))
    crop_right_base = int(np.floor(base_canvas_w * right_crop_fraction + 0.5))
    crop_left = int(np.floor(crop_left_base * ui + 0.5))
    crop_right = int(np.floor(crop_right_base * ui + 0.5))
    # Crop in view coordinates after projection so camera geometry and the
    # cross-track metre scale remain unchanged.
    crop_top_base = int(np.floor(base_canvas_h * top_crop_fraction))
    crop_top = int(np.floor(crop_top_base * ui + 0.5))
    if crop_left or crop_right or crop_top:
        canvas = canvas.crop((crop_left, crop_top, full_output_w - crop_right, full_output_h))
    draw = ImageDraw.Draw(canvas, "RGBA")
    if horizon_cleanup_fraction:
        if not 0.0 <= horizon_cleanup_fraction < 0.25:
            raise ValueError("horizon_cleanup_fraction must be between 0 and 0.25")
        horizon_y = int(np.floor(canvas.height * horizon_cleanup_fraction + 0.5))
        draw.rectangle((0, 0, canvas.width, horizon_y), fill=(198, 219, 228, 255))

    if not decorate:
        label_font = load_font(int(np.floor(20 * style + 0.5)), True)
        label_stroke = max(1, int(np.floor(2 * style + 0.5)))
        label_clearance = 8.0 * style
        transformed_contours = {
            level: [
                [
                    (
                        x * projection_to_output - crop_left,
                        y * projection_to_output - crop_top,
                    )
                    for x, y in line
                ]
                for line in projected_contours.get(level, [])
            ]
            for level in contour_points
        }
        occupied_label_bboxes: list[tuple[float, float, float, float]] = []

        def label_placement(
            level: int,
            anchor: tuple[float, float],
            *,
            centered: bool,
        ) -> tuple[
            tuple[float, float],
            tuple[float, float, float, float],
        ]:
            x, y = anchor
            position = (
                (x - 27 * style, y - 13 * style)
                if centered
                else (x + 6 * style, y - 13 * style)
            )
            bbox = tuple(
                float(value)
                for value in draw.textbbox(
                    position,
                    f"-{level} m",
                    font=label_font,
                    stroke_width=label_stroke,
                )
            )
            return position, bbox

        def label_position_is_clear(
            level: int,
            bbox: tuple[float, float, float, float],
        ) -> bool:
            safe_bbox = expanded_bbox(bbox, label_clearance)
            if not (
                0.0 < safe_bbox[0]
                and safe_bbox[2] < canvas.width
                and 0.0 < safe_bbox[1]
                and safe_bbox[3] < canvas.height
            ):
                return False
            if any(
                bboxes_intersect(safe_bbox, expanded_bbox(other, label_clearance))
                for other in occupied_label_bboxes
            ):
                return False
            return not any(
                polyline_intersects_bbox(line, safe_bbox)
                for other_level, lines in transformed_contours.items()
                if int(other_level) != int(level)
                for line in lines
            )

        def draw_isobath_label(
            level: int,
            position: tuple[float, float],
            bbox: tuple[float, float, float, float],
        ) -> None:
            occupied_label_bboxes.append(bbox)
            draw.text(
                position,
                f"-{level} m",
                font=label_font,
                fill=(3, 4, 6, 245),
                stroke_width=label_stroke,
                stroke_fill=(245, 239, 210, 235),
            )

        suppressed_labels = {int(level) for level in suppressed_label_levels}
        for level in sorted(contour_points):
            if int(level) in suppressed_labels:
                continue
            transformed_lines = transformed_contours[level]
            open_lines = []
            for line in transformed_lines:
                center = isolated_contour_center(line, min_width=45.0 * style, min_height=20.0 * style)
                is_closed = len(line) >= 2 and np.linalg.norm(np.asarray(line[0]) - np.asarray(line[-1])) < 4.0 * style
                if is_closed:
                    placed = False
                    if center and 55 * style < center[0] < canvas.width - 100 * style and 35 * style < center[1] < canvas.height - 35 * style:
                        position, bbox = label_placement(level, center, centered=True)
                        if label_position_is_clear(level, bbox):
                            draw_isobath_label(level, position, bbox)
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
                    if not (55 * style < x < canvas.width - 100 * style and 35 * style < y < canvas.height - 35 * style):
                        continue
                    position, bbox = label_placement(level, (x, y), centered=False)
                    if not label_position_is_clear(level, bbox):
                        continue
                    dx = line[index + 2][0] - line[index - 2][0]
                    dy = line[index + 2][1] - line[index - 2][1]
                    horizontal = abs(dx) / (abs(dx) + abs(dy) + 1e-6)
                    edge_gap = min(x - 55 * style, canvas.width - 100 * style - x, y - 35 * style, canvas.height - 35 * style - y)
                    separation = min(
                        (
                            np.hypot(
                                x - (other[0] + other[2]) / 2.0,
                                y - (other[1] + other[3]) / 2.0,
                            )
                            for other in occupied_label_bboxes
                        ),
                        default=250.0 * style,
                    )
                    focus_penalty = 0.32 * abs(x - canvas.width * 0.48)
                    score = edge_gap + 55.0 * style * horizontal + min(separation, 160.0 * style) - focus_penalty
                    if score > best_score:
                        best_score = score
                        best = (position, bbox)
            if best is None:
                near_frame = [
                    (x, y)
                    for line in open_lines
                    for x, y in line
                    if 55 * style < x < canvas.width - 100 * style and -25 * style < y < canvas.height + 25 * style
                ]
                if near_frame:
                    for x, y in sorted(
                        near_frame,
                        key=lambda point: abs(point[0] - canvas.width / 2),
                    ):
                        anchor = (
                            x,
                            float(np.clip(y, 35 * style, canvas.height - 35 * style)),
                        )
                        position, bbox = label_placement(level, anchor, centered=False)
                        if label_position_is_clear(level, bbox):
                            best = (position, bbox)
                            break
            if best:
                position, bbox = best
                draw_isobath_label(level, position, bbox)

        annotation_font = load_font(int(np.floor(20 * style + 0.5)), True)
        pixel_m = abs(gdal.Open(str(depth_path)).GetGeoTransform()[1])
        bar_px = 50.0 * zoom / step / pixel_m * ui
        sx, sy = 55 * style, canvas.height - 50 * style
        draw.line((sx, sy, sx + bar_px, sy), fill=(245, 239, 210, 245), width=max(1, int(np.floor(8 * style + 0.5))))
        draw.line((sx, sy, sx + bar_px, sy), fill=(5, 7, 10, 255), width=max(1, int(np.floor(3 * style + 0.5))))
        draw.line((sx, sy - 9 * style, sx, sy + 9 * style), fill=(5, 7, 10, 255), width=max(1, int(np.floor(3 * style + 0.5))))
        draw.line((sx + bar_px, sy - 9 * style, sx + bar_px, sy + 9 * style), fill=(5, 7, 10, 255), width=max(1, int(np.floor(3 * style + 0.5))))
        draw.text((sx + bar_px / 2 - 24 * style, sy - 34 * style), "50 m", font=annotation_font, fill=(5, 7, 10, 255), stroke_width=max(1, int(np.floor(2 * style + 0.5))), stroke_fill=(245, 239, 210, 235))

        draw_compass_rose(
            draw,
            (76.0 * style, 76.0 * style),
            bearing,
            annotation_font,
            style,
        )

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
    if copyright_text:
        copyright_font = load_font(int(np.floor(13 * style + 0.5)), True)
        draw.text(
            (canvas.width - 16 * style, canvas.height - 12 * style),
            copyright_text,
            anchor="rb",
            font=copyright_font,
            fill=(245, 239, 218, 235),
            stroke_width=max(1, int(np.floor(2 * style + 0.5))),
            stroke_fill=(5, 9, 13, 225),
        )
    if source_text:
        source_font = load_font(int(np.floor(10 * style + 0.5)), False)
        draw.text(
            (16 * style, canvas.height - 12 * style),
            source_text,
            anchor="lb",
            font=source_font,
            fill=(245, 239, 218, 225),
            stroke_width=max(1, int(np.floor(1.5 * style + 0.5))),
            stroke_fill=(5, 9, 13, 215),
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    rendered = canvas.convert("RGB")
    if final_output_size_px is not None:
        rendered = resize_exact_without_distortion(rendered, final_output_size_px)
    rendered.save(output, quality=98, subsampling=0, optimize=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a 2D plan and a clean 3D view from aligned depth and elevation rasters")
    parser.add_argument("depth", type=Path, help="Positive-depth GeoTIFF")
    parser.add_argument("elevation", type=Path, help="Elevation GeoTIFF")
    parser.add_argument("output_prefix", type=Path, help="Output path prefix")
    parser.add_argument("title", help="Map title used by the optional decorated 3D renderer")
    args = parser.parse_args()
    plan_output = args.output_prefix.with_name(args.output_prefix.name + "-2d.jpg")
    relief_output = args.output_prefix.with_name(args.output_prefix.name + "-3d.jpg")
    make_clean_plan(args.depth, args.elevation, plan_output)
    make_pretty_3d_from_offshore(args.depth, args.elevation, relief_output, args.title, decorate=False)
    print(plan_output)
    print(relief_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
