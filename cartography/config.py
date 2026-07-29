from __future__ import annotations

import json
import math
import re
from datetime import date
from pathlib import Path
from typing import Any, Mapping, Sequence

from cartography.bathymetry_style import (
    BATHYMETRY_DEPTH_SCALES,
    BATHYMETRY_PALETTES_RGB,
)


ROOT = Path(__file__).resolve().parents[1]
REGIONS_ROOT = ROOT / "regions"
DEFAULT_REGION_SLUG = "reunion"
DEFAULT_CACHE = ROOT / ".tmp" / "bathy-renders"
DEFAULT_VERTICAL_EXAGGERATION = 3.9935327405
DEFAULT_RELIEF_EXPOSURE = 1.55

_SLUG_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")

_PATH_KEYS = frozenset(
    {
        "context_depth_raw",
        "context_depth",
        "context_elevation",
        "context_orthophoto",
        "focus_depth",
        "focus_elevation",
        "focus_orthophoto",
        "locator_elevation",
        "locator_bathymetry",
        "output_2d",
        "output_2d_ortho",
        "output_3d",
        "output_3d_ortho",
        "output_locator",
        "output_plate",
        "output_plate_topography",
    }
)

# Keep this list explicit. Configuration is user-authored and a misspelled key
# should fail before any network request or multi-minute render starts.
_ALLOWED_KEYS = frozenset(
    {
        "along_view_projection_scale",
        "bathymetry_depth_scale",
        "bathymetry_palette",
        "bridge_decks",
        "cache_dir",
        "camera_tilt",
        "clip_rotated_outside",
        "coast_frame_fraction",
        "coast_mode",
        "coastline_visible",
        "context_bbox_utm40s",
        "context_topography_resolution_m",
        "copyright_year",
        "deep_edge_nodata_terrain_fill",
        "deep_edge_nodata_terrain_min_depth_m",
        "east_crop_fraction",
        "final_output_size_px",
        "focus_bbox_utm40s",
        "horizon_cleanup_fraction",
        "horizontal_crop_fraction",
        "hyscores_directory",
        "hyscores_tiff_url",
        "imagery_sea_depth_m",
        "imagery_sea_feather_m",
        "imagery_sea_full_depth_m",
        "imagery_sea_max_depth_m",
        "imagery_sea_smoothing_m",
        "interactive_bbox_utm40s",
        "interactive_footprint_utm40s",
        "interactive_exposure",
        "interactive_match_static_along_center",
        "interactive_match_static_horizontal_center",
        "interactive_max_depth_m",
        "interactive_view_along_center_offset_m",
        "interactive_view_visible_width_m",
        "land_sieve_threshold_px",
        "litto3d_archives",
        "litto3d_archive_members",
        "litto3d_archive_url",
        "locator_bathymetry_enabled",
        "locator_bbox_utm40s",
        "locator_gebco_attribution",
        "locator_gebco_blur_px",
        "locator_gebco_layer",
        "locator_gebco_request_width_px",
        "locator_gebco_wms_url",
        "locator_label",
        "locator_map_enabled",
        "locator_marker_utm40s",
        "site_location_utm40s",
        "locator_output_width_px",
        "locator_resolution_m",
        "map_license",
        "map_style_scale",
        "max_depth_m",
        "max_land_elevation_m",
        "nearshore_smoothing_bbox_utm40s",
        "nearshore_smoothing_distance_m",
        "nearshore_land_hole_fill_max_area_m2",
        "nearshore_smoothing_passes",
        "nearshore_smoothing_radius_m",
        "north_south_projection_scale",
        "orthophoto_3d_resolution_m",
        "orthophoto_capture_date",
        "orthophoto_coastline_visible",
        "orthophoto_enabled",
        "orthophoto_layer",
        "orthophoto_resolution_m",
        "output_scale",
        "paths",
        "plan_open_label_offsets_px",
        "plan_land_shading",
        "plan_output_scale",
        "plan_sea_shading",
        "plate_author",
        "plate_canvas_height_px",
        "plate_canvas_width_px",
        "plate_city",
        "plate_site_name",
        "plate_title",
        "plan_max_depth_m",
        "relief_edge_margin_px",
        "relief_output_scale",
        "relief_hemisphere_intensity",
        "relief_exposure",
        "relief_compass_inset_px",
        "relief_footer_inset_px",
        "relief_label_edge_inset_px",
        "relief_surface_draped_contours",
        "relief_surface_draped_zero_contour",
        "relief_surface_contour_supersampling",
        "relief_key_light_bearing_deg",
        "relief_key_light_elevation_deg",
        "relief_key_light_intensity",
        "relief_mesh_gap_fill_max_area_m2",
        "relief_normal_sample_spacing_m",
        "relief_texture_triangle_min_area_px",
        "relief_suppressed_label_levels",
        "region",
        "rotation_k",
        "slug",
        "south_crop_fraction",
        "title",
        "topography_resolution_m",
        "vertical_exaggeration",
        "view_bearing_deg",
        "view_canvas_height_px",
        "view_canvas_width_px",
        "view_center_offset_east_m",
        "view_center_offset_north_m",
        "view_crop_depth_m",
        "view_crop_width_m",
        "view_left_crop_fraction",
        "view_right_crop_fraction",
        "view_top_crop_fraction",
        "view_visible_width_m",
        "west_crop_fraction",
    }
)

