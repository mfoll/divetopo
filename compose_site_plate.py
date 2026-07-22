from __future__ import annotations

import argparse
import json
from pathlib import Path

from osgeo import osr
from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parent
TITLE_FONT = "/System/Library/Fonts/NewYork.ttf"
TEXT_FONT = "/System/Library/Fonts/Avenir Next.ttc"


def project_path(value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else ROOT / path


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def marker_wgs84(marker: list[float]) -> tuple[float, float]:
    projected = osr.SpatialReference()
    projected.ImportFromEPSG(32740)
    projected.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    geographic = osr.SpatialReference()
    geographic.ImportFromEPSG(4326)
    geographic.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    transform = osr.CoordinateTransformation(projected, geographic)
    longitude, latitude, _ = transform.TransformPoint(float(marker[0]), float(marker[1]))
    return latitude, longitude


def resized_width(image: Image.Image, width: int) -> Image.Image:
    height = round(width * image.height / image.width)
    return image.resize((width, height), Image.Resampling.LANCZOS)


def paste_panel(canvas: Image.Image, image: Image.Image, position: tuple[int, int]) -> None:
    x, y = position
    shadow_margin = 28
    shadow = Image.new("RGBA", (image.width + 2 * shadow_margin, image.height + 2 * shadow_margin), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rectangle(
        (shadow_margin, shadow_margin, shadow_margin + image.width, shadow_margin + image.height),
        fill=(0, 0, 0, 175),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    canvas.alpha_composite(shadow, (x - shadow_margin + 10, y - shadow_margin + 14))
    canvas.alpha_composite(image.convert("RGBA"), (x, y))
    draw = ImageDraw.Draw(canvas, "RGBA")
    draw.rectangle((x, y, x + image.width - 1, y + image.height - 1), outline=(234, 229, 211, 205), width=3)


def compose(config: dict) -> Path:
    paths = config["paths"]
    plan_key = "output_2d_ortho" if config.get("orthophoto_enabled", False) else "output_2d"
    relief_key = "output_3d_ortho" if config.get("orthophoto_enabled", False) else "output_3d"
    plan = Image.open(project_path(paths[plan_key])).convert("RGB")
    relief = Image.open(project_path(paths[relief_key])).convert("RGB")
    locator = Image.open(project_path(paths["output_locator"])).convert("RGB")

    canvas_width, canvas_height = 5400, 3700
    canvas = Image.new("RGBA", (canvas_width, canvas_height), (9, 20, 28, 255))
    draw = ImageDraw.Draw(canvas, "RGBA")
    title_color = (244, 239, 224, 255)
    secondary = (177, 200, 205, 255)

    title = str(config.get("plate_title", f"{config.get('locator_label', config['title'])}, La Reunion"))
    author = str(config.get("plate_author", ""))
    latitude, longitude = marker_wgs84(config["locator_marker_utm40s"])
    subtitle = f"{abs(latitude):.5f}° {'S' if latitude < 0 else 'N'}  ·  {abs(longitude):.5f}° {'O' if longitude < 0 else 'E'}"

    title_face = font(TITLE_FONT, 174)
    subtitle_face = font(TEXT_FONT, 58)
    footer_face = font(TEXT_FONT, 34)
    draw.text((canvas_width / 2, 142), title, anchor="mm", font=title_face, fill=title_color)
    draw.text((canvas_width / 2, 300), subtitle, anchor="mm", font=subtitle_face, fill=secondary)
    draw.line((160, 395, canvas_width - 160, 395), fill=(176, 198, 200, 95), width=2)

    side_margin = 160
    panel_gap = 72
    panel_width = (canvas_width - 2 * side_margin - panel_gap) // 2
    plan = resized_width(plan, panel_width)
    relief = resized_width(relief, panel_width)
    top_y = 470
    paste_panel(canvas, plan, (side_margin, top_y))
    paste_panel(canvas, relief, (side_margin + panel_width + panel_gap, top_y))

    locator = resized_width(locator, 1550)
    locator_x = (canvas_width - locator.width) // 2
    locator_y = 2285
    paste_panel(canvas, locator, (locator_x, locator_y))

    source_note = "HYSCORES Ifremer · RGE ALTI et orthophoto IGN · Relief marin GEBCO"
    draw.text((160, canvas_height - 55), source_note, anchor="ls", font=footer_face, fill=(145, 169, 174, 220))
    if author:
        draw.text((canvas_width - 160, canvas_height - 55), f"© {author}", anchor="rs", font=footer_face, fill=title_color)

    output = project_path(paths.get("output_plate", f"outputs/{config['slug']}-planche.jpg"))
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(output, quality=98, subsampling=0, optimize=True)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Assemble the 2D, 3D and locator maps into one presentation plate")
    parser.add_argument("config", type=Path, help="Site JSON configuration")
    args = parser.parse_args()
    config = json.loads(args.config.expanduser().resolve().read_text(encoding="utf-8"))
    print(compose(config))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
