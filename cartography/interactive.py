from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
import shutil
import tempfile
import warnings
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Any, Iterator

import numpy as np
from osgeo import gdal
from PIL import Image

from cartography.relief import (
    NO_DATA_RGB,
    apply_bridge_decks,
    blend_texture,
    build_fused_surface,
    default_view_bearing,
    fill_deep_edge_nodata_at_maximum,
    hillshade,
    imagery_alpha_across_shore,
    imagery_depth_alpha,
    land_palette,
    load_rgb_raster,
    local_slope_shade,
    open_raster,
    palette,
    smooth_depth_mask,
    soften_surface,
    strict_land_imagery_mask,
)
from cartography.bathymetry_style import (
    LAND_SLOPE_MAX_DARKENING,
    LAND_SLOPE_MAX_DEG,
    LAND_SLOPE_SMOOTHING_PASSES,
    SEA_SLOPE_MAX_DARKENING,
    SEA_SLOPE_MAX_DEG,
    SEA_SLOPE_SMOOTHING_PASSES,
)
from cartography.config import (
    DEFAULT_RELIEF_EXPOSURE,
    DEFAULT_VERTICAL_EXAGGERATION,
    bbox,
    interactive_footprint,
    interactive_footprint_bounds,
    interactive_footprint_corners,
    paths_for,
    region_manifest,
    region_output_directory,
    region_site_config_directory,
    validate_config,
)
from cartography.vector_isobaths import (
    extract_vector_isobaths,
    validate_vector_isobath_payload,
)


DEFAULT_REGION_CONFIG = {"region": "reunion"}
DEFAULT_CONFIG_DIRECTORY = region_site_config_directory(DEFAULT_REGION_CONFIG)
DEFAULT_OUTPUT = (
    region_output_directory(DEFAULT_REGION_CONFIG) / "interactive-terrain"
)
DEFAULT_GRID_MAX = 513
DEFAULT_TEXTURE_MAX = 2048
DEFAULT_VECTOR_ISOBATH_MAX_BYTES = 512 * 1024
DEFAULT_VECTOR_ISOBATH_MAX_POLYLINES = 256
DEFAULT_VECTOR_ISOBATH_MAX_POINTS = 50_000
SCHEMA_VERSION = 2


