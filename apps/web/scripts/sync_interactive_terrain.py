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
REGIONS_ROOT = REPOSITORY_ROOT / "regions"
PUBLIC_ROOT = SITE_ROOT / "public"
OUTPUT_ROOT = PUBLIC_ROOT / "terrain"
REQUIRED_FILE_KEYS = {
    "metadata",
    "height",
    "validMask",
    "isobathMask",
    "topographicTexture",
    "orthophotoTexture",
}
OPTIONAL_FILE_KEYS = {"vectorIsobaths"}


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


def published_site_slugs(region_slug: str) -> set[str] | None:
    if region_slug == "paca":
        return set()
    region_path = REGIONS_ROOT / region_slug / "region.json"
    if not region_path.is_file():
        return None
    region = json.loads(region_path.read_text(encoding="utf-8"))
    published: set[str] = set()
    for site in region.get("sites", []):
        config_path = REPOSITORY_ROOT / str(site["config"])
        config = json.loads(config_path.read_text(encoding="utf-8"))
        if config.get("web", {}).get("published") is True:
            published.add(str(site["slug"]))
    return published


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
    source_root: Path,
    output_root: Path = OUTPUT_ROOT,
) -> dict[str, Any]:
    return sync_packages([source_root], output_root)


def discover_source_roots(
    regions_root: Path = REGIONS_ROOT,
) -> list[tuple[str, Path]]:
    packages: list[tuple[str, Path]] = []
    for region_path in sorted(regions_root.glob("*/region.json")):
        region = json.loads(region_path.read_text(encoding="utf-8"))
        relative_path = region.get("pipeline", {}).get(
            "interactiveTerrainDirectory"
        )
        if not relative_path:
            continue
        source_root = (REPOSITORY_ROOT / str(relative_path)).resolve()
        if (source_root / "manifest.json").is_file():
            packages.append((str(region["slug"]), source_root))
    if not packages:
        raise RuntimeError("No regional interactive terrain packages found")
    return packages


def sync_packages(
    packages: list[Path] | list[tuple[str, Path]],
    output_root: Path = OUTPUT_ROOT,
) -> dict[str, Any]:
    normalized: list[tuple[str, Path]] = []
    for index, package in enumerate(packages):
        if isinstance(package, tuple):
            region_slug, source_root = package
        else:
            region_slug, source_root = f"package-{index + 1}", package
        normalized.append((region_slug, source_root.resolve()))
    output_root = output_root.resolve()
    manifests = []
    for region_slug, source_root in normalized:
        manifest = load_manifest(source_root)
        published = published_site_slugs(region_slug)
        if published is not None:
            indexed = {str(site.get("slug", "")) for site in manifest["sites"]}
            missing = sorted(published - indexed)
            if missing:
                raise ValueError(
                    f"{region_slug}: published terrain packages missing: {missing}"
                )
            manifest = {
                **manifest,
                "sites": [
                    site
                    for site in manifest["sites"]
                    if str(site.get("slug", "")) in published
                ],
            }
        if manifest["sites"]:
            manifests.append((region_slug, source_root, manifest))
    if not manifests:
        raise RuntimeError("No published regional terrain packages found")
    combined_manifest: dict[str, Any] = {
        "schemaVersion": 2,
        "regions": [region_slug for region_slug, _, _ in manifests],
        "sites": [],
    }
    output_root.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(
        prefix=".terrain-sync-",
        dir=output_root.parent,
    ) as temporary_directory:
        build_root = Path(temporary_directory) / "terrain"
        build_root.mkdir()
        copied_paths: set[str] = set()

        copied_slugs: set[str] = set()
        for _, source_root, manifest in manifests:
            for site in manifest["sites"]:
                slug = str(site.get("slug", ""))
                if not slug or slug in copied_slugs:
                    raise ValueError(f"Duplicate terrain site slug: {slug}")
                copied_slugs.add(slug)
                files = site.get("files")
                file_keys = set(files) if isinstance(files, dict) else set()
                if (
                    not isinstance(files, dict)
                    or not REQUIRED_FILE_KEYS.issubset(file_keys)
                    or not file_keys.issubset(
                        REQUIRED_FILE_KEYS | OPTIONAL_FILE_KEYS
                    )
                ):
                    raise ValueError(
                        f"{slug or '<unknown>'}: unexpected terrain file set"
                    )
                for record in files.values():
                    source = verify_record(source_root, record)
                    relative_path = str(record["path"])
                    if relative_path in copied_paths:
                        raise ValueError(
                            f"Duplicate terrain artifact: {relative_path}"
                        )
                    copied_paths.add(relative_path)
                    destination = build_root / relative_path
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, destination)
                    verify_record(build_root, record)
                combined_manifest["sites"].append(site)

        (build_root / "manifest.json").write_text(
            json.dumps(combined_manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        swap_output(build_root, output_root)

    return combined_manifest


def main() -> None:
    packages = discover_source_roots()
    manifest = sync_packages(packages)
    print(
        f"Copied {len(manifest['sites'])} canonical terrain packages "
        f"from {len(packages)} regions to {OUTPUT_ROOT}"
    )


if __name__ == "__main__":
    main()
