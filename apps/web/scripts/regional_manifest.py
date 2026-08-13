"""Shared helpers for data-driven regional Web manifests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from osgeo import osr


osr.UseExceptions()


LABEL_LAYOUT_KEYS = {
    "side": "side",
    "shift_y_rem": "shiftYRem",
    "connector_angle_deg": "connectorAngleDeg",
    "connector_width_rem": "connectorWidthRem",
    "label_offset_rem": "labelOffsetRem",
    "lines": "lines",
    "width_rem": "widthRem",
}
INITIAL_VIEW_KEYS = {
    "zoom": "zoom",
    "orbit_azimuth_deg": "orbitAzimuthDeg",
    "camera_elevation_deg": "cameraElevationDeg",
    "pan_right_m": "panRightM",
    "pan_up_m": "panUpM",
    "center_offset_east_m": "centerOffsetEastM",
    "center_offset_south_m": "centerOffsetSouthM",
    "isobath_label_focus_x_ndc": "isobathLabelFocusXNdc",
    "camera_position_m": "cameraPositionM",
    "camera_target_m": "cameraTargetM",
}


def load_region_configs(
    repository_root: Path,
    region_slug: str,
) -> list[dict[str, Any]]:
    """Load site configs in the region inventory order."""
    region_path = repository_root / "regions" / region_slug / "region.json"
    region = json.loads(region_path.read_text(encoding="utf-8"))
    configs: list[dict[str, Any]] = []
    seen: set[str] = set()
    for site in region.get("sites", []):
        config_path = repository_root / str(site["config"])
        if not config_path.is_file():
            raise FileNotFoundError(
                f"{region_slug}: site config missing: {config_path}"
            )
        config = json.loads(config_path.read_text(encoding="utf-8"))
        if config.get("slug") != site.get("slug"):
            raise ValueError(
                f"{config_path}: slug does not match its region inventory entry"
            )
        slug = str(config["slug"])
        if slug in seen:
            raise ValueError(f"{region_slug}: duplicate slug: {slug}")
        seen.add(slug)
        config["_config_path"] = config_path.relative_to(
            repository_root
        ).as_posix()
        configs.append(config)
    return configs


def load_published_configs(
    repository_root: Path,
    region_slug: str,
) -> list[dict[str, Any]]:
    """Load explicitly published sites in the region inventory order."""
    configs = [
        config
        for config in load_region_configs(repository_root, region_slug)
        if isinstance(config.get("web"), dict)
        and config["web"].get("published") is True
    ]
    if not configs:
        raise RuntimeError(f"{region_slug}: no explicitly published sites")
    return configs


def marker_wgs84(marker: list[float], projected_epsg: int) -> tuple[float, float]:
    projected = osr.SpatialReference()
    projected.ImportFromEPSG(projected_epsg)
    projected.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    geographic = osr.SpatialReference()
    geographic.ImportFromEPSG(4326)
    geographic.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    transform = osr.CoordinateTransformation(projected, geographic)
    longitude, latitude, _ = transform.TransformPoint(
        float(marker[0]),
        float(marker[1]),
    )
    return latitude, longitude


def locator_position_wgs84(
    latitude: float,
    longitude: float,
    bounds: dict[str, float],
) -> dict[str, float]:
    x_percent = (
        (longitude - bounds["west"])
        / (bounds["east"] - bounds["west"])
        * 100.0
    )
    y_percent = (
        (bounds["north"] - latitude)
        / (bounds["north"] - bounds["south"])
        * 100.0
    )
    if not (0.0 <= x_percent <= 100.0 and 0.0 <= y_percent <= 100.0):
        raise ValueError(
            "Site marker falls outside the regional locator bounds: "
            f"{latitude}, {longitude}"
        )
    return {
        "xPercent": round(x_percent, 5),
        "yPercent": round(y_percent, 5),
    }


def web_site_metadata(config: dict[str, Any]) -> dict[str, Any]:
    web = config["web"]
    layout = web["site_label_layout"]
    metadata: dict[str, Any] = {
        "siteLabelLayout": {
            output_key: layout[input_key]
            for input_key, output_key in LABEL_LAYOUT_KEYS.items()
            if input_key in layout
        }
    }
    initial_view = web.get("interactive_initial_view")
    if initial_view:
        metadata["interactiveInitialView"] = {
            output_key: initial_view[input_key]
            for input_key, output_key in INITIAL_VIEW_KEYS.items()
            if input_key in initial_view
        }
    return metadata


def site_city(config: dict[str, Any]) -> str:
    return str(config.get("plate_city_detail", config["plate_city"]))
