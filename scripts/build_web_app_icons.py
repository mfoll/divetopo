#!/usr/bin/env python3
"""Build deterministic DiveTopo home-screen icons for the unified website."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PUBLIC_ROOTS = (PROJECT_ROOT / "apps" / "web" / "public",)

BACKGROUND = "#eef3f2"
TEAL = "#0e9295"
NAVY = "#061c24"
CORAL = "#ff7154"

SUPERSAMPLING = 4
MARK_DIAMETER_FRACTION = 0.72
ICON_SIZES = {
    "apple-touch-icon.png": 180,
    "app-icon-192.png": 192,
    "app-icon-512.png": 512,
}


def build_icon(size: int) -> Image.Image:
    """Rasterize the SVG mark on a safe square background."""

    canvas_size = size * SUPERSAMPLING
    mark_diameter = round(canvas_size * MARK_DIAMETER_FRACTION)
    mark_left = (canvas_size - mark_diameter) // 2
    mark_top = (canvas_size - mark_diameter) // 2
    mark_scale = mark_diameter / 128

    def point(x: float, y: float) -> tuple[int, int]:
        return (
            round(mark_left + x * mark_scale),
            round(mark_top + y * mark_scale),
        )

    canvas = Image.new("RGB", (canvas_size, canvas_size), BACKGROUND)
    mark = Image.new("RGB", (canvas_size, canvas_size), TEAL)
    mark_draw = ImageDraw.Draw(mark)
    mark_draw.polygon(
        [point(0, 96), point(128, 27), point(128, 128), point(0, 128)],
        fill=NAVY,
    )
    coral_center = point(41, 38)
    coral_radius = 18 * mark_scale
    mark_draw.ellipse(
        (
            round(coral_center[0] - coral_radius),
            round(coral_center[1] - coral_radius),
            round(coral_center[0] + coral_radius),
            round(coral_center[1] + coral_radius),
        ),
        fill=CORAL,
    )

    clip = Image.new("L", (canvas_size, canvas_size), 0)
    clip_draw = ImageDraw.Draw(clip)
    clip_draw.ellipse(
        (
            mark_left,
            mark_top,
            mark_left + mark_diameter,
            mark_top + mark_diameter,
        ),
        fill=255,
    )
    canvas.paste(mark, mask=clip)
    return canvas.resize((size, size), Image.Resampling.LANCZOS)


def main() -> None:
    icons = {filename: build_icon(size) for filename, size in ICON_SIZES.items()}
    for public_root in PUBLIC_ROOTS:
        public_root.mkdir(parents=True, exist_ok=True)
        for filename, icon in icons.items():
            icon.save(
                public_root / filename,
                format="PNG",
                optimize=False,
                compress_level=9,
            )


if __name__ == "__main__":
    main()