_OLD_CROP_KEYS = frozenset(
    {
        "horizontal_crop_fraction",
        "east_crop_fraction",
        "west_crop_fraction",
        "south_crop_fraction",
    }
)
_NEW_CROP_KEYS = frozenset(
    {
        "view_left_crop_fraction",
        "view_right_crop_fraction",
        "view_top_crop_fraction",
    }
)
_BOOLEAN_KEYS = frozenset(
    {
        "clip_rotated_outside",
        "coastline_visible",
        "deep_edge_nodata_terrain_fill",
        "interactive_match_static_along_center",
        "interactive_match_static_horizontal_center",
        "locator_bathymetry_enabled",
        "locator_map_enabled",
        "orthophoto_coastline_visible",
        "orthophoto_enabled",
        "relief_surface_draped_contours",
        "relief_surface_draped_zero_contour",
    }
)


def region_slug(config: Mapping[str, Any]) -> str:
    value = config.get("region", DEFAULT_REGION_SLUG)
    if not isinstance(value, str) or not _SLUG_PATTERN.fullmatch(value):
        raise ValueError(
            "region must use lowercase letters, digits, and single hyphens"
        )
    return value


def region_directory(config: Mapping[str, Any]) -> Path:
    return REGIONS_ROOT / region_slug(config)


def region_manifest(config: Mapping[str, Any]) -> dict[str, Any]:
    path = region_directory(config) / "region.json"
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ValueError(f"Missing region manifest: {path}") from error
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Invalid region manifest: {path}") from error
    if not isinstance(manifest, dict):
        raise ValueError(f"Invalid region manifest: {path}")
    if manifest.get("slug") != region_slug(config):
        raise ValueError(
            f"Region manifest slug does not match configuration: {path}"
        )
    return manifest


def region_site_config_directory(config: Mapping[str, Any]) -> Path:
    manifest = region_manifest(config)
    raw = manifest.get("pipeline", {}).get("siteConfigDirectory")
    if not isinstance(raw, str) or not raw:
        raise ValueError("Region manifest is missing pipeline.siteConfigDirectory")
    return as_path(raw, region_directory(config) / "sites")


def region_output_directory(config: Mapping[str, Any]) -> Path:
    manifest = region_manifest(config)
    raw = manifest.get("pipeline", {}).get("outputDirectory")
    if not isinstance(raw, str) or not raw:
        raise ValueError("Region manifest is missing pipeline.outputDirectory")
    return as_path(raw, region_directory(config) / "outputs")


def as_path(value: str | None, default: Path) -> Path:
    path = Path(value).expanduser() if value else default
    return path if path.is_absolute() else ROOT / path


def bbox(config: Mapping[str, Any], key: str) -> tuple[float, float, float, float]:
    if key not in config:
        raise ValueError(f"Missing required configuration key: {key}")
    raw = config[key]
    if isinstance(raw, (str, bytes)) or not isinstance(raw, Sequence) or len(raw) != 4:
        raise ValueError(f"{key} must contain [min_x, min_y, max_x, max_y]")
    try:
        values = tuple(float(value) for value in raw)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{key} must contain four finite numbers") from error
    if not all(math.isfinite(value) for value in values):
        raise ValueError(f"{key} must contain four finite numbers")
    min_x, min_y, max_x, max_y = values
    if min_x >= max_x or min_y >= max_y:
        raise ValueError(f"Invalid {key}: {values}")
    return values


def contains(
    outer: tuple[float, float, float, float],
    inner: tuple[float, float, float, float],
) -> bool:
    return (
        outer[0] <= inner[0]
        and outer[1] <= inner[1]
        and outer[2] >= inner[2]
        and outer[3] >= inner[3]
    )


