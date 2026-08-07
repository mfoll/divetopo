#!/usr/bin/env python3
"""Rebuild a regional terrain manifest from published site packages."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from regional_manifest import load_published_configs


SCRIPT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = SCRIPT_DIR.parents[2]
FILE_KEYS = {
    "metadata": "terrain.json",
    "height": "height.bin",
    "validMask": "valid-mask.bin",
    "isobathMask": "isobath-mask.bin",
    "vectorIsobaths": "isobaths-vector.json",
    "topographicTexture": "topographic.webp",
    "orthophotoTexture": "orthophoto.webp",
}


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


def build_manifest(region_slug: str) -> tuple[Path, dict[str, Any]]:
    configs = load_published_configs(REPOSITORY_ROOT, region_slug)
    region = json.loads(
        (REPOSITORY_ROOT / "regions" / region_slug / "region.json").read_text(
            encoding="utf-8"
        )
    )
    output_root = REPOSITORY_ROOT / region["pipeline"][
        "interactiveTerrainDirectory"
    ]
    sites: list[dict[str, Any]] = []
    for config in configs:
        slug = str(config["slug"])
        site_root = output_root / slug
        metadata_path = site_root / "terrain.json"
        if not metadata_path.is_file():
            raise FileNotFoundError(f"{slug}: missing terrain package")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata.get("slug") != slug:
            raise ValueError(f"{slug}: terrain metadata slug mismatch")
        files = {
            key: artifact_record(site_root / filename, output_root)
            for key, filename in FILE_KEYS.items()
        }
        sites.append(
            {
                "slug": slug,
                "title": metadata["title"],
                "metadata": f"{slug}/terrain.json",
                "files": files,
            }
        )
    manifest = {"schemaVersion": 2, "sites": sites}
    return output_root, manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("region", help="Region slug under regions/<slug>")
    args = parser.parse_args()
    output_root, manifest = build_manifest(args.region)
    manifest_path = output_root / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Indexed {len(manifest['sites'])} {args.region} terrain packages")


if __name__ == "__main__":
    main()
