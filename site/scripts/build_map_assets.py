#!/usr/bin/env python3
"""Build deterministic, responsive website assets from canonical map outputs.

The map renderers remain the source of truth. This script only resizes and
encodes their JPEG outputs for the website, then copies the original planches
unchanged so visitors can download the full-resolution printable files.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from osgeo import osr
from PIL import Image, ImageOps


SCRIPT_DIR = Path(__file__).resolve().parent
SITE_ROOT = SCRIPT_DIR.parent
PROJECT_ROOT = SITE_ROOT.parent
CONFIG_ROOT = PROJECT_ROOT / "sites"
SITE_DETAILS_PATH = SITE_ROOT / "content" / "site-details.json"
PUBLIC_ROOT = SITE_ROOT / "public"
OUTPUT_ROOT = PUBLIC_ROOT / "maps"

MAP_WIDTHS = (960, 1600, 2474)
PLANCHE_PREVIEW_WIDTH = 1800
WEST_COAST_LOCATOR_PATH = PUBLIC_ROOT / "west-coast-locator.webp"
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

osr.UseExceptions()


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
    source = PROJECT_ROOT / relative_path
    if not source.is_file():
        raise FileNotFoundError(f"{config['slug']}: canonical output missing: {source}")
    return source


def marker_wgs84(marker: list[float]) -> tuple[float, float]:
    projected = osr.SpatialReference()
    projected.ImportFromEPSG(32740)
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


def west_coast_locator_position(marker: list[float]) -> dict[str, float]:
    easting = float(marker[0])
    northing = float(marker[1])
    bounds = WEST_COAST_LOCATOR_BOUNDS_UTM40S
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
            "Site marker falls outside the shared west-coast locator bounds: "
            f"{marker}"
        )
    return {
        "xPercent": round(x_percent, 4),
        "yPercent": round(y_percent, 4),
    }


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


def load_site_details() -> dict[str, dict[str, str]]:
    with SITE_DETAILS_PATH.open(encoding="utf-8") as stream:
        details = json.load(stream)
    if not isinstance(details, dict):
        raise TypeError(f"{SITE_DETAILS_PATH}: expected a JSON object")
    for slug, item in details.items():
        if not isinstance(item, dict) or not str(item.get("city", "")).strip():
            raise ValueError(f"{SITE_DETAILS_PATH}: {slug!r} requires a non-empty city")
    return details


def load_configs() -> list[dict[str, Any]]:
    site_details = load_site_details()
    configs: list[dict[str, Any]] = []
    for path in sorted(CONFIG_ROOT.glob("*.json")):
        with path.open(encoding="utf-8") as stream:
            config = json.load(stream)
        if not config.get("orthophoto_enabled"):
            raise ValueError(f"{path.name}: the website requires orthophoto variants")
        try:
            config["_site_details"] = site_details[config["slug"]]
        except KeyError as exc:
            raise KeyError(
                f"{SITE_DETAILS_PATH}: missing website details for {config['slug']!r}"
            ) from exc
        config["_config_path"] = path.relative_to(PROJECT_ROOT).as_posix()
        configs.append(config)

    if not configs:
        raise RuntimeError(f"No site configurations found under {CONFIG_ROOT}")

    # A north-to-south order makes the west-coast collection read naturally.
    return sorted(configs, key=lambda item: item["locator_marker_utm40s"][1], reverse=True)


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

        download_path = site_root / "downloads" / f"planche-{style}-full.jpg"
        download_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_path, download_path)

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
                    **image_record(
                        download_path,
                        build_root,
                        source_image.width,
                        source_image.height,
                    ),
                    "filename": source_path.name,
                },
            }
        )

    latitude, longitude = marker_wgs84(config["locator_marker_utm40s"])

    return {
        "slug": slug,
        "displayName": config["locator_label"],
        "title": config["title"],
        "plateTitle": config["plate_title"],
        "config": config["_config_path"],
        "location": {
            "city": config["_site_details"]["city"],
            "latitude": round(latitude, 8),
            "longitude": round(longitude, 8),
        },
        "westCoastLocatorPosition": west_coast_locator_position(
            config["locator_marker_utm40s"]
        ),
        "maxDepthM": config["max_depth_m"],
        "verticalExaggeration": config["vertical_exaggeration"],
        "orthophotoCaptureDate": config["orthophoto_capture_date"],
        "plateAuthor": config["plate_author"],
        "copyrightYear": config["copyright_year"],
        "mapLicense": config["map_license"],
        "maps": maps,
        "planches": planches,
    }


def manifest_totals(manifest: dict[str, Any]) -> dict[str, int]:
    web_bytes = manifest["westCoastLocator"]["bytes"]
    download_bytes = 0
    asset_files = 1

    for site in manifest["sites"]:
        for map_item in site["maps"]:
            for variant in map_item["variants"]:
                web_bytes += variant["bytes"]
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

        manifest: dict[str, Any] = {
            "schemaVersion": 4,
            "mapWidths": list(MAP_WIDTHS),
            "planchePreviewWidth": PLANCHE_PREVIEW_WIDTH,
            "westCoastLocator": west_coast_locator_record(),
            "sites": [build_site(config, build_root) for config in configs],
        }
        manifest["totals"] = manifest_totals(manifest)
        manifest_path = build_root / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        swap_build(build_root)

    totals = manifest["totals"]
    print(
        f"Built {len(manifest['sites'])} sites and {totals['assetFiles']} assets "
        f"({totals['totalBytes'] / 1024 / 1024:.1f} MiB) in {OUTPUT_ROOT}"
    )


if __name__ == "__main__":
    main()