def paths_for(config: Mapping[str, Any]) -> dict[str, Path]:
    slug = str(config["slug"])
    output_root = region_output_directory(config)
    cache_value = config.get("cache_dir")
    if cache_value is not None and not isinstance(cache_value, str):
        raise ValueError("cache_dir must be a path string")
    cache = as_path(cache_value, DEFAULT_CACHE)
    raw_overrides = config.get("paths", {})
    if not isinstance(raw_overrides, Mapping):
        raise ValueError("paths must be an object")
    overrides = dict(raw_overrides)
    unknown_paths = sorted(set(overrides) - _PATH_KEYS)
    if unknown_paths:
        raise ValueError(f"Unknown path key(s): {', '.join(unknown_paths)}")
    for key, value in overrides.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"paths.{key} must be a non-empty path string")

    defaults = {
        "context_depth_raw": cache / f"{slug}-context-depth.tif",
        "context_depth": cache / f"{slug}-context-depth-positive.tif",
        "context_elevation": cache / f"{slug}-context-elevation.tif",
        "context_orthophoto": cache / f"{slug}-context-orthophoto.tif",
        "focus_depth": cache / f"{slug}-focus-depth-positive.tif",
        "focus_elevation": cache / f"{slug}-focus-elevation.tif",
        "focus_orthophoto": cache / f"{slug}-focus-orthophoto.tif",
        "locator_elevation": cache / f"{region_slug(config)}-locator-elevation.tif",
        "locator_bathymetry": cache
        / f"{region_slug(config)}-locator-gebco-relief.tif",
        "output_2d": output_root / f"{slug}-topobathy-2d.jpg",
        "output_2d_ortho": output_root / f"{slug}-topobathy-2d-ortho.jpg",
        "output_3d": output_root / f"{slug}-topobathy-3d.jpg",
        "output_3d_ortho": output_root / f"{slug}-topobathy-3d-ortho.jpg",
        "output_locator": output_root / f"{slug}-locator-{region_slug(config)}.jpg",
        "output_plate": output_root / f"{slug}-planche.jpg",
        "output_plate_topography": output_root
        / f"{slug}-planche-topographique.jpg",
    }
    return {
        key: as_path(overrides.get(key), default)
        for key, default in defaults.items()
    }


def _number(config: Mapping[str, Any], key: str, default: float | None = None) -> float:
    if key not in config:
        if default is None:
            raise ValueError(f"Missing required configuration key: {key}")
        return default
    value = config[key]
    if isinstance(value, bool):
        raise ValueError(f"{key} must be a finite number")
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{key} must be a finite number") from error
    if not math.isfinite(number):
        raise ValueError(f"{key} must be a finite number")
    return number


def _positive(config: Mapping[str, Any], key: str, default: float | None = None) -> float:
    value = _number(config, key, default)
    if value <= 0.0:
        raise ValueError(f"{key} must be positive")
    return value


def _fraction(
    config: Mapping[str, Any],
    key: str,
    default: float = 0.0,
    *,
    upper: float = 1.0,
) -> float:
    value = _number(config, key, default)
    if not 0.0 <= value < upper:
        raise ValueError(f"{key} must be between 0 (inclusive) and {upper} (exclusive)")
    return value


def _positive_int(config: Mapping[str, Any], key: str) -> None:
    if key not in config:
        return
    value = config[key]
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{key} must be a positive integer")


def _pair(
    value: Any,
    key: str,
    *,
    positive: bool = False,
) -> tuple[float, float]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence) or len(value) != 2:
        raise ValueError(f"{key} must contain two numbers")
    try:
        pair = float(value[0]), float(value[1])
    except (TypeError, ValueError) as error:
        raise ValueError(f"{key} must contain two finite numbers") from error
    if not all(math.isfinite(item) for item in pair):
        raise ValueError(f"{key} must contain two finite numbers")
    if positive and not all(item > 0.0 for item in pair):
        raise ValueError(f"{key} values must be positive")
    return pair


def interactive_footprint(
    config: Mapping[str, Any],
) -> tuple[tuple[float, float], float, float, float]:
    """Return the oriented interactive footprint.

    Width runs across the camera view, approximately along the coastline.
    Depth follows the configured look bearing from sea toward land.
    """
    key = "interactive_footprint_utm40s"
    if key not in config:
        raise ValueError(f"Missing required configuration key: {key}")
    raw = config[key]
    if not isinstance(raw, Mapping):
        raise ValueError(f"{key} must be an object")
    allowed = {"center", "width_m", "depth_m", "look_bearing_deg"}
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise ValueError(
            f"Unknown {key} key(s): {', '.join(unknown)}"
        )
    missing = sorted(allowed - set(raw))
    if missing:
        raise ValueError(
            f"{key} requires {', '.join(missing)}"
        )
    center = _pair(raw["center"], f"{key}.center")
    width = _positive(raw, "width_m")
    depth = _positive(raw, "depth_m")
    bearing = _number(raw, "look_bearing_deg")
    if not 0.0 <= bearing < 360.0:
        raise ValueError(
            f"{key}.look_bearing_deg must be between 0 and 360 degrees"
        )
    return center, width, depth, bearing


