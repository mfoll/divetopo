#!/usr/bin/env python3
"""Copy the canonical interactive terrain package into the website.

Terrain generation belongs to the map pipeline. This script only verifies the
canonical manifest and copies the exact declared files into the website's
public directory.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
SITE_ROOT = SCRIPT_DIR.parent
REPOSITORY_ROOT = SITE_ROOT.parents[1]
CANONICAL_ROOT = (
    REPOSITORY_ROOT
    / "regions"
    / "reunion"
    / "outputs"
    / "interactive-terrain"
)
PUBLIC_ROOT = SITE_ROOT / "public"
OUTPUT_ROOT = PUBLIC_ROOT / "terrain"
EXPECTED_FILE_KEYS = {
    "metadata",
    "height",
    "validMask",
    "isobathMask",
    "topographicTexture",
    "orthophotoTexture",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def checked_source(source_root: Path, relative_path: str) -> Path:
    source_root = source_root.resolve()
    source = (source_root / relative_path).resolve()
    if not source.is_relative_to(source_root):
        raise ValueError(f"Terrain manifest path escapes its package: {relative_path}")
    if not source.is_file():
        raise FileNotFoundError(f"Canonical terrain artifact missing: {source}")
    return source


def verify_record(source_root: Path, record: dict[str, Any]) -> Path:
    source = checked_source(source_root, str(record["path"]))
    if source.stat().st_size != int(record["bytes"]):
        raise ValueError(f"Canonical terrain size mismatch: {source}")
    if sha256(source) != str(record["sha256"]):
        raise ValueError(f"Canonical terrain digest mismatch: {source}")
    return source


def load_manifest(source_root: Path) -> dict[str, Any]:
    manifest_path = source_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schemaVersion") != 2:
        raise ValueError("Unsupported interactive terrain package schema")
    sites = manifest.get("sites")
    if not isinstance(sites, list) or not sites:
        raise ValueError("Interactive terrain package contains no sites")
    return manifest


def swap_output(build_root: Path, output_root: Path) -> None:
    previous_root = build_root.parent / "previous"
    if output_root.exists():
        output_root.rename(previous_root)
    try:
        build_root.rename(output_root)
    except Exception:
        if previous_root.exists():
            previous_root.rename(output_root)
        raise
    if previous_root.exists():
        shutil.rmtree(previous_root)


def sync_package(
    source_root: Path = CANONICAL_ROOT,
    output_root: Path = OUTPUT_ROOT,
) -> dict[str, Any]:
    source_root = source_root.resolve()
    output_root = output_root.resolve()
    manifest = load_manifest(source_root)
    output_root.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(
        prefix=".terrain-sync-",
        dir=output_root.parent,
    ) as temporary_directory:
        build_root = Path(temporary_directory) / "terrain"
        build_root.mkdir()
        copied_paths: set[str] = set()

        for site in manifest["sites"]:
            files = site.get("files")
            if not isinstance(files, dict) or set(files) != EXPECTED_FILE_KEYS:
                raise ValueError(
                    f"{site.get('slug', '<unknown>')}: unexpected terrain file set"
                )
            for record in files.values():
                source = verify_record(source_root, record)
                relative_path = str(record["path"])
                if relative_path in copied_paths:
                    raise ValueError(f"Duplicate terrain artifact: {relative_path}")
                copied_paths.add(relative_path)
                destination = build_root / relative_path
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
                verify_record(build_root, record)

        shutil.copy2(source_root / "manifest.json", build_root / "manifest.json")
        swap_output(build_root, output_root)

    return manifest


def main() -> None:
    manifest = sync_package()
    print(
        f"Copied {len(manifest['sites'])} canonical terrain packages "
        f"from {CANONICAL_ROOT} to {OUTPUT_ROOT}"
    )


if __name__ == "__main__":
    main()
