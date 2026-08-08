#!/usr/bin/env python3
"""Refresh the lightweight five-site inventory in regional Web manifests."""

from __future__ import annotations

import json

import build_paca_map_assets as builder


REGIONS = (
    "bouches-du-rhone",
    "var-ouest",
    "var-centre",
    "var-est",
    "alpes-maritimes",
)


def main() -> None:
    for region_slug in REGIONS:
        manifest_path = (
            builder.WEB_ROOT / "content" / f"{region_slug}-map-manifest.json"
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        bounds = manifest["westCoastLocator"].get("boundsWgs84")
        if not isinstance(bounds, dict):
            raise ValueError(f"{region_slug}: regional locator requires WGS84 bounds")
        configs = builder.load_region_configs(builder.REPOSITORY_ROOT, region_slug)
        manifest["plannedSites"] = [
            builder.build_planned_site(config, bounds) for config in configs
        ]
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Updated {manifest_path} with {len(configs)} planned sites")


if __name__ == "__main__":
    main()
