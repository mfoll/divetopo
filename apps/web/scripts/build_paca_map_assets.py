#!/usr/bin/env python3
"""Publish PACA planche previews and refresh their release-backed records."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from PIL import Image

from regional_manifest import (
    load_region_configs,
    locator_position_wgs84,
    marker_wgs84,
    site_city,
    web_site_metadata,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
WEB_ROOT = REPOSITORY_ROOT / "apps" / "web"
PUBLIC_ROOT = WEB_ROOT / "public"
OUTPUT_ROOT = REPOSITORY_ROOT / "regions" / "paca" / "outputs"
MANIFEST_PATH = WEB_ROOT / "content" / "paca-map-manifest.json"
REGION_SLUG = "paca"
PREVIEW_WIDTH = 1800
RELEASE_TAG = "v1.4.0"
RELEASE_ASSET_BASE = (
    f"https://github.com/mfoll/divetopo/releases/download/{RELEASE_TAG}"
)
MEDITERRANEAN_COMPACT_ATTRIBUTIONS = {
    "topographic": "Bathymétrie / topographie : Shom–IGN Litto3D PACA 2015 · MNT 1 m · IGN69",
    "orthophoto": "Bathymétrie / topographie : Shom–IGN Litto3D PACA 2015 · MNT 1 m · IGN69 · Orthophoto : IGN BD ORTHO",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def image_record(path: Path, public_root: Path, width: int, height: int) -> dict[str, object]:
    digest = sha256(path)
    return {
        "src": f"/{path.relative_to(public_root).as_posix()}?v={digest[:12]}",
        "width": width,
        "height": height,
        "bytes": path.stat().st_size,
        "sha256": digest,
    }


def bundled_image_record(path: Path, width: int, height: int) -> dict[str, object]:
    return {
        "src": f"/{path.relative_to(PUBLIC_ROOT).as_posix()}",
        "width": width,
        "height": height,
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def source_for(slug: str, style: str) -> Path:
    suffix = "-topographique" if style == "topographic" else ""
    return OUTPUT_ROOT / f"{slug}-planche{suffix}.jpg"


def plan_source_for(slug: str, style: str) -> Path:
    suffix = "-ortho" if style == "orthophoto" else ""
    return OUTPUT_ROOT / f"{slug}-topobathy-2d{suffix}.jpg"


def publish_plan(slug: str, style: str) -> dict[str, object]:
    source = plan_source_for(slug, style)
    if not source.is_file():
        raise FileNotFoundError(
            f"Missing generated {REGION_SLUG} 2D plan: {source}"
        )
    destination = (
        PUBLIC_ROOT
        / "maps"
        / REGION_SLUG
        / slug
        / "maps"
        / f"2d-{style}.jpg"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    with Image.open(destination) as image:
        width, height = image.size
    record = image_record(destination, PUBLIC_ROOT, width, height)
    return {
        "view": "2d",
        "style": style,
        "sourceDimensions": {"width": width, "height": height},
        "variants": [record],
        "download": {
            **record,
            "filename": source.name,
        },
    }


def build_planche(slug: str, style: str) -> dict[str, object]:
    source = source_for(slug, style)
    if not source.is_file():
        raise FileNotFoundError(
            f"Missing generated {REGION_SLUG} planche: {source}"
        )

    site_root = PUBLIC_ROOT / "maps" / REGION_SLUG / slug / "maps"
    preview_path = site_root / f"planche-{style}-{PREVIEW_WIDTH}.webp"

    with Image.open(source) as image:
        source_width, source_height = image.size
        preview_height = round(PREVIEW_WIDTH * source_height / source_width)
        image.resize(
            (PREVIEW_WIDTH, preview_height),
            Image.Resampling.LANCZOS,
        ).save(
            preview_path,
            format="WEBP",
            quality=86,
            method=6,
            exact=True,
        )

    return {
        "style": style,
        "preview": image_record(
            preview_path,
            PUBLIC_ROOT,
            PREVIEW_WIDTH,
            preview_height,
        ),
        "download": {
            "src": f"{RELEASE_ASSET_BASE}/{source.name}",
            "width": source_width,
            "height": source_height,
            "bytes": source.stat().st_size,
            "sha256": sha256(source),
            "filename": source.name,
        },
    }


def build_dynamic_map(slug: str, style: str) -> dict[str, object]:
    site_root = PUBLIC_ROOT / "maps" / REGION_SLUG / slug / "maps"
    variants: list[dict[str, object]] = []
    for width in (960, 1600, 2474):
        path = site_root / f"3d-dynamic-{style}-{width}.webp"
        if not path.is_file():
            raise FileNotFoundError(
                f"Missing {REGION_SLUG} 3D capture: {path}"
            )
        with Image.open(path) as image:
            output_width, output_height = image.size
        variants.append(
            bundled_image_record(path, output_width, output_height)
        )
    mobile = site_root / f"3d-dynamic-{style}-mobile-960.webp"
    if not mobile.is_file():
        raise FileNotFoundError(
            f"Missing {REGION_SLUG} mobile 3D capture: {mobile}"
        )
    download = site_root / "downloads" / f"3d-dynamic-{style}-full.jpg"
    if not download.is_file():
        raise FileNotFoundError(
            f"Missing {REGION_SLUG} 3D download: {download}"
        )
    with Image.open(download) as image:
        source_width, source_height = image.size
    return {
        "view": "3d",
        "style": style,
        "sourceDimensions": {
            "width": source_width,
            "height": source_height,
        },
        "variants": variants,
        "download": {
            **bundled_image_record(download, source_width, source_height),
            "filename": f"{slug}-3d-dynamique-{style}.jpg",
        },
    }


def build_site(
    config: dict[str, Any],
    locator_bounds: dict[str, float],
) -> dict[str, Any]:
    slug = str(config["slug"])
    marker = config.get("site_location_utm40s") or config.get(
        "locator_marker_utm40s"
    )
    if not isinstance(marker, list):
        raise ValueError(f"{slug}: invalid site marker")
    latitude, longitude = marker_wgs84(marker, 2154)
    return {
        "slug": slug,
        "displayName": config["plate_site_name"],
        "plateTitle": config["plate_title"],
        "config": config["_config_path"],
        "assetBasePath": f"/maps/{REGION_SLUG}/{slug}",
        "location": {
            "city": site_city(config),
            "latitude": round(latitude, 8),
            "longitude": round(longitude, 8),
        },
        "westCoastLocatorPosition": locator_position_wgs84(
            latitude,
            longitude,
            locator_bounds,
        ),
        "maxDepthM": config["max_depth_m"],
        "planMaxDepthM": config.get("plan_max_depth_m", config["max_depth_m"]),
        "verticalExaggeration": config["vertical_exaggeration"],
        "orthophotoCaptureDate": config["orthophoto_capture_date"],
        "plateAuthor": config["plate_author"],
        "copyrightYear": config["copyright_year"],
        "mapLicense": config["map_license"],
        "compactAttributions": MEDITERRANEAN_COMPACT_ATTRIBUTIONS,
        "maps": [
            publish_plan(slug, "topographic"),
            publish_plan(slug, "orthophoto"),
            build_dynamic_map(slug, "topographic"),
            build_dynamic_map(slug, "orthophoto"),
        ],
        "planches": [
            build_planche(slug, "topographic"),
            build_planche(slug, "orthophoto"),
        ],
        **web_site_metadata(config),
    }


def build_planned_site(
    config: dict[str, Any],
    locator_bounds: dict[str, float],
) -> dict[str, Any]:
    slug = str(config["slug"])
    marker = config.get("site_location_utm40s") or config.get(
        "locator_marker_utm40s"
    )
    if not isinstance(marker, list):
        raise ValueError(f"{slug}: invalid site marker")
    latitude, longitude = marker_wgs84(marker, 2154)
    web = config.get("web", {})
    return {
        "slug": slug,
        "displayName": config["plate_site_name"],
        "location": {
            "city": site_city(config),
            "latitude": round(latitude, 8),
            "longitude": round(longitude, 8),
        },
        "westCoastLocatorPosition": locator_position_wgs84(
            latitude,
            longitude,
            locator_bounds,
        ),
        "siteLabelLayout": web_site_metadata(config)["siteLabelLayout"],
        "status": "published" if web.get("published") is True else "preparing",
    }


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    all_configs = load_region_configs(REPOSITORY_ROOT, REGION_SLUG)
    configs = [
        config
        for config in all_configs
        if isinstance(config.get("web"), dict)
        and config["web"].get("published") is True
    ]
    locator_bounds = manifest["westCoastLocator"].get("boundsWgs84")
    if not isinstance(locator_bounds, dict):
        raise ValueError("PACA regional locator requires WGS84 bounds")
    manifest["schemaVersion"] = 2
    manifest["plannedSites"] = [
        build_planned_site(config, locator_bounds)
        for config in all_configs
    ]
    manifest["sites"] = [
        build_site(config, locator_bounds) for config in configs
    ]
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Updated {MANIFEST_PATH}")
    print(
        f"Built {len(manifest['sites'])} data-driven {REGION_SLUG} site entries "
        "with 2D, 3D and planche assets"
    )


if __name__ == "__main__":
    main()