def interactive_max_depth(config: dict[str, Any]) -> float:
    return float(config.get("interactive_max_depth_m", config.get("max_depth_m", 20.0)))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact_record(path: Path, output_root: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(output_root).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def load_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    validate_config(config)
    return config


@contextmanager
def interactive_source_paths(
    config: dict[str, Any],
    paths: dict[str, Path],
) -> Iterator[dict[str, Path]]:
    """Yield focus-like rasters for the optional interactive-only extent."""
    if "interactive_footprint_utm40s" in config:
        west, south, east, north = interactive_footprint_bounds(config)
    elif "interactive_bbox_utm40s" in config:
        west, south, east, north = bbox(config, "interactive_bbox_utm40s")
    else:
        yield paths
        return

    source_keys = {
        "focus_depth": "context_depth",
        "focus_elevation": "context_elevation",
        "focus_orthophoto": "context_orthophoto",
    }
    with tempfile.TemporaryDirectory(
        prefix=f".{config['slug']}-interactive-source-",
    ) as temporary_directory:
        cropped_paths = dict(paths)
        temporary_root = Path(temporary_directory)
        for focus_key, context_key in source_keys.items():
            destination = temporary_root / f"{focus_key}.tif"
            translated = gdal.Translate(
                str(destination),
                str(paths[context_key]),
                format="GTiff",
                projWin=[west, north, east, south],
            )
            if translated is None:
                raise RuntimeError(
                    f"Could not crop {context_key} to the interactive extent"
                )
            translated.FlushCache()
            translated = None
            cropped_paths[focus_key] = destination
        yield cropped_paths


def interactive_footprint_mask(
    config: dict[str, Any],
    raster_path: Path,
    output_shape: tuple[int, int],
) -> np.ndarray:
    """Mask the north-up crop to its coastline-aligned rectangle."""
    if "interactive_footprint_utm40s" not in config:
        return np.ones(output_shape, dtype=bool)

    center, width, depth, bearing_deg = interactive_footprint(config)
    source = open_raster(raster_path, "interactive footprint raster")
    transform = source.GetGeoTransform()
    if (
        abs(float(transform[2])) > 1e-9
        or abs(float(transform[4])) > 1e-9
    ):
        raise ValueError("Interactive footprint raster must be north-up")

    columns = source.RasterXSize
    rows = source.RasterYSize
    eastings = (
        float(transform[0])
        + (np.arange(columns, dtype=np.float32) + 0.5)
        * float(transform[1])
        - center[0]
    )
    northings = (
        float(transform[3])
        + (np.arange(rows, dtype=np.float32) + 0.5)
        * float(transform[5])
        - center[1]
    )
    bearing = math.radians(bearing_deg)
    forward_east = math.sin(bearing)
    forward_north = math.cos(bearing)
    right_east = math.cos(bearing)
    right_north = -math.sin(bearing)
    tolerance = max(abs(float(transform[1])), abs(float(transform[5]))) * 0.75
    mask = np.empty((rows, columns), dtype=bool)
    for row_start in range(0, rows, 256):
        row_stop = min(row_start + 256, rows)
        delta_north = northings[row_start:row_stop, None]
        delta_east = eastings[None, :]
        across = (
            delta_east * right_east
            + delta_north * right_north
        )
        along = (
            delta_east * forward_east
            + delta_north * forward_north
        )
        mask[row_start:row_stop] = (
            (np.abs(across) <= width * 0.5 + tolerance)
            & (np.abs(along) <= depth * 0.5 + tolerance)
        )

    rotation_k = int(config.get("rotation_k", 0)) % 4
    if rotation_k:
        mask = np.rot90(mask, rotation_k).copy()
    if mask.shape != output_shape:
        raise ValueError(
            "Interactive footprint mask and fused surface do not share "
            f"the same dimensions: {mask.shape} != {output_shape}"
        )
    return mask


def fitted_dimensions(
    width: int,
    height: int,
    longest_dimension: int,
    *,
    preserve_vertices: bool = False,
) -> tuple[int, int]:
    if min(width, height, longest_dimension) < 2:
        raise ValueError("Raster and target dimensions must be at least 2 pixels")
    if max(width, height) <= longest_dimension:
        return width, height

    if preserve_vertices:
        # Heightfields cover the intervals between vertices. Scaling those
        # intervals keeps the first and last vertex exactly on the footprint.
        scale = (longest_dimension - 1) / (max(width, height) - 1)
        target_width = int(round((width - 1) * scale)) + 1
        target_height = int(round((height - 1) * scale)) + 1
    else:
        scale = longest_dimension / max(width, height)
        target_width = int(round(width * scale))
        target_height = int(round(height * scale))
    return max(2, target_width), max(2, target_height)


def resize_scalar(values: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    image = Image.fromarray(values.astype(np.float32), mode="F")
    return np.asarray(image.resize(size, Image.Resampling.BICUBIC), dtype=np.float32)


def resize_mask(mask: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    image = Image.fromarray(mask.astype(np.uint8) * 255, mode="L")
    return np.asarray(image.resize(size, Image.Resampling.NEAREST), dtype=np.uint8) > 127


def isobath_source_vertex_mask(
    deep_edge_fill: np.ndarray,
    size: tuple[int, int],
    source_valid: np.ndarray | None = None,
) -> np.ndarray:
    """Return valid source vertices outside filled/transition triangles."""
    safe = np.ones((size[1], size[0]), dtype=bool)
    if np.any(deep_edge_fill):
        fill_image = Image.fromarray(
            deep_edge_fill.astype(np.float32),
            mode="F",
        )
        grid_fill = (
            np.asarray(
                fill_image.resize(size, Image.Resampling.BOX),
                dtype=np.float32,
            )
            > 0.0
        )
        transition_cells = (
            grid_fill[:-1, :-1]
            | grid_fill[:-1, 1:]
            | grid_fill[1:, :-1]
            | grid_fill[1:, 1:]
        )
        safe[:-1, :-1][transition_cells] = False
        safe[:-1, 1:][transition_cells] = False
        safe[1:, :-1][transition_cells] = False
        safe[1:, 1:][transition_cells] = False
    if source_valid is not None:
        safe &= resize_mask(source_valid, size)
    return safe


def make_surface(
    config: dict[str, Any],
    paths: dict[str, Path],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    max_depth = interactive_max_depth(config)
    max_land_elevation = float(config.get("max_land_elevation_m", 55.0))
    rotation_k = int(config.get("rotation_k", 0))
    coast_mode = str(config.get("coast_mode", "profile"))
    sieve = int(config.get("land_sieve_threshold_px", 200))
    (
        elevation,
        coast_y,
        land_mask,
        land_weight,
        valid,
        fused_depth,
        _contours,
        _coastlines,
    ) = build_fused_surface(
        paths["focus_depth"],
        paths["focus_elevation"],
        max_depth,
        rotation_k,
        coast_mode,
        sieve,
    )

    depth = np.clip(fused_depth, 0.0, max_depth)
    sea_mask = valid & ~land_mask
    land_blend = np.where(land_mask, land_weight, 0.0).astype(np.float32)

    sea_z = soften_surface(
        -np.nan_to_num(depth, nan=max_depth),
        sea_mask,
        passes=2,
    )
    land_z = soften_surface(
        np.clip(np.nan_to_num(elevation, nan=0.0), 0.0, max_land_elevation),
        land_mask,
        passes=10,
    )
    source = open_raster(paths["focus_depth"], "focus depth raster")
    land_z = apply_bridge_decks(
        land_z,
        source.GetGeoTransform(),
        source.RasterXSize,
        source.RasterYSize,
        rotation_k,
        1,
        config.get("bridge_decks"),
    )

    if coast_mode == "profile":
        signed_distance = (
            np.arange(land_z.shape[0], dtype=np.float32)[:, None]
            - coast_y[None, :]
        )
        land_ramp = np.clip(signed_distance / 14.0, 0.0, 1.0)
    else:
        land_ramp = np.clip((land_weight - 0.5) / 0.5, 0.0, 1.0)
    land_ramp = land_ramp * land_ramp * (3.0 - 2.0 * land_ramp)
    land_z *= land_ramp

    surface = sea_z * (1.0 - land_blend) + land_z * land_blend
    surface = np.where(land_mask, np.maximum(surface, 0.0), np.minimum(surface, 0.0))
    surface = np.where(valid, surface, -max_depth).astype(np.float32)
    return surface, depth, elevation, land_mask, land_weight, valid


def complete_interactive_deep_edge_nodata(
    config: dict[str, Any],
    surface: np.ndarray,
    depth: np.ndarray,
    land_mask: np.ndarray,
    valid: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Apply the explicit flat-at-maximum completion to interactive terrain."""
    if not config.get("deep_edge_nodata_terrain_fill", False):
        return surface, depth, valid, np.zeros_like(valid)

    max_depth = interactive_max_depth(config)
    filled_depth, filled_valid, fill_mask = fill_deep_edge_nodata_at_maximum(
        depth,
        valid,
        land_mask,
        max_depth,
        min_boundary_depth_m=config.get(
            "deep_edge_nodata_terrain_min_depth_m"
        ),
    )
    filled_surface = surface.copy()
    filled_surface[fill_mask] = -max_depth
    return filled_surface, filled_depth, filled_valid, fill_mask


def make_textures(
    config: dict[str, Any],
    paths: dict[str, Path],
    depth: np.ndarray,
    elevation: np.ndarray,
    land_mask: np.ndarray,
    land_weight: np.ndarray,
    valid: np.ndarray,
) -> tuple[Image.Image, Image.Image]:
    max_depth = interactive_max_depth(config)
    max_land_elevation = float(config.get("max_land_elevation_m", 55.0))
    sea_mask = valid & ~land_mask
    land_blend = np.where(land_mask, land_weight, 0.0)

    sea_rgb = palette(
        np.nan_to_num(depth, nan=max_depth),
        max_depth=max_depth,
        scheme=str(config.get("bathymetry_palette", "legacy")),
        depth_scale=str(
            config.get("bathymetry_depth_scale", "legacy_linear")
        ),
    ).astype(np.float32)
    sea_shading = str(config.get("plan_sea_shading", "directional"))
    land_shading = str(config.get("plan_land_shading", "none"))
    source_dataset = open_raster(paths["focus_depth"], "focus depth raster")
    geotransform = source_dataset.GetGeoTransform()
    pixel_size_x_m = float(np.hypot(geotransform[1], geotransform[4]))
    pixel_size_y_m = float(np.hypot(geotransform[2], geotransform[5]))
    if int(config.get("rotation_k", 0)) % 2:
        pixel_size_x_m, pixel_size_y_m = pixel_size_y_m, pixel_size_x_m
    if sea_shading == "directional":
        sea_shade = hillshade(
            np.nan_to_num(depth, nan=max_depth),
            sea_mask,
            0.035,
        )
    elif sea_shading == "local_slope":
        sea_shade = local_slope_shade(
            np.nan_to_num(depth, nan=max_depth),
            sea_mask,
            pixel_size_x_m,
            pixel_size_y_m,
            max_slope_deg=SEA_SLOPE_MAX_DEG,
            max_darkening=SEA_SLOPE_MAX_DARKENING,
            smoothing_passes=SEA_SLOPE_SMOOTHING_PASSES,
        )
    else:
        sea_shade = np.ones_like(depth, dtype=np.float32)
    sea_rgb *= sea_shade[:, :, None]
    sea_rgb = np.clip(sea_rgb, 0.0, 255.0)
    land_color_z = soften_surface(
        np.clip(np.nan_to_num(elevation, nan=0.0), 0.0, max_land_elevation),
        land_mask,
        passes=2,
    )
    land_rgb = land_palette(land_color_z).astype(np.float32)
    if land_shading == "local_slope":
        land_rgb *= local_slope_shade(
            np.clip(
                np.nan_to_num(elevation, nan=0.0),
                0.0,
                max_land_elevation,
            ),
            land_mask,
            pixel_size_x_m,
            pixel_size_y_m,
            max_slope_deg=LAND_SLOPE_MAX_DEG,
            max_darkening=LAND_SLOPE_MAX_DARKENING,
            smoothing_passes=LAND_SLOPE_SMOOTHING_PASSES,
        )[:, :, None]
        land_rgb = np.clip(land_rgb, 0.0, 255.0)

    topographic = np.broadcast_to(NO_DATA_RGB, (*depth.shape, 3)).copy()
    topographic[sea_mask] = sea_rgb[sea_mask]
    topographic = (
        topographic * (1.0 - land_blend[:, :, None])
        + land_rgb * land_blend[:, :, None]
    )
    topographic[~valid] = NO_DATA_RGB

    orthophoto = load_rgb_raster(
        paths["focus_orthophoto"],
        paths["focus_depth"],
    )
    rotation_k = int(config.get("rotation_k", 0)) % 4
    if rotation_k:
        orthophoto = np.rot90(orthophoto, rotation_k).copy()
    if orthophoto.shape[:2] != depth.shape:
        raise ValueError("Orthophoto and fused surface do not share the same dimensions")

    alpha = np.where(
        land_mask,
        np.clip((land_weight - 0.5) * 2.0, 0.0, 1.0),
        0.0,
    )
    imagery_enabled_at_sea = any(
        config.get(key) is not None
        for key in (
            "imagery_sea_depth_m",
            "imagery_sea_full_depth_m",
            "imagery_sea_max_depth_m",
        )
    )
    if imagery_enabled_at_sea:
        source = open_raster(paths["focus_depth"], "focus depth raster")
        pixel_m = abs(source.GetGeoTransform()[1])
        imagery_depth = smooth_depth_mask(
            depth,
            float(config.get("imagery_sea_smoothing_m", 0.0)),
            pixel_m,
        )
        sea_alpha = imagery_depth_alpha(
            imagery_depth,
            config.get("imagery_sea_depth_m"),
            float(config.get("imagery_sea_feather_m", 0.6)),
            config.get("imagery_sea_full_depth_m"),
            config.get("imagery_sea_max_depth_m"),
        )
        assert sea_alpha is not None
        alpha = imagery_alpha_across_shore(land_mask, sea_alpha)
    else:
        alpha = np.minimum(alpha, strict_land_imagery_mask(land_mask))
    alpha = np.where(valid, alpha, 0.0).astype(np.float32)

    orthophoto_composite = blend_texture(topographic, orthophoto, alpha)
    orthophoto_composite[~valid] = NO_DATA_RGB
    return (
        Image.fromarray(np.clip(topographic, 0, 255).astype(np.uint8), "RGB"),
        Image.fromarray(
            np.clip(orthophoto_composite, 0, 255).astype(np.uint8),
            "RGB",
        ),
    )


def source_attribution(config: dict[str, Any], *, orthophoto: bool) -> str:
    sources = region_manifest(config)["sources"]
    bathymetry_attribution = str(
        config.get(
            "bathymetry_attribution",
            sources["bathymetry"]["attribution"],
        )
    )
    text = (
        f"Bathymétrie : {bathymetry_attribution} · "
        f"Topographie : {sources['landElevation']['attribution']}"
    )
    if orthophoto:
        capture_date = date.fromisoformat(str(config["orthophoto_capture_date"]))
        text += (
            " · Orthophoto : IGN BD ORTHO, prise de vue "
            f"{capture_date.strftime('%d-%m-%Y')}"
        )
    return text


def static_view_horizontal_center_offset_m(
    config: dict[str, Any],
    focus_bounds: tuple[float, float, float, float],
) -> float | None:
    """Return the static crop centre on the initial view's screen-right axis.

    The value is expressed in metres from the focus terrain's geometric
    centre. Positive values move the initial framing to screen right. Keeping
    this one-dimensional lets the viewer continue to place the coastline
    vertically from the terrain itself.
    """
    if not config.get("interactive_match_static_horizontal_center", False):
        return None

    focus_west, focus_south, focus_east, focus_north = focus_bounds
    context_west, context_south, context_east, context_north = (
        float(value) for value in config["context_bbox_utm40s"]
    )
    focus_center_east = (focus_west + focus_east) / 2.0
    focus_center_north = (focus_south + focus_north) / 2.0
    static_center_east = (
        (context_west + context_east) / 2.0
        + float(config.get("view_center_offset_east_m", 0.0))
    )
    static_center_north = (
        (context_south + context_north) / 2.0
        + float(config.get("view_center_offset_north_m", 0.0))
    )

    rotation_k = int(config.get("rotation_k", 0))
    bearing_deg = float(
        config.get("view_bearing_deg", default_view_bearing(rotation_k))
    ) % 360.0
    bearing = math.radians(bearing_deg)
    delta_east = static_center_east - focus_center_east
    delta_north = static_center_north - focus_center_north
    # At bearing 0 degrees, east is screen right. Rotating the view clockwise
    # rotates screen right toward the south, hence the negative north term.
    return delta_east * math.cos(bearing) - delta_north * math.sin(bearing)


def static_view_along_center_offset_m(
    config: dict[str, Any],
    focus_bounds: tuple[float, float, float, float],
) -> float | None:
    """Return the static crop centre on the initial view's forward axis."""
    if not config.get("interactive_match_static_along_center", False):
        return None

    focus_west, focus_south, focus_east, focus_north = focus_bounds
    context_west, context_south, context_east, context_north = (
        float(value) for value in config["context_bbox_utm40s"]
    )
    focus_center_east = (focus_west + focus_east) / 2.0
    focus_center_north = (focus_south + focus_north) / 2.0
    static_center_east = (
        (context_west + context_east) / 2.0
        + float(config.get("view_center_offset_east_m", 0.0))
    )
    static_center_north = (
        (context_south + context_north) / 2.0
        + float(config.get("view_center_offset_north_m", 0.0))
    )

    bearing = math.radians(
        float(config.get("view_bearing_deg", 0.0)) % 360.0
    )
    delta_east = static_center_east - focus_center_east
    delta_north = static_center_north - focus_center_north
    return delta_east * math.sin(bearing) + delta_north * math.cos(bearing)


def view_center_metadata(
    config: dict[str, Any],
    focus_bounds: tuple[float, float, float, float],
) -> dict[str, float]:
    metadata: dict[str, float] = {}
    horizontal_center_offset = static_view_horizontal_center_offset_m(
        config,
        focus_bounds,
    )
    if horizontal_center_offset is not None:
        metadata["horizontalCenterOffsetM"] = round(
            horizontal_center_offset,
            6,
        )
    along_center_offset = config.get("interactive_view_along_center_offset_m")
    if along_center_offset is None:
        along_center_offset = static_view_along_center_offset_m(
            config,
            focus_bounds,
        )
    if along_center_offset is not None:
        metadata["alongCenterOffsetM"] = round(
            float(along_center_offset),
            6,
        )
    return metadata


def _export_site_from_paths(
    config: dict[str, Any],
    paths: dict[str, Path],
    output_root: Path,
    grid_max: int,
    texture_max: int,
) -> dict[str, Any]:
    surface, depth, elevation, land_mask, land_weight, valid = make_surface(
        config,
        paths,
    )
    surface, depth, valid, deep_edge_fill = (
        complete_interactive_deep_edge_nodata(
            config,
            surface,
            depth,
            land_mask,
            valid,
        )
    )
    footprint_mask = interactive_footprint_mask(
        config,
        paths["focus_depth"],
        valid.shape,
    )
    valid &= footprint_mask
    deep_edge_fill &= footprint_mask
    if np.any(deep_edge_fill):
        source = open_raster(paths["focus_depth"], "focus depth raster")
        transform = source.GetGeoTransform()
        pixel_area_m2 = abs(
            float(transform[1]) * float(transform[5])
            - float(transform[2]) * float(transform[4])
        )
        filled_cells = int(np.count_nonzero(deep_edge_fill))
        warnings.warn(
            f"Filled {filled_cells} deep edge cells "
            f"({filled_cells * pixel_area_m2:.1f} m²) with a flat "
            "maximum-depth surface in the interactive terrain",
            stacklevel=2,
        )
    topographic_texture, orthophoto_texture = make_textures(
        config,
        paths,
        depth,
        elevation,
        land_mask,
        land_weight,
        valid,
    )

    slug = str(config["slug"])
    site_output = output_root / slug
    site_output.mkdir(parents=True, exist_ok=True)

    grid_size = fitted_dimensions(
        surface.shape[1],
        surface.shape[0],
        grid_max,
        preserve_vertices=True,
    )
    grid_surface = resize_scalar(surface, grid_size)
    grid_valid = resize_mask(valid, grid_size)
    grid_land = resize_mask(land_mask, grid_size)
    grid_isobath_source = isobath_source_vertex_mask(
        deep_edge_fill,
        grid_size,
        valid,
    )
    max_depth = interactive_max_depth(config)
    max_land_elevation = float(config.get("max_land_elevation_m", 55.0))
    grid_surface = np.where(
        grid_land,
        np.clip(grid_surface, 0.0, max_land_elevation),
        np.clip(grid_surface, -max_depth, 0.0),
    )
    finite = grid_valid & np.isfinite(grid_surface)
    if not np.any(finite):
        raise ValueError(f"{slug} has no valid terrain vertices")
    minimum = float(np.min(grid_surface[finite]))
    maximum = float(np.max(grid_surface[finite]))
    if maximum <= minimum:
        raise ValueError(f"{slug} has a constant terrain surface")
    scale = (maximum - minimum) / 65535.0
    encoded = np.rint((grid_surface - minimum) / scale)
    encoded = np.clip(encoded, 0, 65535).astype("<u2")
    encoded[~grid_valid] = 0
    (site_output / "height.bin").write_bytes(encoded.tobytes(order="C"))
    packed_mask = np.packbits(
        grid_valid.reshape(-1),
        bitorder="little",
    )
    (site_output / "valid-mask.bin").write_bytes(packed_mask.tobytes())
    packed_isobath_mask = np.packbits(
        grid_isobath_source.reshape(-1),
        bitorder="little",
    )
    (site_output / "isobath-mask.bin").write_bytes(
        packed_isobath_mask.tobytes()
    )
    decoded_surface = (
        minimum + encoded.astype(np.float32) * scale
    )
    vector_levels = tuple(
        range(5, int(max_depth // 5) * 5 + 1, 5)
    )
    if vector_levels:
        vector_payload, vector_diagnostics = extract_vector_isobaths(
            decoded_surface,
            grid_isobath_source & (decoded_surface < 0.0),
            vector_levels,
            source_kind="elevation",
        )
    else:
        vector_payload = {
            "coordinateSpace": "grid-pixels",
            "levels": {},
        }
        vector_diagnostics = validate_vector_isobath_payload(
            vector_payload,
            width=grid_size[0],
            height=grid_size[1],
        )
    vector_diagnostics = validate_vector_isobath_payload(
        vector_payload,
        width=grid_size[0],
        height=grid_size[1],
        depth=-decoded_surface,
        residual_tolerance_m=0.05,
    )
    if not vector_diagnostics["reprojectionResidualM"]["withinTolerance"]:
        maximum_residual = vector_diagnostics[
            "reprojectionResidualM"
        ]["max"]
        worst_sample = vector_diagnostics["worstResidualSample"]
        raise ValueError(
            f"{slug}: vector isobath reprojection residual "
            f"{maximum_residual:.6f} m exceeds 0.05 m "
            f"at {worst_sample}"
        )
    vector_path = site_output / "isobaths-vector.json"
    vector_path.write_text(
        json.dumps(
            vector_payload,
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )

    texture_size = fitted_dimensions(
        topographic_texture.width,
        topographic_texture.height,
        texture_max,
    )
    if topographic_texture.size != texture_size:
        topographic_texture = topographic_texture.resize(
            texture_size,
            Image.Resampling.LANCZOS,
        )
        orthophoto_texture = orthophoto_texture.resize(
            texture_size,
            Image.Resampling.LANCZOS,
        )
    topographic_texture.save(
        site_output / "topographic.webp",
        "WEBP",
        quality=90,
        method=6,
    )
    orthophoto_texture.save(
        site_output / "orthophoto.webp",
        "WEBP",
        quality=84,
        method=6,
    )

    source = open_raster(paths["focus_depth"], "focus depth raster")
    transform = source.GetGeoTransform()
    raster_west = float(transform[0])
    raster_north = float(transform[3])
    raster_east = raster_west + source.RasterXSize * float(transform[1])
    raster_south = raster_north + source.RasterYSize * float(transform[5])
    west, east = sorted((raster_west, raster_east))
    south, north = sorted((raster_south, raster_north))
    rotation_k = int(config.get("rotation_k", 0)) % 4
    view_bearing_deg = float(
        config.get("view_bearing_deg", default_view_bearing(rotation_k))
    ) % 360.0
    physical_width = east - west
    physical_depth = north - south
    if rotation_k % 2:
        physical_width, physical_depth = physical_depth, physical_width

    author = str(config.get("plate_author", "")).strip()
    year = int(config.get("copyright_year", 2026))
    license_name = str(config.get("map_license", "")).strip()
    copyright_text = f"© {year} {author}".strip()
    if license_name:
        copyright_text += f" · {license_name}"
    attribution_topographic = source_attribution(config, orthophoto=False)
    attribution_orthophoto = source_attribution(config, orthophoto=True)
    view_metadata = {
        "lookBearingDeg": view_bearing_deg,
        "gridLookBearingDeg": (
            view_bearing_deg - 90.0 * rotation_k
        ) % 360.0,
        "cameraTilt": float(config.get("camera_tilt", 0.34)),
        "alongViewProjectionScale": float(
            config.get("along_view_projection_scale", 1.0)
        ),
        "visibleWidthM": round(
            float(
                config.get(
                    "interactive_view_visible_width_m",
                    config.get("view_visible_width_m", physical_width),
                )
            ),
            6,
        ),
        "coastFrameFraction": round(
            (
                float(config.get("coast_frame_fraction", 0.44))
                - float(config.get("view_top_crop_fraction", 0.0))
            )
            / (
                1.0
                - float(config.get("view_top_crop_fraction", 0.0))
            ),
            4,
        ),
    }
    view_metadata.update(
        view_center_metadata(
            config,
            (west, south, east, north),
        )
    )
    metadata = {
        "schemaVersion": SCHEMA_VERSION,
        "slug": slug,
        "title": str(config.get("plate_title", config["title"])),
        "crs": str(region_manifest(config)["crs"]["code"]),
        "sourceBboxUtm40s": {
            "west": round(west, 3),
            "south": round(south, 3),
            "east": round(east, 3),
            "north": round(north, 3),
        },
        "physicalSizeM": {
            "width": round(physical_width, 3),
            "depth": round(physical_depth, 3),
        },
        "orientation": {
            "sourceRows": "north-to-south",
            "sourceColumns": "west-to-east",
            "rotationQuarterTurnsCounterClockwise": rotation_k,
            "textureUvOrigin": "northwest",
        },
        "grid": {
            "width": grid_size[0],
            "height": grid_size[1],
            "triangleCount": 2 * (grid_size[0] - 1) * (grid_size[1] - 1),
            "layout": "row-major",
            "rowOrder": "north-to-south",
            "columnOrder": "west-to-east",
            "heightFile": "height.bin",
            "heightEncoding": {
                "type": "uint16",
                "byteOrder": "little-endian",
                "offsetM": minimum,
                "scaleMPerUnit": scale,
                "formula": "elevationM = offsetM + rawUint16 * scaleMPerUnit",
            },
            "validMaskFile": "valid-mask.bin",
            "validMaskEncoding": {
                "type": "bitset",
                "bitOrder": "least-significant-bit-first",
                "formula": "(byte[index >> 3] >> (index & 7)) & 1",
            },
            "isobathMaskFile": "isobath-mask.bin",
            "isobathMaskEncoding": {
                "type": "bitset",
                "bitOrder": "least-significant-bit-first",
                "formula": "(byte[index >> 3] >> (index & 7)) & 1",
                "meaning": (
                    "1 = source-derived contour-safe vertex; "
                    "0 = deep-edge completion or transition buffer"
                ),
            },
            "vectorIsobathsFile": "isobaths-vector.json",
            "vectorIsobathsEncoding": {
                "coordinateSpace": "grid-pixels",
                "intervalM": 5,
                "outlineWidthCssPx": 4.8,
                "centreWidthCssPx": 2.6,
                "fragmentDepthBias": 0.0002,
            },
        },
        "elevationRangeM": {
            "min": minimum,
            "max": maximum,
        },
        "heightValues": "physical metres before vertical exaggeration",
        "interactiveExposure": float(
            config.get("interactive_exposure", DEFAULT_RELIEF_EXPOSURE)
        ),
        "bathymetryStyle": {
            "palette": str(config.get("bathymetry_palette", "legacy")),
            "depthScale": str(
                config.get(
                    "bathymetry_depth_scale",
                    "legacy_linear",
                )
            ),
            "isobathColorsRgb": {
                str(level): [
                    int(channel)
                    for channel in palette(
                        np.asarray([level], dtype=np.float32),
                        max_depth=max_depth,
                        scheme=str(
                            config.get("bathymetry_palette", "legacy")
                        ),
                        depth_scale=str(
                            config.get(
                                "bathymetry_depth_scale",
                                "legacy_linear",
                            )
                        ),
                    )[0]
                ]
                for level in vector_levels
                if level < max_depth - 0.001
            },
        },
        "vectorIsobaths": {
            "levels": vector_diagnostics["levels"],
            "totals": vector_diagnostics["totals"],
            "reprojectionResidualM": (
                vector_diagnostics["reprojectionResidualM"]
            ),
        },
        "verticalExaggeration": float(
            config.get("vertical_exaggeration", DEFAULT_VERTICAL_EXAGGERATION)
        ),
        "view": view_metadata,
        "textures": {
            "width": texture_size[0],
            "height": texture_size[1],
            "topographic": {
                "file": "topographic.webp",
                "attribution": attribution_topographic,
            },
            "orthophoto": {
                "file": "orthophoto.webp",
                "captureDate": str(config["orthophoto_capture_date"]),
                "attribution": attribution_orthophoto,
            },
        },
        "credits": {
            "copyright": copyright_text,
            "license": license_name,
            "requiredDisplay": f"{copyright_text} · {attribution_orthophoto}",
        },
    }
    if "interactive_footprint_utm40s" in config:
        footprint_center, footprint_width, footprint_depth, footprint_bearing = (
            interactive_footprint(config)
        )
        metadata["footprint"] = {
            "shape": "oriented-rectangle",
            "centerUtm40s": [
                round(footprint_center[0], 3),
                round(footprint_center[1], 3),
            ],
            "widthM": round(footprint_width, 3),
            "depthM": round(footprint_depth, 3),
            "lookBearingDeg": round(footprint_bearing, 3),
            "cornersUtm40s": [
                [round(easting, 3), round(northing, 3)]
                for easting, northing in interactive_footprint_corners(config)
            ],
        }
    metadata_path = site_output / "terrain.json"
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    build_fused_surface.cache_clear()
    del surface, depth, elevation, land_mask, land_weight, valid
    gc.collect()
    return {
        "slug": slug,
        "title": metadata["title"],
        "metadata": f"{slug}/terrain.json",
        "files": {
            "metadata": artifact_record(metadata_path, output_root),
            "height": artifact_record(site_output / "height.bin", output_root),
            "validMask": artifact_record(
                site_output / "valid-mask.bin",
                output_root,
            ),
            "isobathMask": artifact_record(
                site_output / "isobath-mask.bin",
                output_root,
            ),
            "vectorIsobaths": artifact_record(
                vector_path,
                output_root,
            ),
            "topographicTexture": artifact_record(
                site_output / "topographic.webp",
                output_root,
            ),
            "orthophotoTexture": artifact_record(
                site_output / "orthophoto.webp",
                output_root,
            ),
        },
    }


def export_site(
    config_path: Path,
    output_root: Path,
    grid_max: int,
    texture_max: int,
) -> dict[str, Any]:
    config = load_config(config_path)
    if not config.get("orthophoto_enabled", False):
        raise ValueError(f"{config['slug']} does not provide an orthophoto")
    paths = paths_for(config)
    uses_context = (
        "interactive_bbox_utm40s" in config
        or "interactive_footprint_utm40s" in config
    )
    required_keys = (
        ("context_depth", "context_elevation", "context_orthophoto")
        if uses_context
        else ("focus_depth", "focus_elevation", "focus_orthophoto")
    )
    for key in required_keys:
        if not paths[key].is_file():
            raise FileNotFoundError(f"Missing cached {key}: {paths[key]}")

    with interactive_source_paths(config, paths) as source_paths:
        return _export_site_from_paths(
            config,
            source_paths,
            output_root,
            grid_max,
            texture_max,
        )


def validate_export(output_root: Path, manifest: dict[str, Any]) -> None:
    for item in manifest["sites"]:
        for record in item["files"].values():
            artifact_path = output_root / record["path"]
            if artifact_path.stat().st_size != int(record["bytes"]):
                raise ValueError(f"Unexpected artifact size: {artifact_path}")
            if sha256(artifact_path) != record["sha256"]:
                raise ValueError(f"Unexpected artifact digest: {artifact_path}")
        metadata_path = output_root / item["metadata"]
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        grid = metadata["grid"]
        grid_width = int(grid["width"])
        grid_height = int(grid["height"])
        if min(grid_width, grid_height) < 2 or max(
            grid_width,
            grid_height,
        ) > DEFAULT_GRID_MAX:
            raise ValueError(
                "Heightfield dimensions exceed the interactive terrain "
                f"contract: {metadata_path}"
            )
        vertex_count = grid_width * grid_height
        height_path = metadata_path.parent / grid["heightFile"]
        mask_path = metadata_path.parent / grid["validMaskFile"]
        isobath_mask_path = metadata_path.parent / grid["isobathMaskFile"]
        vector_isobaths_path = (
            metadata_path.parent / grid["vectorIsobathsFile"]
        )
        if (
            vector_isobaths_path.stat().st_size
            > DEFAULT_VECTOR_ISOBATH_MAX_BYTES
        ):
            raise ValueError(
                "Vector isobath payload exceeds the mobile payload contract: "
                f"{vector_isobaths_path}"
            )
        if height_path.stat().st_size != vertex_count * 2:
            raise ValueError(f"Unexpected height payload size: {height_path}")
        if mask_path.stat().st_size != (vertex_count + 7) // 8:
            raise ValueError(f"Unexpected validity payload size: {mask_path}")
        if isobath_mask_path.stat().st_size != (vertex_count + 7) // 8:
            raise ValueError(
                f"Unexpected isobath mask payload size: {isobath_mask_path}"
            )
        vector_payload = json.loads(
            vector_isobaths_path.read_text(encoding="utf-8")
        )
        vector_diagnostics = validate_vector_isobath_payload(
            vector_payload,
            width=grid_width,
            height=grid_height,
        )
        vector_totals = vector_diagnostics["totals"]
        if (
            int(vector_totals["polylines"])
            > DEFAULT_VECTOR_ISOBATH_MAX_POLYLINES
        ):
            raise ValueError(
                "Vector isobath payload exceeds the mobile polyline "
                f"contract: {vector_isobaths_path}"
            )
        if int(vector_totals["points"]) > DEFAULT_VECTOR_ISOBATH_MAX_POINTS:
            raise ValueError(
                "Vector isobath payload exceeds the mobile point "
                f"contract: {vector_isobaths_path}"
            )
        textures = metadata["textures"]
        if max(int(textures["width"]), int(textures["height"])) > DEFAULT_TEXTURE_MAX:
            raise ValueError(f"Texture exceeds the mobile payload contract: {metadata_path}")
        for style in ("topographic", "orthophoto"):
            texture_path = metadata_path.parent / textures[style]["file"]
            with Image.open(texture_path) as image:
                if image.size != (int(textures["width"]), int(textures["height"])):
                    raise ValueError(f"Texture dimensions do not match metadata: {texture_path}")


def swap_output(build_root: Path, output_root: Path) -> None:
    previous_root = build_root.parent / "previous"
    if output_root.exists():
        output_root.rename(previous_root)
    try:
        build_root.rename(output_root)
    except Exception:
        if previous_root.exists():
            previous_root.rename(output_root)
        raise
    if previous_root.exists():
        shutil.rmtree(previous_root)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Export compact heightfields and matched map textures for the "
            "canonical interactive terrain package."
        )
    )
    parser.add_argument(
        "configs",
        nargs="*",
        type=Path,
        help=(
            "Site JSON files forming the complete package "
            "(defaults to every regions/reunion/sites/*.json file)"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Asset directory (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--grid-max",
        type=int,
        default=DEFAULT_GRID_MAX,
        help=f"Maximum heightfield dimension (default: {DEFAULT_GRID_MAX})",
    )
    parser.add_argument(
        "--texture-max",
        type=int,
        default=DEFAULT_TEXTURE_MAX,
        help="Maximum texture dimension (default: 2048)",
    )
    args = parser.parse_args()
    if not 3 <= args.grid_max <= DEFAULT_GRID_MAX:
        parser.error(f"--grid-max must be between 3 and {DEFAULT_GRID_MAX}")
    if not 256 <= args.texture_max <= DEFAULT_TEXTURE_MAX:
        parser.error(f"--texture-max must be between 256 and {DEFAULT_TEXTURE_MAX}")

    configs = args.configs or sorted(DEFAULT_CONFIG_DIRECTORY.glob("*.json"))
    if not configs:
        parser.error("No site configurations found")
    output_root = args.output.expanduser().resolve()
    output_root.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".interactive-terrain-build-",
        dir=output_root.parent,
    ) as temporary_directory:
        build_root = Path(temporary_directory) / "interactive-terrain"
        build_root.mkdir()
        sites = [
            export_site(
                path.expanduser().resolve(),
                build_root,
                args.grid_max,
                args.texture_max,
            )
            for path in configs
        ]
        manifest = {
            "schemaVersion": SCHEMA_VERSION,
            "sites": sites,
        }
        (build_root / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        validate_export(build_root, manifest)
        swap_output(build_root, output_root)
    for item in sites:
        print(output_root / item["metadata"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
