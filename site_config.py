from __future__ import annotations

import math
import re
from datetime import date
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parent
DEFAULT_CACHE = ROOT / ".tmp" / "bathy-renders"
DEFAULT_VERTICAL_EXAGGERATION = 3.9935327405

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
        "land_sieve_threshold_px",
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
        "locator_output_width_px",
        "locator_resolution_m",
        "map_license",
        "map_style_scale",
        "max_depth_m",
        "max_land_elevation_m",
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
        "plan_output_scale",
        "plate_author",
        "plate_canvas_height_px",
        "plate_canvas_width_px",
        "plate_title",
        "relief_output_scale",
        "relief_hemisphere_intensity",
        "relief_key_light_bearing_deg",
        "relief_key_light_elevation_deg",
        "relief_key_light_intensity",
        "relief_normal_sample_spacing_m",
        "relief_suppressed_label_levels",
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
        "locator_bathymetry_enabled",
        "locator_map_enabled",
        "orthophoto_coastline_visible",
        "orthophoto_enabled",
    }
)


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
        "locator_elevation": cache / "reunion-locator-elevation.tif",
        "locator_bathymetry": cache / "reunion-locator-gebco-relief.tif",
        "output_2d": ROOT / "outputs" / f"{slug}-topobathy-2d.jpg",
        "output_2d_ortho": ROOT / "outputs" / f"{slug}-topobathy-2d-ortho.jpg",
        "output_3d": ROOT / "outputs" / f"{slug}-topobathy-3d.jpg",
        "output_3d_ortho": ROOT / "outputs" / f"{slug}-topobathy-3d-ortho.jpg",
        "output_locator": ROOT / "outputs" / f"{slug}-locator-reunion.jpg",
        "output_plate": ROOT / "outputs" / f"{slug}-planche.jpg",
        "output_plate_topography": ROOT / "outputs" / f"{slug}-planche-topographique.jpg",
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


def _point_in_box(point: tuple[float, float], extent: tuple[float, float, float, float]) -> bool:
    return extent[0] <= point[0] <= extent[2] and extent[1] <= point[1] <= extent[3]


def _validate_wms_grid(
    extent: tuple[float, float, float, float],
    resolution: float,
    description: str,
) -> None:
    width = int(round((extent[2] - extent[0]) / resolution))
    height = int(round((extent[3] - extent[1]) / resolution))
    if width <= 0 or height <= 0:
        raise ValueError(f"{description} has no pixels at {resolution:g} m resolution")
    if width > 5000 or height > 5000:
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
    for key in _BOOLEAN_KEYS.intersection(config):
        if not isinstance(config[key], bool):
            raise ValueError(f"{key} must be true or false")

    for key in ("slug", "title"):
        _non_empty_string(config, key, required=True)
    slug = str(config["slug"])
    if not _SLUG_PATTERN.fullmatch(slug):
        raise ValueError("slug must use lowercase letters, digits, and single hyphens")

    _non_empty_string(config, "hyscores_tiff_url", required=True)
    if "hyscores_directory" in config:
        _non_empty_string(config, "hyscores_directory")

    for key in ("plate_author", "plate_title", "map_license"):
        if key in config:
            _non_empty_string(config, key)

    focus = bbox(config, "focus_bbox_utm40s")
    context = bbox(config, "context_bbox_utm40s")
    if not contains(context, focus):
        raise ValueError("context_bbox_utm40s must contain focus_bbox_utm40s")

    max_depth = _number(config, "max_depth_m", 20.0)
    if not 0.0 < max_depth <= 40.0:
        raise ValueError("max_depth_m must be greater than 0 and at most 40")
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
        "relief_hemisphere_intensity",
        "relief_key_light_intensity",
        "relief_normal_sample_spacing_m",
    ):
        if key in config:
            _positive(config, key)
    for key in ("view_center_offset_east_m", "view_center_offset_north_m"):
        if key in config:
            _number(config, key)

    focus_resolution = _number(config, "topography_resolution_m", 0.5)
    context_resolution = _number(
        config,
        "context_topography_resolution_m",
        focus_resolution,
    )
    _validate_wms_grid(context, context_resolution, "context RGE ALTI request")
    if abs(focus_resolution - context_resolution) > 1e-9:
        _validate_wms_grid(focus, focus_resolution, "focus RGE ALTI request")

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
    ):
        _positive_int(config, key)
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
        )
        _validate_wms_grid(
            context,
            _number(config, "orthophoto_3d_resolution_m", 0.4),
            "context orthophoto request",
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
