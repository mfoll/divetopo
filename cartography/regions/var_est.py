from __future__ import annotations

import argparse
import json
from pathlib import Path

from cartography.config import paths_for, validate_config
from cartography.regions.paca import validate_cached_inputs
from cartography.regions.reunion import render


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a local Var Est site package"
    )
    parser.add_argument("config", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--render-only", action="store_true")
    parser.add_argument(
        "--plan-only",
        action="store_true",
        help="Render only the two 2D plans; never create static 3D JPEGs.",
    )
    args = parser.parse_args()

    config_path = args.config.expanduser().resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    validate_config(config)
    if config.get("region") != "var-est":
        raise ValueError("The Var Est pipeline requires region='var-est'")
    paths = paths_for(config)
    validate_cached_inputs(config, paths)
    if args.check:
        print(f"Configuration and Var Est source rasters are valid: {config_path}")
        return 0
    render(config, paths, plan_only=args.plan_only)
    print(paths["output_2d"])
    print(paths["output_2d_ortho"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
