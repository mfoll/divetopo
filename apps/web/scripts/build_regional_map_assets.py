#!/usr/bin/env python3
"""Build published Web assets and a manifest for one region."""

from __future__ import annotations

import argparse
from pathlib import Path

import build_paca_map_assets as builder


ROOT = Path(__file__).resolve().parents[3]
WEB_ROOT = ROOT / "apps" / "web"


def configure(region_slug: str) -> None:
    builder.REGION_SLUG = region_slug
    builder.OUTPUT_ROOT = ROOT / "regions" / region_slug / "outputs"
    builder.MANIFEST_PATH = (
        WEB_ROOT / "content" / f"{region_slug}-map-manifest.json"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("region_slug")
    args = parser.parse_args()
    configure(args.region_slug)
    builder.main()


if __name__ == "__main__":
    main()
