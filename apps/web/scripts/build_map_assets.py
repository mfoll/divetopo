#!/usr/bin/env python3
"""Build deterministic, responsive website assets from canonical map outputs.

The map renderers remain the source of truth. This script only resizes and
encodes their JPEG outputs for the website. Full-resolution printable sheets
are published as GitHub Release assets rather than bundled into Sites.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps

from regional_manifest import (
    load_published_configs,
    marker_wgs84,
    site_city,
    web_site_metadata,
)


SCRIPT_DIR = Path(__file__).resolve().parent
SITE_ROOT = SCRIPT_DIR.parent
REPOSITORY_ROOT = SITE_ROOT.parents[1]
BUNDLED_MANIFEST_PATH = SITE_ROOT / "content" / "map-manifest.json"
PUBLIC_ROOT = SITE_ROOT / "public"
OUTPUT_ROOT = PUBLIC_ROOT / "maps"
RELEASE_TAG = "v1.4.0"
RELEASE_ASSET_BASE = (
    f"https://github.com/mfoll/divetopo/releases/download/{RELEASE_TAG}"
)

MAP_WIDTHS = (960, 1600, 2474)
PLANCHE_PREVIEW_WIDTH = 1800
WEST_COAST_LOCATOR_PATH = PUBLIC_ROOT / "west-coast-locator.webp"
REUNION_OVERVIEW_PATH = PUBLIC_ROOT / "reunion-overview.webp"
REUNION_OVERVIEW_BOUNDS_UTM40S = {
    "minEasting": 305_000.0,
    "minNorthing": 7_628_000.0,
    "maxEasting": 386_000.0,
    "maxNorthing": 7_696_000.0,
}
WEST_COAST_LOCATOR_BOUNDS_UTM40S = {
    "minEasting": 309_000.0,
    "minNorthing": 7_652_000.0,
    "maxEasting": 326_000.0,
    "maxNorthing": 7_678_000.0,
}

MAP_WEBP_QUALITY = 84
PLANCHE_WEBP_QUALITY = 86
WEBP_METHOD = 6

MAP_SOURCES = (
    ("2d", "topographic", "output_2d"),
    ("2d", "orthophoto", "output_2d_ortho"),
    ("3d", "topographic", "output_3d"),
    ("3d", "orthophoto", "output_3d_ortho"),
)
PLANCHE_SOURCES = (
    ("topographic", "output_plate_topography"),
    ("orthophoto", "output_plate"),
)

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def public_url(path: Path, build_root: Path) -> str:
    return f"/maps/{path.relative_to(build_root).as_posix()}"


def image_record(path: Path, build_root: Path, width: int, height: int) -> dict[str, Any]:
    return {
        "src": public_url(path, build_root),
        "width": width,
        "height": height,
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def open_rgb(path: Path) -> Image.Image:
    with Image.open(path) as source:
        return ImageOps.exif_transpose(source).convert("RGB")


def resized(image: Image.Image, width: int) -> Image.Image:
    if width > image.width:
        raise ValueError(f"Requested width {width}px exceeds source width {image.width}px")
    if width == image.width:
        return image.copy()
    height = round(image.height * width / image.width)
    return image.resize(
        (width, height),
        Image.Resampling.LANCZOS,
        reducing_gap=3.0,
    )


def write_webp(
    image: Image.Image,
    destination: Path,
    *,
    width: int,
    quality: int,
) -> tuple[int, int]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    output = resized(image, width)
    output.save(
        destination,
        format="WEBP",
        quality=quality,
        method=WEBP_METHOD,
        exact=True,
    )
    return output.size


def configured_source(config: dict[str, Any], key: str) -> Path:
    try:
        relative_path = config["paths"][key]
    except KeyError as exc:
        raise KeyError(f"{config.get('slug', '<unknown>')}: missing paths.{key}") from exc
    source = REPOSITORY_ROOT / relative_path
    if not source.is_file():
        raise FileNotFoundError(f"{config['slug']}: canonical output missing: {source}")
    return source


def locator_position(
    marker: list[float],
    bounds: dict[str, float],
    label: str,
) -> dict[str, float]:
    easting = float(marker[0])
    northing = float(marker[1])
    x_percent = (
        (easting - bounds["minEasting"])
        / (bounds["maxEasting"] - bounds["minEasting"])
        * 100.0
    )
    y_percent = (
        (bounds["maxNorthing"] - northing)
        / (bounds["maxNorthing"] - bounds["minNorthing"])
        * 100.0
    )
    if not (0.0 <= x_percent <= 100.0 and 0.0 <= y_percent <= 100.0):
        raise ValueError(
            f"Site marker falls outside the shared {label} bounds: "
            f"{marker}"
        )
    return {
        "xPercent": round(x_percent, 4),
        "yPercent": round(y_percent, 4),
    }


def west_coast_locator_position(marker: list[float]) -> dict[str, float]:
    return locator_position(
        marker,
        WEST_COAST_LOCATOR_BOUNDS_UTM40S,
        "west-coast locator",
    )


def reunion_overview_position(marker: list[float]) -> dict[str, float]:
    return locator_position(
        marker,
        REUNION_OVERVIEW_BOUNDS_UTM40S,
        "Réunion overview",
    )


def west_coast_locator_record() -> dict[str, Any]:
    if not WEST_COAST_LOCATOR_PATH.is_file():
        raise FileNotFoundError(
            f"Shared west-coast locator missing: {WEST_COAST_LOCATOR_PATH}"
        )
    with Image.open(WEST_COAST_LOCATOR_PATH) as image:
        width, height = image.size
    return {
        "src": "/west-coast-locator.webp",
        "width": width,
        "height": height,
        "bytes": WEST_COAST_LOCATOR_PATH.stat().st_size,
        "sha256": sha256(WEST_COAST_LOCATOR_PATH),
        "boundsUtm40s": WEST_COAST_LOCATOR_BOUNDS_UTM40S,
    }


def reunion_overview_record() -> dict[str, Any]:
    if not REUNION_OVERVIEW_PATH.is_file():
        raise FileNotFoundError(
            f"Reunion overview missing: {REUNION_OVERVIEW_PATH}"
        )
    with Image.open(REUNION_OVERVIEW_PATH) as image:
        width, height = image.size
    return {
        "src": "/reunion-overview.webp",
        "width": width,
        "height": height,
        "bytes": REUNION_OVERVIEW_PATH.stat().st_size,
        "sha256": sha256(REUNION_OVERVIEW_PATH),
        "boundsUtm40s": REUNION_OVERVIEW_BOUNDS_UTM40S,
    }


def load_configs() -> list[dict[str, Any]]:
    configs = load_published_configs(REPOSITORY_ROOT, "reunion")
    for config in configs:
        if not config.get("orthophoto_enabled"):
            raise ValueError(
                f"{config['slug']}: the website requires orthophoto variants"
            )
        if not str(config.get("plate_city", "")).strip():
            raise ValueError(
                f"{config['slug']}: plate_city must identify the municipality"
            )
    return configs


def build_site(config: dict[str, Any], build_root: Path) -> dict[str, Any]:
    slug = config["slug"]
    site_root = build_root / slug
    maps: list[dict[str, Any]] = []

    for view, style, source_key in MAP_SOURCES:
        source_path = configured_source(config, source_key)
        source_image = open_rgb(source_path)
        variants: list[dict[str, Any]] = []
        for width in MAP_WIDTHS:
            destination = site_root / f"{view}-{style}-{width}.webp"
            output_width, output_height = write_webp(
                source_image,
                destination,
                width=width,
                quality=MAP_WEBP_QUALITY,
            )
            variants.append(
                image_record(
                    destination,
                    build_root,
                    output_width,
                    output_height,
                )
            )
        maps.append(
            {
                "view": view,
                "style": style,
                "sourceDimensions": {
                    "width": source_image.width,
                    "height": source_image.height,
                },
                "variants": variants,
                "download": {
                    "src": f"{RELEASE_ASSET_BASE}/{source_path.name}",
                    "width": source_image.width,
                    "height": source_image.height,
                    "bytes": source_path.stat().st_size,
                    "sha256": sha256(source_path),
                    "filename": source_path.name,
                },
            }
        )

    planches: list[dict[str, Any]] = []
    for style, source_key in PLANCHE_SOURCES:
        source_path = configured_source(config, source_key)
        source_image = open_rgb(source_path)

        preview_path = site_root / f"planche-{style}-{PLANCHE_PREVIEW_WIDTH}.webp"
        preview_width, preview_height = write_webp(
            source_image,
            preview_path,
            width=PLANCHE_PREVIEW_WIDTH,
            quality=PLANCHE_WEBP_QUALITY,
        )

        planches.append(
            {
                "style": style,
                "preview": image_record(
                    preview_path,
                    build_root,
                    preview_width,
                    preview_height,
                ),
                "download": {
                    "src": f"{RELEASE_ASSET_BASE}/{source_path.name}",
                    "width": source_image.width,
                    "height": source_image.height,
                    "bytes": source_path.stat().st_size,
                    "sha256": sha256(source_path),
                    "filename": source_path.name,
                },
            }
        )

    site_location = config.get(
        "site_location_utm40s",
        config["locator_marker_utm40s"],
    )
    latitude, longitude = marker_wgs84(site_location, 32740)

    compact_topographic = str(
        config.get(
            "bathymetry_source_text",
            "Bathymétrie : HYSCORES / Litto3D · Topographie : IGN RGE ALTI",
        )
    )
    compact_attributions = {
        "topographic": compact_topographic,
        "orthophoto": f"{compact_topographic} · Orthophoto : IGN BD ORTHO",
    }

    site = {
        "slug": slug,
        "displayName": config["plate_site_name"],
        "title": config["title"],
        "plateTitle": config["plate_title"],
        "config": config["_config_path"],
        "location": {
            "city": site_city(config),
            "latitude": round(latitude, 8),
            "longitude": round(longitude, 8),
        },
        "westCoastLocatorPosition": west_coast_locator_position(
            site_location
        ),
        "reunionOverviewPosition": reunion_overview_position(site_location),
        "maxDepthM": config["max_depth_m"],
        "planMaxDepthM": config.get("plan_max_depth_m", config["max_depth_m"]),
        "verticalExaggeration": config["vertical_exaggeration"],
        "orthophotoCaptureDate": config["orthophoto_capture_date"],
        "plateAuthor": config["plate_author"],
        "copyrightYear": config["copyright_year"],
        "mapLicense": config["map_license"],
        "compactAttributions": compact_attributions,
        "maps": maps,
        "planches": planches,
        **web_site_metadata(config),
    }
    return site


def manifest_totals(manifest: dict[str, Any]) -> dict[str, int]:
    web_bytes = (
        manifest["reunionOverview"]["bytes"]
        + manifest["westCoastLocator"]["bytes"]
    )
    download_bytes = 0
    asset_files = 2

    for site in manifest["sites"]:
        for map_item in site["maps"]:
            for variant in map_item["variants"]:
                web_bytes += variant["bytes"]
                asset_files += 1
            download_bytes += map_item["download"]["bytes"]
            asset_files += 1
        for planche in site["planches"]:
            web_bytes += planche["preview"]["bytes"]
            download_bytes += planche["download"]["bytes"]
            asset_files += 2

    return {
        "assetFiles": asset_files,
        "webOptimizedBytes": web_bytes,
        "downloadBytes": download_bytes,
        "totalBytes": web_bytes + download_bytes,
    }


def swap_build(build_root: Path) -> None:
    OUTPUT_ROOT.parent.mkdir(parents=True, exist_ok=True)
    previous_root = build_root.parent / "previous"
    if OUTPUT_ROOT.exists():
        OUTPUT_ROOT.rename(previous_root)
    try:
        build_root.rename(OUTPUT_ROOT)
    except Exception:
        if previous_root.exists():
            previous_root.rename(OUTPUT_ROOT)
        raise
    if previous_root.exists():
        shutil.rmtree(previous_root)


def main() -> None:
    configs = load_configs()
    with tempfile.TemporaryDirectory(prefix=".maps-build-", dir=PUBLIC_ROOT) as temp:
        build_root = Path(temp) / "maps"
        build_root.mkdir()
        # This builder owns the Réunion derivatives only. Preserve regional
        # packages and dynamic captures that live beside them in public/maps.
        if OUTPUT_ROOT.exists():
            shutil.copytree(OUTPUT_ROOT, build_root, dirs_exist_ok=True)

        manifest: dict[str, Any] = {
            "schemaVersion": 6,
            "mapWidths": list(MAP_WIDTHS),
            "planchePreviewWidth": PLANCHE_PREVIEW_WIDTH,
            "reunionOverview": reunion_overview_record(),
            "westCoastLocator": west_coast_locator_record(),
            "sites": [build_site(config, build_root) for config in configs],
        }
        manifest["totals"] = manifest_totals(manifest)
        manifest_path = build_root / "manifest.json"
        manifest_text = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
        manifest_path.write_text(manifest_text, encoding="utf-8")
        swap_build(build_root)
        BUNDLED_MANIFEST_PATH.write_text(manifest_text, encoding="utf-8")

    totals = manifest["totals"]
    print(
        f"Built {len(manifest['sites'])} sites and {totals['assetFiles']} assets "
        f"({totals['totalBytes'] / 1024 / 1024:.1f} MiB) in {OUTPUT_ROOT}"
    )


if __name__ == "__main__":
    main()