def interactive_footprint_corners(
    config: Mapping[str, Any],
) -> tuple[tuple[float, float], ...]:
    center, width, depth, bearing_deg = interactive_footprint(config)
    bearing = math.radians(bearing_deg)
    forward = (math.sin(bearing), math.cos(bearing))
    screen_right = (math.cos(bearing), -math.sin(bearing))
    corners: list[tuple[float, float]] = []
    for width_sign, depth_sign in (
        (-1.0, -1.0),
        (1.0, -1.0),
        (1.0, 1.0),
        (-1.0, 1.0),
    ):
        corners.append(
            (
                center[0]
                + width_sign * width * 0.5 * screen_right[0]
                + depth_sign * depth * 0.5 * forward[0],
                center[1]
                + width_sign * width * 0.5 * screen_right[1]
                + depth_sign * depth * 0.5 * forward[1],
            )
        )
    return tuple(corners)


def interactive_footprint_bounds(
    config: Mapping[str, Any],
) -> tuple[float, float, float, float]:
    corners = interactive_footprint_corners(config)
    eastings = [point[0] for point in corners]
    northings = [point[1] for point in corners]
    return (
        min(eastings),
        min(northings),
        max(eastings),
        max(northings),
    )


def _point_in_box(point: tuple[float, float], extent: tuple[float, float, float, float]) -> bool:
    return extent[0] <= point[0] <= extent[2] and extent[1] <= point[1] <= extent[3]


def _validate_wms_grid(
    extent: tuple[float, float, float, float],
    resolution: float,
    description: str,
    *,
    allow_tiling: bool = False,
) -> None:
    width = int(round((extent[2] - extent[0]) / resolution))
    height = int(round((extent[3] - extent[1]) / resolution))
    if width <= 0 or height <= 0:
        raise ValueError(f"{description} has no pixels at {resolution:g} m resolution")
    if not allow_tiling and (width > 5000 or height > 5000):
        raise ValueError(
            f"{description} would request {width} x {height} pixels; "
            "the WMS limit is 5000 pixels per axis"
        )


def _non_empty_string(config: Mapping[str, Any], key: str, *, required: bool = False) -> None:
    if key not in config:
        if required:
            raise ValueError(f"Missing required configuration key: {key}")
        return
    value = config[key]
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")


def _validate_crop_aliases(config: Mapping[str, Any]) -> None:
    old_present = _OLD_CROP_KEYS.intersection(config)
    new_present = _NEW_CROP_KEYS.intersection(config)
    if old_present and new_present:
        raise ValueError(
            "Do not mix legacy crop keys "
            f"({', '.join(sorted(old_present))}) with new view crop keys "
            f"({', '.join(sorted(new_present))})"
        )

    if new_present:
        left = _fraction(config, "view_left_crop_fraction")
        right = _fraction(config, "view_right_crop_fraction")
        _fraction(config, "view_top_crop_fraction")
    else:
        horizontal = _fraction(config, "horizontal_crop_fraction", upper=0.5)
        left = _fraction(config, "east_crop_fraction", horizontal)
        right = _fraction(config, "west_crop_fraction", horizontal)
        _fraction(config, "south_crop_fraction")
    if left + right >= 1.0:
        raise ValueError("Left and right crop fractions must retain a positive view width")


def _validate_bridges(config: Mapping[str, Any], context: tuple[float, float, float, float]) -> None:
    if "bridge_decks" not in config:
        return
    bridges = config["bridge_decks"]
    if not isinstance(bridges, list):
        raise ValueError("bridge_decks must be a list")
    allowed = {"start_utm40s", "end_utm40s", "half_width_m", "feather_m"}
    for index, bridge in enumerate(bridges):
        key = f"bridge_decks[{index}]"
        if not isinstance(bridge, Mapping):
            raise ValueError(f"{key} must be an object")
        unknown = sorted(set(bridge) - allowed)
        if unknown:
            raise ValueError(f"Unknown {key} key(s): {', '.join(unknown)}")
        if "start_utm40s" not in bridge or "end_utm40s" not in bridge:
            raise ValueError(f"{key} requires start_utm40s and end_utm40s")
        start = _pair(bridge["start_utm40s"], f"{key}.start_utm40s")
        end = _pair(bridge["end_utm40s"], f"{key}.end_utm40s")
        if start == end:
            raise ValueError(f"{key} endpoints must be distinct")
        if not _point_in_box(start, context) or not _point_in_box(end, context):
            raise ValueError(f"{key} endpoints must lie within context_bbox_utm40s")
        for field, default in (("half_width_m", 5.0), ("feather_m", 2.0)):
            raw = bridge.get(field, default)
            if isinstance(raw, bool):
                raise ValueError(f"{key}.{field} must be positive")
            try:
                value = float(raw)
            except (TypeError, ValueError) as error:
                raise ValueError(f"{key}.{field} must be positive") from error
            if not math.isfinite(value) or value <= 0.0:
                raise ValueError(f"{key}.{field} must be positive")


