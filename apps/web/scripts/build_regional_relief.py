#!/usr/bin/env python3
"""Build one autonomous Mediterranean regional relief and manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from regional_manifest import marker_wgs84


ROOT = Path(__file__).resolve().parents[3]
WEB_ROOT = ROOT / "apps" / "web"
WIDTH = 1864
HEIGHT = 1440
MIN_LONGITUDE_SPAN = 0.32
MIN_LATITUDE_SPAN = 0.24


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_region(region_slug: str) -> dict[str, Any]:
    path = ROOT / "regions" / region_slug / "region.json"
    region = json.loads(path.read_text(encoding="utf-8"))
    if region.get("slug") != region_slug:
        raise ValueError(f"Region slug mismatch in {path}")
    return region


def marker_bounds(region: dict[str, Any]) -> tuple[float, float, float, float]:
    configured = region.get("regionalMap")
    if isinstance(configured, dict):
        raw = configured.get("boundsWgs84")
        if (
            isinstance(raw, list)
            and len(raw) == 4
            and all(isinstance(value, (int, float)) for value in raw)
        ):
            west, south, east, north = (float(value) for value in raw)
            if west < east and south < north:
                return west, south, east, north

    coordinates: list[tuple[float, float]] = []
    crs = str(region["crs"]["code"])
    epsg = int(crs.split(":")[-1])
    for site in region.get("sites", []):
        config_path = ROOT / str(site["config"])
        config = json.loads(config_path.read_text(encoding="utf-8"))
        marker = config.get(
            "site_location_utm40s",
            config.get("locator_marker_utm40s"),
        )
        if not isinstance(marker, list) or len(marker) != 2:
            raise ValueError(f"{config_path}: missing site marker")
        latitude, longitude = marker_wgs84(marker, epsg)
        coordinates.append((longitude, latitude))
    if not coordinates:
        raise ValueError(f"{region['slug']}: no site markers for regional map")

    longitudes, latitudes = zip(*coordinates)
    longitude_span = max(max(longitudes) - min(longitudes), MIN_LONGITUDE_SPAN)
    latitude_span = max(max(latitudes) - min(latitudes), MIN_LATITUDE_SPAN)
    longitude_center = (min(longitudes) + max(longitudes)) / 2.0
    latitude_center = (min(latitudes) + max(latitudes)) / 2.0
    return (
        longitude_center - longitude_span * 0.65,
        latitude_center - latitude_span * 0.65,
        longitude_center + longitude_span * 0.65,
        latitude_center + latitude_span * 0.65,
    )


def manifest_template(
    region_slug: str,
    bounds: tuple[float, float, float, float],
) -> dict[str, Any]:
    west, south, east, north = bounds
    return {
        "schemaVersion": 2,
        "reunionOverview": {
            "src": "/maps/paca/france-metropolitan-situation.png",
            "width": 1000,
            "height": 840,
        },
        "westCoastLocator": {
            "src": f"/maps/{region_slug}/{region_slug}-regional-relief.png",
            "width": WIDTH,
            "height": HEIGHT,
            "boundsWgs84": {
                "west": west,
                "south": south,
                "east": east,
                "north": north,
            },
        },
        "sites": [],
    }


def refresh_manifest_data(
    region_slug: str,
    bounds: tuple[float, float, float, float],
    manifest_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    template = manifest_template(region_slug, bounds)
    if manifest_data is None:
        return template

    locator = manifest_data.setdefault("westCoastLocator", {})
    locator.update(template["westCoastLocator"])
    manifest_data.setdefault("reunionOverview", template["reunionOverview"])
    manifest_data.setdefault("sites", [])
    return manifest_data


def configure(region_slug: str) -> tuple[dict[str, Any], Path, Path, Any]:
    import build_paca_regional_relief as builder

    region = load_region(region_slug)
    bounds = marker_bounds(region)
    public_output = (
        WEB_ROOT
        / "public"
        / "maps"
        / region_slug
        / f"{region_slug}-regional-relief.png"
    )
    manifest = WEB_ROOT / "content" / f"{region_slug}-map-manifest.json"
    if manifest.is_file():
        manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
    else:
        manifest_data = None
    manifest_data = refresh_manifest_data(region_slug, bounds, manifest_data)
    manifest.write_text(
        json.dumps(manifest_data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    builder.REGION_SLUG = region_slug
    builder.OUTPUT = public_output
    builder.MANIFEST = manifest
    builder.CACHE = ROOT / ".tmp" / f"{region_slug}-regional-relief"
    builder.SITE_CONFIG_DIR = ROOT / "regions" / region_slug / "sites"
    builder.MAP_BOUNDS = bounds
    builder.EMODNET_REQUEST_WIDTH = round(
        (bounds[2] - bounds[0]) / builder.EMODNET_CELL_DEG
    )
    builder.EMODNET_REQUEST_HEIGHT = round(
        (bounds[3] - bounds[1]) / builder.EMODNET_CELL_DEG
    )
    regional_output = (
        ROOT / "regions" / region_slug / "outputs"
        / f"{region_slug}-regional-relief.png"
    )
    return region, public_output, regional_output, builder


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("region_slug")
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    region, public_output, regional_output, builder = configure(
        args.region_slug
    )
    builder.render(refresh=args.refresh)
    regional_output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(public_output, regional_output)
    regional_map = region.get("regionalMap")
    if isinstance(regional_map, dict):
        regional_map.update(
            {
                "status": "generated",
                "output": regional_output.relative_to(ROOT).as_posix(),
                "webDerivative": public_output.relative_to(ROOT).as_posix(),
                "boundsWgs84": list(builder.MAP_BOUNDS),
                "sha256": sha256(public_output),
            }
        )
    else:
        region["regionalMap"] = {
            "status": "generated",
            "output": regional_output.relative_to(ROOT).as_posix(),
            "webDerivative": public_output.relative_to(ROOT).as_posix(),
            "boundsWgs84": list(builder.MAP_BOUNDS),
            "sha256": sha256(public_output),
        }
    region_path = ROOT / "regions" / args.region_slug / "region.json"
    region_path.write_text(
        json.dumps(region, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Updated {region_path}")


if __name__ == "__main__":
    main()
