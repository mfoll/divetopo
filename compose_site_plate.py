from __future__ import annotations

import argparse
import json
from pathlib import Path

from osgeo import osr
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
TEXT_FONT = "/System/Library/Fonts/Avenir Next.ttc"


def project_path(value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else ROOT / path


def font(path: str, size: int, index: int = 0) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size, index=index)


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


def format_dms(value: float, positive: str, negative: str) -> str:
    absolute = abs(value)
    degrees = int(absolute)
    minute_value = (absolute - degrees) * 60.0
    minutes = int(minute_value)
    seconds = (minute_value - minutes) * 60.0
    direction = negative if value < 0 else positive
    return f'{degrees}° {minutes:02d}\' {seconds:04.1f}" {direction}'


def resized_width(image: Image.Image, width: int) -> Image.Image:
    height = round(width * image.height / image.width)
    return image.resize((width, height), Image.Resampling.LANCZOS)


def paste_panel(canvas: Image.Image, image: Image.Image, position: tuple[int, int]) -> None:
    x, y = position
    canvas.alpha_composite(image.convert("RGBA"), (x, y))
    draw = ImageDraw.Draw(canvas, "RGBA")
    draw.rectangle((x, y, x + image.width - 1, y + image.height - 1), outline=(22, 27, 29, 255), width=3)


def compose(config: dict, land_style: str) -> Path:
    paths = config["paths"]
    use_orthophoto = land_style == "orthophoto"
    if use_orthophoto and not config.get("orthophoto_enabled", False):
        raise ValueError("The orthophoto plate requires orthophoto_enabled=true")
    plan_key = "output_2d_ortho" if use_orthophoto else "output_2d"
    relief_key = "output_3d_ortho" if use_orthophoto else "output_3d"
    plan = Image.open(project_path(paths[plan_key])).convert("RGB")
    relief = Image.open(project_path(paths[relief_key])).convert("RGB")
    locator = Image.open(project_path(paths["output_locator"])).convert("RGB")

    canvas_width = int(config.get("plate_canvas_width_px", 5400))
    canvas_height = int(config.get("plate_canvas_height_px", 3250))
    canvas = Image.new("RGBA", (canvas_width, canvas_height), (255, 255, 255, 255))
    draw = ImageDraw.Draw(canvas, "RGBA")
    title_color = (24, 31, 35, 255)
    secondary = (77, 91, 97, 255)

    title = str(config.get("plate_title", config.get("locator_label", config["title"])))
    title_lines = [part.strip() for part in title.split(",", 1)]
    if len(title_lines) == 1:
        title_lines.append("La Réunion")
    latitude, longitude = marker_wgs84(config["locator_marker_utm40s"])
    latitude_text = format_dms(latitude, "N", "S")
    longitude_text = format_dms(longitude, "E", "O")

    title_face = font(TEXT_FONT, 280, index=8)
    place_face = font(TEXT_FONT, 112, index=2)
    coordinate_label_face = font(TEXT_FONT, 39, index=5)
    coordinate_face = font(TEXT_FONT, 105, index=8)

    title_center_x = 1840
    draw.text((title_center_x, 285), title_lines[0].upper(), anchor="mm", font=title_face, fill=title_color)

    place_y = 595
    place_bbox = draw.textbbox((0, 0), title_lines[1].upper(), font=place_face)
    place_width = place_bbox[2] - place_bbox[0]
    rule_gap = 52
    rule_length = 430
    draw.line((title_center_x - place_width / 2 - rule_gap - rule_length, place_y, title_center_x - place_width / 2 - rule_gap, place_y), fill=(24, 31, 35, 175), width=3)
    draw.line((title_center_x + place_width / 2 + rule_gap, place_y, title_center_x + place_width / 2 + rule_gap + rule_length, place_y), fill=(24, 31, 35, 175), width=3)
    draw.text((title_center_x, place_y), title_lines[1].upper(), anchor="mm", font=place_face, fill=title_color)

    latitude_x, longitude_x = 1040, 2640
    draw.text((latitude_x, 835), "LATITUDE", anchor="mm", font=coordinate_label_face, fill=secondary)
    draw.text((longitude_x, 835), "LONGITUDE", anchor="mm", font=coordinate_label_face, fill=secondary)
    draw.text((latitude_x, 1000), latitude_text, anchor="mm", font=coordinate_face, fill=title_color)
    draw.text((longitude_x, 1000), longitude_text, anchor="mm", font=coordinate_face, fill=title_color)
    draw.line((1840, 790, 1840, 1080), fill=(24, 31, 35, 130), width=3)
    draw.line((3700, 90, 3700, 1280), fill=(24, 31, 35, 175), width=3)

    side_margin = 80
    panel_gap = 40
    panel_width = (canvas_width - 2 * side_margin - panel_gap) // 2
    plan = resized_width(plan, panel_width)
    relief = resized_width(relief, panel_width)
    detail_y = canvas_height - 80 - max(plan.height, relief.height)
    paste_panel(canvas, plan, (side_margin, detail_y))
    paste_panel(canvas, relief, (side_margin + panel_width + panel_gap, detail_y))

    locator = resized_width(locator, 1500)
    locator_x = canvas_width - side_margin - locator.width
    locator_y = 50
    paste_panel(canvas, locator, (locator_x, locator_y))

    output_key = "output_plate" if use_orthophoto else "output_plate_topography"
    default_name = f"outputs/{config['slug']}-planche.jpg" if use_orthophoto else f"outputs/{config['slug']}-planche-topographique.jpg"
    output = project_path(paths.get(output_key, default_name))
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(output, quality=98, subsampling=0, optimize=True)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Assemble the 2D, 3D and locator maps into one presentation plate")
    parser.add_argument("config", type=Path, help="Site JSON configuration")
    parser.add_argument(
        "--land-style",
        choices=("orthophoto", "topography", "both"),
        default="both",
        help="Terrestrial rendering used in the detailed 2D and 3D panels",
    )
    args = parser.parse_args()
    config = json.loads(args.config.expanduser().resolve().read_text(encoding="utf-8"))
    styles = ("orthophoto", "topography") if args.land_style == "both" else (args.land_style,)
    for style in styles:
        print(compose(config, style))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
