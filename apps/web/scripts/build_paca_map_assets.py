#!/usr/bin/env python3
"""Publish PACA planche previews/downloads and refresh their manifest records."""

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


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def image_record(path: Path, public_root: Path, width: int, height: int) -> dict[str, object]:
    return {
        "src": f"/{path.relative_to(public_root).as_posix()}",
        "width": width,
        "height": height,
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def source_for(slug: str, style: str) -> Path:
    suffix = "-topographique" if style == "topographic" else ""
    return OUTPUT_ROOT / f"{slug}-planche{suffix}.jpg"


def build_planche(slug: str, style: str) -> dict[str, object]:
    source = source_for(slug, style)
    if not source.is_file():
        raise FileNotFoundError(f"Missing generated PACA planche: {source}")

    site_root = PUBLIC_ROOT / "maps" / "paca" / slug / "maps"
    download_path = site_root / "downloads" / f"planche-{style}-full.jpg"
    preview_path = site_root / f"planche-{style}-{PREVIEW_WIDTH}.webp"
    download_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, download_path)

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
            **image_record(
                download_path,
                PUBLIC_ROOT,
                source_width,
                source_height,
            ),
            "filename": source.name,
        },
    }


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    for site in manifest["sites"]:
        site["planches"] = [
            build_planche(site["slug"], "topographic"),
            build_planche(site["slug"], "orthophoto"),
        ]
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Updated {MANIFEST_PATH}")
    print(f"Built {len(manifest['sites']) * 2} PACA planche assets")


if __name__ == "__main__":
    main()
