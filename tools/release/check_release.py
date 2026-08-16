#!/usr/bin/env python3
"""Verify that the declared release scope is fully published and packaged."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "release-contract.json"
REQUIRED_MAP_FILES = {
    "maps/2d-orthophoto.jpg",
    "maps/2d-topographic.jpg",
    "maps/3d-dynamic-orthophoto-1600.webp",
    "maps/3d-dynamic-orthophoto-2474.webp",
    "maps/3d-dynamic-orthophoto-960.webp",
    "maps/3d-dynamic-orthophoto-mobile-960.webp",
    "maps/3d-dynamic-topographic-1600.webp",
    "maps/3d-dynamic-topographic-2474.webp",
    "maps/3d-dynamic-topographic-960.webp",
    "maps/3d-dynamic-topographic-mobile-960.webp",
    "maps/downloads/3d-dynamic-orthophoto-full.jpg",
    "maps/downloads/3d-dynamic-topographic-full.jpg",
    "maps/planche-orthophoto-1800.webp",
    "maps/planche-topographic-1800.webp",
}
REQUIRED_TERRAIN_FILES = {
    "height.bin",
    "isobath-mask.bin",
    "isobaths-vector.json",
    "orthophoto.webp",
    "terrain.json",
    "topographic.webp",
    "valid-mask.bin",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def relative_files(root: Path) -> set[str]:
    if not root.is_dir():
        return set()
    return {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    }


def validate_release(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    contract = load_json(root / "release-contract.json")
    version = str(contract["version"])
    notes_path = root / str(contract["releaseNotes"])
    if not notes_path.is_file():
        errors.append(f"release notes missing: {notes_path.relative_to(root)}")
        notes = ""
    else:
        notes = notes_path.read_text(encoding="utf-8")
    required_heading = str(contract["requiredNotesHeading"])
    if required_heading not in notes:
        errors.append(f"release notes missing heading: {required_heading}")

    version_sources = (
        root / "apps/web/content/routing.ts",
        root / "apps/web/scripts/build_map_assets.py",
        root / "apps/web/scripts/build_paca_map_assets.py",
    )
    for source in version_sources:
        if version not in source.read_text(encoding="utf-8"):
            errors.append(f"{source.relative_to(root)} does not target {version}")

    global_terrain = load_json(root / "apps/web/public/terrain/manifest.json")
    global_terrain_slugs = {
        str(site.get("slug")) for site in global_terrain.get("sites", [])
    }

    for target in contract["requiredPublishedSites"]:
        region = str(target["region"])
        slug = str(target["slug"])
        display_name = str(target["displayName"])
        identity = f"{region}/{slug}"
        if display_name not in notes:
            errors.append(f"release notes do not name {display_name}")

        region_data = load_json(root / "regions" / region / "region.json")
        inventory = {
            str(site.get("slug")): site for site in region_data.get("sites", [])
        }
        entry = inventory.get(slug)
        if entry is None:
            errors.append(f"{identity}: missing from regional inventory")
            continue
        if entry.get("publication") in {"pending", "preparing", "draft"}:
            errors.append(f"{identity}: regional publication is not final")
        if entry.get("artifacts", {}).get("status") in {
            "pending",
            "preparing",
            "draft",
        }:
            errors.append(f"{identity}: regional artifacts are not complete")

        config = load_json(root / str(entry["config"]))
        if config.get("web", {}).get("published") is not True:
            errors.append(f"{identity}: web.published is not true")

        manifest = load_json(
            root / "apps" / "web" / "content" / f"{region}-map-manifest.json"
        )
        published = {
            str(site.get("slug")) for site in manifest.get("sites", [])
        }
        planned = {
            str(site.get("slug")): site
            for site in manifest.get("plannedSites", [])
        }
        if slug not in published:
            errors.append(f"{identity}: absent from published regional manifest")
        if planned.get(slug, {}).get("status") != "published":
            errors.append(f"{identity}: planned-site status is not published")

        map_root = root / "apps" / "web" / "public" / "maps" / region / slug
        missing_maps = sorted(REQUIRED_MAP_FILES - relative_files(map_root))
        if missing_maps:
            errors.append(f"{identity}: missing Web maps: {missing_maps}")

        terrain_root = root / "apps" / "web" / "public" / "terrain" / slug
        missing_terrain = sorted(
            REQUIRED_TERRAIN_FILES - relative_files(terrain_root)
        )
        if missing_terrain:
            errors.append(f"{identity}: missing Web terrain: {missing_terrain}")
        if slug not in global_terrain_slugs:
            errors.append(f"{identity}: absent from global terrain manifest")

    return errors


def main() -> None:
    errors = validate_release()
    if errors:
        raise SystemExit("Release contract failed:\n- " + "\n- ".join(errors))
    contract = load_json(CONTRACT_PATH)
    print(
        f"Release contract {contract['version']} passes for "
        f"{len(contract['requiredPublishedSites'])} required sites"
    )


if __name__ == "__main__":
    main()
