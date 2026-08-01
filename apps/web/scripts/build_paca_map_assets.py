#!/usr/bin/env python3
"""Publish PACA planche previews and refresh their release-backed records."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
WEB_ROOT = REPOSITORY_ROOT / "apps" / "web"
PUBLIC_ROOT = WEB_ROOT / "public"
OUTPUT_ROOT = REPOSITORY_ROOT / "regions" / "paca" / "outputs"
MANIFEST_PATH = WEB_ROOT / "content" / "paca-map-manifest.json"
PREVIEW_WIDTH = 1800
RELEASE_TAG = "v1.2.0"
RELEASE_ASSET_BASE = (
    f"https://github.com/mfoll/divetopo/releases/download/{RELEASE_TAG}"
)


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


def source_for(slug: str, style: str) -> Path:
    suffix = "-topographique" if style == "topographic" else ""
    return OUTPUT_ROOT / f"{slug}-planche{suffix}.jpg"


def plan_source_for(slug: str, style: str) -> Path:
    suffix = "-ortho" if style == "orthophoto" else ""
    return OUTPUT_ROOT / f"{slug}-topobathy-2d{suffix}.jpg"


def publish_plan(slug: str, style: str) -> dict[str, object]:
    source = plan_source_for(slug, style)
    if not source.is_file():
        raise FileNotFoundError(f"Missing generated PACA 2D plan: {source}")
    destination = (
        PUBLIC_ROOT / "maps" / "paca" / slug / "maps" / f"2d-{style}.jpg"
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
        raise FileNotFoundError(f"Missing generated PACA planche: {source}")

    site_root = PUBLIC_ROOT / "maps" / "paca" / slug / "maps"
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


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    for site in manifest["sites"]:
        preserved_maps = [item for item in site["maps"] if item["view"] != "2d"]
        site["maps"] = [
            publish_plan(site["slug"], "topographic"),
            publish_plan(site["slug"], "orthophoto"),
            *preserved_maps,
        ]
        site["planches"] = [
            build_planche(site["slug"], "topographic"),
            build_planche(site["slug"], "orthophoto"),
        ]
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Updated {MANIFEST_PATH}")
    print(f"Built {len(manifest['sites']) * 2} PACA 2D and planche assets")


if __name__ == "__main__":
    main()