def validate_config(config: Mapping[str, Any]) -> None:
    if not isinstance(config, Mapping):
        raise ValueError("Site configuration must be an object")

    unknown = sorted(set(config) - _ALLOWED_KEYS)
    if unknown:
        raise ValueError(f"Unknown configuration key(s): {', '.join(unknown)}")
    manifest = region_manifest(config)
    for key in _BOOLEAN_KEYS.intersection(config):
        if not isinstance(config[key], bool):
            raise ValueError(f"{key} must be true or false")

    for key in ("slug", "title", "plate_site_name", "plate_city"):
        _non_empty_string(config, key, required=True)
    slug = str(config["slug"])
    if not _SLUG_PATTERN.fullmatch(slug):
        raise ValueError("slug must use lowercase letters, digits, and single hyphens")

    plate_site_name = str(config["plate_site_name"]).strip()
    forbidden_name_separators = (",", "·", "/", "|", " - ", " & ")
    if any(separator in plate_site_name for separator in forbidden_name_separators):
        raise ValueError(
            "plate_site_name must contain one canonical site name only, "
            "without aliases or location separators"
        )
    folded_site_name = plate_site_name.casefold()
    region_names = manifest.get("names", {})
    forbidden_region_names = {
        str(value).casefold()
        for value in region_names.values()
        if isinstance(value, str) and value.strip()
    }
    if any(name in folded_site_name for name in forbidden_region_names):
        raise ValueError(
            "plate_site_name must not contain the region name; "
            "the region is rendered on its own line"
        )

    plate_city = str(config["plate_city"]).strip()
    if any(separator in plate_city for separator in (",", "·", "/", "|")):
        raise ValueError(
            "plate_city must contain the municipality only, without region or island"
        )
    folded_city = plate_city.casefold()
    if any(name in folded_city for name in forbidden_region_names):
        raise ValueError(
            "plate_city must not contain the region name; "
            "the region is rendered on its own line"
        )

    region = region_slug(config)
    if region != "reunion":
        raise ValueError(
            f"Region {region!r} has no configured source validation contract"
        )
    _non_empty_string(config, "hyscores_tiff_url", required=True)
    if "hyscores_directory" in config:
        _non_empty_string(config, "hyscores_directory")

    for key in ("plate_author", "plate_title", "map_license"):
        if key in config:
            _non_empty_string(config, key)

    palette_name = str(config.get("bathymetry_palette", "legacy"))
    if palette_name not in BATHYMETRY_PALETTES_RGB:
        raise ValueError(f"Unsupported bathymetry_palette: {palette_name}")
    depth_scale = str(
        config.get("bathymetry_depth_scale", "legacy_linear")
    )
    if depth_scale not in BATHYMETRY_DEPTH_SCALES:
        raise ValueError(f"Unsupported bathymetry_depth_scale: {depth_scale}")
    plan_sea_shading = str(
        config.get("plan_sea_shading", "directional")
    )
    if plan_sea_shading not in {"directional", "local_slope", "none"}:
        raise ValueError(f"Unsupported plan_sea_shading: {plan_sea_shading}")
    plan_land_shading = str(config.get("plan_land_shading", "none"))
    if plan_land_shading not in {"local_slope", "none"}:
        raise ValueError(f"Unsupported plan_land_shading: {plan_land_shading}")

    focus = bbox(config, "focus_bbox_utm40s")
    context = bbox(config, "context_bbox_utm40s")
    if not contains(context, focus):
        raise ValueError("context_bbox_utm40s must contain focus_bbox_utm40s")
    if "nearshore_smoothing_bbox_utm40s" in config:
        smoothing_bbox = bbox(config, "nearshore_smoothing_bbox_utm40s")
        if not contains(context, smoothing_bbox):
            raise ValueError(
                "context_bbox_utm40s must contain "
                "nearshore_smoothing_bbox_utm40s"
            )
        for key in (
            "nearshore_land_hole_fill_max_area_m2",
            "nearshore_smoothing_distance_m",
            "nearshore_smoothing_radius_m",
        ):
            if _number(config, key) <= 0.0:
                raise ValueError(f"{key} must be positive")
        smoothing_passes = config.get("nearshore_smoothing_passes", 1)
        if (
            isinstance(smoothing_passes, bool)
            or not isinstance(smoothing_passes, int)
            or smoothing_passes < 1
            or smoothing_passes > 8
        ):
            raise ValueError(
                "nearshore_smoothing_passes must be an integer from 1 to 8"
            )
    if "interactive_bbox_utm40s" in config:
        interactive = bbox(config, "interactive_bbox_utm40s")
        if not contains(context, interactive):
            raise ValueError(
                "context_bbox_utm40s must contain interactive_bbox_utm40s"
            )
    if (
        "interactive_bbox_utm40s" in config
        and "interactive_footprint_utm40s" in config
    ):
        raise ValueError(
            "Use either interactive_bbox_utm40s or "
            "interactive_footprint_utm40s, not both"
        )
    if "interactive_footprint_utm40s" in config:
        interactive = interactive_footprint_bounds(config)
        if not contains(context, interactive):
            raise ValueError(
                "context_bbox_utm40s must contain "
                "interactive_footprint_utm40s"
            )

    max_depth = _number(config, "max_depth_m", 20.0)
    maximum_depth = 40.0 if region == "reunion" else 60.0
    if not 0.0 < max_depth <= maximum_depth:
        raise ValueError(
            "max_depth_m must be greater than 0 and at most "
            f"{maximum_depth:g} for region {region}"
        )
    if "plan_max_depth_m" in config:
        plan_max_depth = _number(config, "plan_max_depth_m")
        if not 0.0 < plan_max_depth <= max_depth:
            raise ValueError(
                "plan_max_depth_m must be greater than 0 and at most max_depth_m"
            )
    interactive_max_depth = max_depth
    if "interactive_max_depth_m" in config:
        interactive_max_depth = _number(config, "interactive_max_depth_m")
        if not 0.0 < interactive_max_depth <= max_depth:
            raise ValueError(
                "interactive_max_depth_m must be greater than 0 and at most max_depth_m"
            )
    if "deep_edge_nodata_terrain_min_depth_m" in config:
        minimum_fill_depth = _number(
            config,
            "deep_edge_nodata_terrain_min_depth_m",
        )
        if not config.get("deep_edge_nodata_terrain_fill", False):
            raise ValueError(
                "deep_edge_nodata_terrain_min_depth_m requires "
                "deep_edge_nodata_terrain_fill"
            )
        if not 0.0 < minimum_fill_depth <= interactive_max_depth:
            raise ValueError(
                "deep_edge_nodata_terrain_min_depth_m must be greater than 0 "
                "and at most the effective interactive depth"
            )
    coast_mode = config.get("coast_mode", "profile")
    if not isinstance(coast_mode, str):
        raise ValueError("coast_mode must be 'profile' or 'mask'")
    if coast_mode not in {"profile", "mask"}:
        raise ValueError("coast_mode must be 'profile' or 'mask'")

    for key, default in (
        ("topography_resolution_m", 0.5),
        ("output_scale", 1.0),
        ("map_style_scale", 2.0),
        ("camera_tilt", 0.34),
        ("vertical_exaggeration", DEFAULT_VERTICAL_EXAGGERATION),
        ("max_land_elevation_m", 55.0),
    ):
        _positive(config, key, default)
    for key in (
        "context_topography_resolution_m",
        "orthophoto_resolution_m",
        "orthophoto_3d_resolution_m",
        "locator_resolution_m",
        "plan_output_scale",
        "relief_output_scale",
        "view_crop_width_m",
        "view_crop_depth_m",
        "view_visible_width_m",
        "interactive_view_visible_width_m",
        "interactive_exposure",
        "relief_hemisphere_intensity",
        "relief_exposure",
        "relief_compass_inset_px",
        "relief_footer_inset_px",
        "relief_label_edge_inset_px",
        "relief_key_light_intensity",
        "relief_mesh_gap_fill_max_area_m2",
        "relief_normal_sample_spacing_m",
        "relief_texture_triangle_min_area_px",
    ):
        if key in config:
            _positive(config, key)
    if "interactive_view_along_center_offset_m" in config:
        _number(config, "interactive_view_along_center_offset_m")
    if (
        "relief_edge_margin_px" in config
        and _number(config, "relief_edge_margin_px") < 0.0
    ):
        raise ValueError("relief_edge_margin_px must be non-negative")
    for key in ("view_center_offset_east_m", "view_center_offset_north_m"):
        if key in config:
            _number(config, key)

    old_axis = "north_south_projection_scale" in config
    new_axis = "along_view_projection_scale" in config
    if old_axis and new_axis:
        raise ValueError(
            "Do not mix north_south_projection_scale with along_view_projection_scale"
        )
    if old_axis:
        _positive(config, "north_south_projection_scale")
    if new_axis:
        _positive(config, "along_view_projection_scale")

    if "interactive_footprint_utm40s" in config:
        _, footprint_width, footprint_depth, footprint_bearing = (
            interactive_footprint(config)
        )
        visible_width = _positive(
            config,
            "interactive_view_visible_width_m",
            _positive(config, "view_visible_width_m"),
        )
        view_bearing = _number(
            config,
            "view_bearing_deg",
            float(config.get("rotation_k", 0)) * 90.0 + 180.0,
        ) % 360.0
        bearing_delta = abs(
            (footprint_bearing - view_bearing + 180.0) % 360.0 - 180.0
        )
        if bearing_delta > 1e-6:
            raise ValueError(
                "interactive_footprint_utm40s.look_bearing_deg must match "
                "view_bearing_deg"
            )
        final_size = config.get("final_output_size_px", [2474, 1712])
        canvas_width, canvas_height = _pair(
            final_size,
            "final_output_size_px",
            positive=True,
        )
        aspect = canvas_width / canvas_height
        projection_slope = (
            _positive(config, "camera_tilt", 0.34)
            * _positive(config, "along_view_projection_scale", 1.0)
        )
        minimum_width = visible_width * 1.15
        minimum_depth = (
            visible_width / (aspect * projection_slope) * 1.20
        )
        if footprint_width + 1e-6 < minimum_width:
            raise ValueError(
                "interactive_footprint_utm40s.width_m must be at least "
                "1.15 times view_visible_width_m"
            )
        if footprint_depth + 1e-6 < minimum_depth:
            raise ValueError(
                "interactive_footprint_utm40s.depth_m is too short for "
                "the canonical initial camera view"
            )

    focus_resolution = _number(config, "topography_resolution_m", 0.5)
    context_resolution = _number(
        config,
        "context_topography_resolution_m",
        focus_resolution,
    )
    _validate_wms_grid(context, context_resolution, "context RGE ALTI request")
    if abs(focus_resolution - context_resolution) > 1e-9:
        _validate_wms_grid(focus, focus_resolution, "focus RGE ALTI request")

    _validate_crop_aliases(config)
    _fraction(config, "coast_frame_fraction", 0.44)
    if "horizon_cleanup_fraction" in config:
        _fraction(config, "horizon_cleanup_fraction", upper=0.25)

    for key in (
        "view_canvas_width_px",
        "view_canvas_height_px",
        "locator_output_width_px",
        "locator_gebco_request_width_px",
        "plate_canvas_width_px",
        "plate_canvas_height_px",
        "land_sieve_threshold_px",
        "copyright_year",
        "relief_surface_contour_supersampling",
    ):
        _positive_int(config, key)
    if int(config.get("relief_surface_contour_supersampling", 1)) > 4:
        raise ValueError(
            "relief_surface_contour_supersampling must be an integer from 1 to 4"
        )
    if "final_output_size_px" in config:
        values = config["final_output_size_px"]
        if (
            isinstance(values, (str, bytes))
            or not isinstance(values, Sequence)
            or len(values) != 2
            or any(isinstance(value, bool) or not isinstance(value, int) or value <= 0 for value in values)
        ):
            raise ValueError("final_output_size_px must contain two positive integers")

    if "rotation_k" in config:
        rotation = config["rotation_k"]
        if isinstance(rotation, bool) or not isinstance(rotation, int) or rotation not in range(4):
            raise ValueError("rotation_k must be one of 0, 1, 2, or 3")
    if "view_bearing_deg" in config:
        bearing = _number(config, "view_bearing_deg")
        if not 0.0 <= bearing < 360.0:
            raise ValueError("view_bearing_deg must be between 0 (inclusive) and 360 (exclusive)")
    if "relief_key_light_bearing_deg" in config:
        bearing = _number(config, "relief_key_light_bearing_deg")
        if not 0.0 <= bearing < 360.0:
            raise ValueError(
                "relief_key_light_bearing_deg must be between 0 (inclusive) and 360 (exclusive)"
            )
    if "relief_key_light_elevation_deg" in config:
        elevation = _number(config, "relief_key_light_elevation_deg")
        if not 0.0 < elevation < 90.0:
            raise ValueError(
                "relief_key_light_elevation_deg must be between 0 and 90 degrees"
            )

    explicit_imagery = {
        "imagery_sea_full_depth_m",
        "imagery_sea_max_depth_m",
    }.intersection(config)
    if explicit_imagery and len(explicit_imagery) != 2:
        raise ValueError(
            "imagery_sea_full_depth_m and imagery_sea_max_depth_m must be set together"
        )
    if explicit_imagery:
        full_depth = _number(config, "imagery_sea_full_depth_m")
        maximum_depth = _number(config, "imagery_sea_max_depth_m")
        if full_depth < 0.0 or maximum_depth <= full_depth:
            raise ValueError(
                "Sea imagery depths must satisfy 0 <= full depth < maximum depth"
            )
    if "imagery_sea_depth_m" in config and explicit_imagery:
        raise ValueError(
            "Do not mix imagery_sea_depth_m with explicit full/max sea imagery bounds"
        )
    if "imagery_sea_depth_m" in config and _number(config, "imagery_sea_depth_m") < 0.0:
        raise ValueError("imagery_sea_depth_m must be non-negative")
    if "imagery_sea_feather_m" in config:
        _positive(config, "imagery_sea_feather_m")
    if "imagery_sea_smoothing_m" in config and _number(config, "imagery_sea_smoothing_m") < 0.0:
        raise ValueError("imagery_sea_smoothing_m must be non-negative")

    if config.get("orthophoto_enabled", False):
        _non_empty_string(config, "orthophoto_layer", required=True)
        _non_empty_string(config, "orthophoto_capture_date", required=True)
        capture_date = str(config["orthophoto_capture_date"])
        try:
            parsed_date = date.fromisoformat(capture_date)
        except ValueError as error:
            raise ValueError("orthophoto_capture_date must be an ISO date (YYYY-MM-DD)") from error
        if parsed_date.isoformat() != capture_date:
            raise ValueError("orthophoto_capture_date must be an ISO date (YYYY-MM-DD)")
        _validate_wms_grid(
            focus,
            _number(config, "orthophoto_resolution_m", 0.2),
            "focus orthophoto request",
            allow_tiling=True,
        )
        _validate_wms_grid(
            context,
            _number(config, "orthophoto_3d_resolution_m", 0.4),
            "context orthophoto request",
            allow_tiling=True,
        )

    locator_enabled = config.get("locator_map_enabled", False)
    locator_bathymetry = config.get("locator_bathymetry_enabled", False)
    if locator_bathymetry and not locator_enabled:
        raise ValueError("locator_bathymetry_enabled requires locator_map_enabled")
    if locator_enabled:
        locator = bbox(config, "locator_bbox_utm40s")
        if "locator_marker_utm40s" not in config:
            raise ValueError("Missing required configuration key: locator_marker_utm40s")
        marker = _pair(config["locator_marker_utm40s"], "locator_marker_utm40s")
        if not _point_in_box(marker, focus):
            raise ValueError("locator_marker_utm40s must lie within focus_bbox_utm40s")
        if not _point_in_box(marker, locator):
            raise ValueError("locator_marker_utm40s must lie within locator_bbox_utm40s")
        _non_empty_string(config, "locator_label", required=True)
        _validate_wms_grid(
            locator,
            _number(config, "locator_resolution_m", 20.0),
            "locator RGE ALTI request",
        )
    if locator_bathymetry:
        _non_empty_string(config, "locator_gebco_attribution", required=True)
        _non_empty_string(config, "locator_gebco_layer", required=True)
        _non_empty_string(config, "locator_gebco_wms_url", required=True)

    if "locator_gebco_blur_px" in config and _number(config, "locator_gebco_blur_px") < 0.0:
        raise ValueError("locator_gebco_blur_px must be non-negative")

    if "plan_open_label_offsets_px" in config:
        offsets = config["plan_open_label_offsets_px"]
        if not isinstance(offsets, Mapping):
            raise ValueError("plan_open_label_offsets_px must be an object")
        for level, offset in offsets.items():
            _pair(offset, f"plan_open_label_offsets_px.{level}")
    if "relief_suppressed_label_levels" in config:
        levels = config["relief_suppressed_label_levels"]
        if not isinstance(levels, list) or any(
            isinstance(level, bool) or not isinstance(level, int) or level <= 0
            for level in levels
        ):
            raise ValueError("relief_suppressed_label_levels must be a list of positive integers")

    _validate_bridges(config, context)

    if int(config.get("plate_canvas_width_px", 5400)) != 5400:
        raise ValueError(
            "plate_canvas_width_px must be 5400; the current plate layout uses fixed coordinates"
        )

    resolved_paths = paths_for(config)
    seen: dict[Path, str] = {}
    for key, path in resolved_paths.items():
        canonical = path.resolve(strict=False)
        if canonical in seen:
            raise ValueError(
                f"paths.{key} resolves to the same file as paths.{seen[canonical]}: {canonical}"
            )
        seen[canonical] = key
