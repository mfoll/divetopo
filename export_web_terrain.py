from __future__ import annotations

import argparse
import gc
import json
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
from osgeo import gdal
from PIL import Image

from render_fused_relief import (
    NO_DATA_RGB,
    apply_bridge_decks,
    blend_texture,
    build_fused_surface,
    default_view_bearing,
    hillshade,
    imagery_alpha_across_shore,
    imagery_depth_alpha,
    land_palette,
    load_rgb_raster,
    open_raster,
    palette,
    smooth_depth_mask,
    soften_surface,
    strict_land_imagery_mask,
)
from site_config import (
    DEFAULT_VERTICAL_EXAGGERATION,
    ROOT,
    paths_for,
    validate_config,
)


DEFAULT_OUTPUT = ROOT / "site" / "public" / "terrain"
DEFAULT_GRID_MAX = 257
DEFAULT_TEXTURE_MAX = 2048
SCHEMA_VERSION = 1


def load_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    validate_config(config)
    return config


def fitted_dimensions(
    width: int,
    height: int,
    longest_dimension: int,
    *,
    preserve_vertices: bool = False,
) -> tuple[int, int]:
    if min(width, height, longest_dimension) < 2:
        raise ValueError("Raster and target dimensions must be at least 2 pixels")
    if max(width, height) <= longest_dimension:
        return width, height

    if preserve_vertices:
        # Heightfields cover the intervals between vertices. Scaling those
        # intervals keeps the first and last vertex exactly on the footprint.
        scale = (longest_dimension - 1) / (max(width, height) - 1)
        target_width = int(round((width - 1) * scale)) + 1
        target_height = int(round((height - 1) * scale)) + 1
    else:
        scale = longest_dimension / max(width, height)
        target_width = int(round(width * scale))
        target_height = int(round(height * scale))
    return max(2, target_width), max(2, target_height)


def resize_scalar(values: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    image = Image.fromarray(values.astype(np.float32), mode="F")
    return np.asarray(image.resize(size, Image.Resampling.BICUBIC), dtype=np.float32)


def resize_mask(mask: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    image = Image.fromarray(mask.astype(np.uint8) * 255, mode="L")
    return np.asarray(image.resize(size, Image.Resampling.NEAREST), dtype=np.uint8) > 127


def make_surface(
    config: dict[str, Any],
    paths: dict[str, Path],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    max_depth = float(config.get("max_depth_m", 20.0))
    max_land_elevation = float(config.get("max_land_elevation_m", 55.0))
    rotation_k = int(config.get("rotation_k", 0))
    coast_mode = str(config.get("coast_mode", "profile"))
    sieve = int(config.get("land_sieve_threshold_px", 200))
    (
        elevation,
        coast_y,
        land_mask,
        land_weight,
        valid,
        fused_depth,
        _contours,
        _coastlines,
    ) = build_fused_surface(
        paths["focus_depth"],
        paths["focus_elevation"],
        max_depth,
        rotation_k,
        coast_mode,
        sieve,
    )

    depth = np.clip(fused_depth, 0.0, max_depth)
    sea_mask = valid & ~land_mask
    land_blend = np.where(land_mask, land_weight, 0.0).astype(np.float32)

    sea_z = soften_surface(
        -np.nan_to_num(depth, nan=max_depth),
        sea_mask,
        passes=2,
    )
    land_z = soften_surface(
        np.clip(np.nan_to_num(elevation, nan=0.0), 0.0, max_land_elevation),
        land_mask,
        passes=10,
    )
    source = open_raster(paths["focus_depth"], "focus depth raster")
    land_z = apply_bridge_decks(
        land_z,
        source.GetGeoTransform(),
        source.RasterXSize,
        source.RasterYSize,
        rotation_k,
        1,
        config.get("bridge_decks"),
    )

    if coast_mode == "profile":
        signed_distance = (
            np.arange(land_z.shape[0], dtype=np.float32)[:, None]
            - coast_y[None, :]
        )
        land_ramp = np.clip(signed_distance / 14.0, 0.0, 1.0)
    else:
        land_ramp = np.clip((land_weight - 0.5) / 0.5, 0.0, 1.0)
    land_ramp = land_ramp * land_ramp * (3.0 - 2.0 * land_ramp)
    land_z *= land_ramp

    surface = sea_z * (1.0 - land_blend) + land_z * land_blend
    surface = np.where(land_mask, np.maximum(surface, 0.0), np.minimum(surface, 0.0))
    surface = np.where(valid, surface, -max_depth).astype(np.float32)
    return surface, depth, elevation, land_mask, land_weight, valid


def make_textures(
    config: dict[str, Any],
    paths: dict[str, Path],
    depth: np.ndarray,
    elevation: np.ndarray,
    land_mask: np.ndarray,
    land_weight: np.ndarray,
    valid: np.ndarray,
) -> tuple[Image.Image, Image.Image]:
    max_depth = float(config.get("max_depth_m", 20.0))
    max_land_elevation = float(config.get("max_land_elevation_m", 55.0))
    sea_mask = valid & ~land_mask
    land_blend = np.where(land_mask, land_weight, 0.0)

    sea_rgb = palette(
        np.nan_to_num(depth, nan=max_depth),
        max_depth=max_depth,
    ).astype(np.float32)
    sea_rgb *= hillshade(
        np.nan_to_num(depth, nan=max_depth),
        sea_mask,
        0.035,
    )[:, :, None]
    sea_rgb = np.clip(sea_rgb, 0.0, 255.0)
    land_color_z = soften_surface(
        np.clip(np.nan_to_num(elevation, nan=0.0), 0.0, max_land_elevation),
        land_mask,
        passes=2,
    )
    land_rgb = land_palette(land_color_z).astype(np.float32)

    topographic = np.broadcast_to(NO_DATA_RGB, (*depth.shape, 3)).copy()
    topographic[sea_mask] = sea_rgb[sea_mask]
    topographic = (
        topographic * (1.0 - land_blend[:, :, None])
        + land_rgb * land_blend[:, :, None]
    )
    topographic[~valid] = NO_DATA_RGB

    orthophoto = load_rgb_raster(
        paths["focus_orthophoto"],
        paths["focus_depth"],
    )
    rotation_k = int(config.get("rotation_k", 0)) % 4
    if rotation_k:
        orthophoto = np.rot90(orthophoto, rotation_k).copy()
    if orthophoto.shape[:2] != depth.shape:
        raise ValueError("Orthophoto and fused surface do not share the same dimensions")

    alpha = np.where(
        land_mask,
        np.clip((land_weight - 0.5) * 2.0, 0.0, 1.0),
        0.0,
    )
    imagery_enabled_at_sea = any(
        config.get(key) is not None
        for key in (
            "imagery_sea_depth_m",
            "imagery_sea_full_depth_m",
            "imagery_sea_max_depth_m",
        )
    )
    if imagery_enabled_at_sea:
        source = open_raster(paths["focus_depth"], "focus depth raster")
        pixel_m = abs(source.GetGeoTransform()[1])
        imagery_depth = smooth_depth_mask(
            depth,
            float(config.get("imagery_sea_smoothing_m", 0.0)),
            pixel_m,
        )
        sea_alpha = imagery_depth_alpha(
            imagery_depth,
            config.get("imagery_sea_depth_m"),
            float(config.get("imagery_sea_feather_m", 0.6)),
            config.get("imagery_sea_full_depth_m"),
            config.get("imagery_sea_max_depth_m"),
        )
        assert sea_alpha is not None
        alpha = imagery_alpha_across_shore(land_mask, sea_alpha)
    else:
        alpha = np.minimum(alpha, strict_land_imagery_mask(land_mask))
    alpha = np.where(valid, alpha, 0.0).astype(np.float32)

    orthophoto_composite = blend_texture(topographic, orthophoto, alpha)
    orthophoto_composite[~valid] = NO_DATA_RGB
    return (
        Image.fromarray(np.clip(topographic, 0, 255).astype(np.uint8), "RGB"),
        Image.fromarray(
            np.clip(orthophoto_composite, 0, 255).astype(np.uint8),
            "RGB",
        ),
    )


def source_attribution(config: dict[str, Any], *, orthophoto: bool) -> str:
    text = (
        "Bathymétrie : Projet HYSCORES (Ifremer, UBO, Office de l'Eau "
        "Réunion), 2015, incluant Litto3D · Topographie : IGN RGE ALTI, "
        "mise à jour arrêtée en 2024"
    )
    if orthophoto:
        capture_date = date.fromisoformat(str(config["orthophoto_capture_date"]))
        text += (
            " · Orthophoto : IGN BD ORTHO, prise de vue "
            f"{capture_date.strftime('%d-%m-%Y')}"
        )
    return text


def export_site(
    config_path: Path,
    output_root: Path,
    grid_max: int,
    texture_max: int,
) -> dict[str, Any]:
    config = load_config(config_path)
    if not config.get("orthophoto_enabled", False):
        raise ValueError(f"{config['slug']} does not provide an orthophoto")
    paths = paths_for(config)
    for key in ("focus_depth", "focus_elevation", "focus_orthophoto"):
        if not paths[key].is_file():
            raise FileNotFoundError(f"Missing cached {key}: {paths[key]}")

    surface, depth, elevation, land_mask, land_weight, valid = make_surface(
        config,
        paths,
    )
    topographic_texture, orthophoto_texture = make_textures(
        config,
        paths,
        depth,
        elevation,
        land_mask,
        land_weight,
        valid,
    )

    slug = str(config["slug"])
    site_output = output_root / slug
    site_output.mkdir(parents=True, exist_ok=True)

    grid_size = fitted_dimensions(
        surface.shape[1],
        surface.shape[0],
        grid_max,
        preserve_vertices=True,
    )
    grid_surface = resize_scalar(surface, grid_size)
    grid_valid = resize_mask(valid, grid_size)
    grid_land = resize_mask(land_mask, grid_size)
    max_depth = float(config.get("max_depth_m", 20.0))
    max_land_elevation = float(config.get("max_land_elevation_m", 55.0))
    grid_surface = np.where(
        grid_land,
        np.clip(grid_surface, 0.0, max_land_elevation),
        np.clip(grid_surface, -max_depth, 0.0),
    )
    finite = grid_valid & np.isfinite(grid_surface)
    if not np.any(finite):
        raise ValueError(f"{slug} has no valid terrain vertices")
    minimum = float(np.min(grid_surface[finite]))
    maximum = float(np.max(grid_surface[finite]))
    if maximum <= minimum:
        raise ValueError(f"{slug} has a constant terrain surface")
    scale = (maximum - minimum) / 65535.0
    encoded = np.rint((grid_surface - minimum) / scale)
    encoded = np.clip(encoded, 0, 65535).astype("<u2")
    encoded[~grid_valid] = 0
    (site_output / "height.bin").write_bytes(encoded.tobytes(order="C"))
    packed_mask = np.packbits(
        grid_valid.reshape(-1),
        bitorder="little",
    )
    (site_output / "valid-mask.bin").write_bytes(packed_mask.tobytes())

    texture_size = fitted_dimensions(
        topographic_texture.width,
        topographic_texture.height,
        texture_max,
    )
    if topographic_texture.size != texture_size:
        topographic_texture = topographic_texture.resize(
            texture_size,
            Image.Resampling.LANCZOS,
        )
        orthophoto_texture = orthophoto_texture.resize(
            texture_size,
            Image.Resampling.LANCZOS,
        )
    topographic_texture.save(
        site_output / "topographic.webp",
        "WEBP",
        quality=90,
        method=6,
    )
    orthophoto_texture.save(
        site_output / "orthophoto.webp",
        "WEBP",
        quality=84,
        method=6,
    )

    source = open_raster(paths["focus_depth"], "focus depth raster")
    transform = source.GetGeoTransform()
    raster_west = float(transform[0])
    raster_north = float(transform[3])
    raster_east = raster_west + source.RasterXSize * float(transform[1])
    raster_south = raster_north + source.RasterYSize * float(transform[5])
    west, east = sorted((raster_west, raster_east))
    south, north = sorted((raster_south, raster_north))
    rotation_k = int(config.get("rotation_k", 0)) % 4
    view_bearing_deg = float(
        config.get("view_bearing_deg", default_view_bearing(rotation_k))
    ) % 360.0
    physical_width = east - west
    physical_depth = north - south
    if rotation_k % 2:
        physical_width, physical_depth = physical_depth, physical_width

    author = str(config.get("plate_author", "")).strip()
    year = int(config.get("copyright_year", 2026))
    license_name = str(config.get("map_license", "")).strip()
    copyright_text = f"© {year} {author}".strip()
    if license_name:
        copyright_text += f" · {license_name}"
    attribution_topographic = source_attribution(config, orthophoto=False)
    attribution_orthophoto = source_attribution(config, orthophoto=True)
    metadata = {
        "schemaVersion": SCHEMA_VERSION,
        "slug": slug,
        "title": str(config.get("plate_title", config["title"])),
        "crs": "EPSG:32740",
        "sourceBboxUtm40s": {
            "west": round(west, 3),
            "south": round(south, 3),
            "east": round(east, 3),
            "north": round(north, 3),
        },
        "physicalSizeM": {
            "width": round(physical_width, 3),
            "depth": round(physical_depth, 3),
        },
        "orientation": {
            "sourceRows": "north-to-south",
            "sourceColumns": "west-to-east",
            "rotationQuarterTurnsCounterClockwise": rotation_k,
            "textureUvOrigin": "northwest",
        },
        "grid": {
            "width": grid_size[0],
            "height": grid_size[1],
            "triangleCount": 2 * (grid_size[0] - 1) * (grid_size[1] - 1),
            "layout": "row-major",
            "rowOrder": "north-to-south",
            "columnOrder": "west-to-east",
            "heightFile": "height.bin",
            "heightEncoding": {
                "type": "uint16",
                "byteOrder": "little-endian",
                "offsetM": minimum,
                "scaleMPerUnit": scale,
                "formula": "elevationM = offsetM + rawUint16 * scaleMPerUnit",
            },
            "validMaskFile": "valid-mask.bin",
            "validMaskEncoding": {
                "type": "bitset",
                "bitOrder": "least-significant-bit-first",
                "formula": "(byte[index >> 3] >> (index & 7)) & 1",
            },
        },
        "elevationRangeM": {
            "min": minimum,
            "max": maximum,
        },
        "heightValues": "physical metres before vertical exaggeration",
        "verticalExaggeration": float(
            config.get("vertical_exaggeration", DEFAULT_VERTICAL_EXAGGERATION)
        ),
        "view": {
            "lookBearingDeg": view_bearing_deg,
            "gridLookBearingDeg": (
                view_bearing_deg - 90.0 * rotation_k
            ) % 360.0,
            "cameraTilt": float(config.get("camera_tilt", 0.34)),
            "alongViewProjectionScale": float(
                config.get("along_view_projection_scale", 1.0)
            ),
            "visibleWidthM": float(
                config.get("view_visible_width_m", physical_width)
            ),
            "coastFrameFraction": (
                float(config.get("coast_frame_fraction", 0.44))
                - float(config.get("view_top_crop_fraction", 0.0))
            )
            / (
                1.0
                - float(config.get("view_top_crop_fraction", 0.0))
            ),
        },
        "textures": {
            "width": texture_size[0],
            "height": texture_size[1],
            "topographic": {
                "file": "topographic.webp",
                "attribution": attribution_topographic,
            },
            "orthophoto": {
                "file": "orthophoto.webp",
                "captureDate": str(config["orthophoto_capture_date"]),
                "attribution": attribution_orthophoto,
            },
        },
        "credits": {
            "copyright": copyright_text,
            "license": license_name,
            "requiredDisplay": f"{copyright_text} · {attribution_orthophoto}",
        },
    }
    (site_output / "terrain.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    build_fused_surface.cache_clear()
    del surface, depth, elevation, land_mask, land_weight, valid
    gc.collect()
    return {
        "slug": slug,
        "title": metadata["title"],
        "metadata": f"{slug}/terrain.json",
    }


def validate_export(output_root: Path, manifest: dict[str, Any]) -> None:
    for item in manifest["sites"]:
        metadata_path = output_root / item["metadata"]
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        grid = metadata["grid"]
        vertex_count = int(grid["width"]) * int(grid["height"])
        height_path = metadata_path.parent / grid["heightFile"]
        mask_path = metadata_path.parent / grid["validMaskFile"]
        if height_path.stat().st_size != vertex_count * 2:
            raise ValueError(f"Unexpected height payload size: {height_path}")
        if mask_path.stat().st_size != (vertex_count + 7) // 8:
            raise ValueError(f"Unexpected validity payload size: {mask_path}")
        textures = metadata["textures"]
        if max(int(textures["width"]), int(textures["height"])) > DEFAULT_TEXTURE_MAX:
            raise ValueError(f"Texture exceeds the mobile payload contract: {metadata_path}")
        for style in ("topographic", "orthophoto"):
            texture_path = metadata_path.parent / textures[style]["file"]
            with Image.open(texture_path) as image:
                if image.size != (int(textures["width"]), int(textures["height"])):
                    raise ValueError(f"Texture dimensions do not match metadata: {texture_path}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Export compact heightfields and matched map textures for the "
            "interactive web terrain viewer."
        )
    )
    parser.add_argument(
        "configs",
        nargs="*",
        type=Path,
        help="Site JSON files (defaults to every sites/*.json file)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Asset directory (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--grid-max",
        type=int,
        default=DEFAULT_GRID_MAX,
        help="Maximum heightfield dimension (default: 257)",
    )
    parser.add_argument(
        "--texture-max",
        type=int,
        default=DEFAULT_TEXTURE_MAX,
        help="Maximum texture dimension (default: 2048)",
    )
    args = parser.parse_args()
    if not 3 <= args.grid_max <= DEFAULT_GRID_MAX:
        parser.error(f"--grid-max must be between 3 and {DEFAULT_GRID_MAX}")
    if not 256 <= args.texture_max <= DEFAULT_TEXTURE_MAX:
        parser.error(f"--texture-max must be between 256 and {DEFAULT_TEXTURE_MAX}")

    configs = args.configs or sorted((ROOT / "sites").glob("*.json"))
    if not configs:
        parser.error("No site configurations found")
    output_root = args.output.expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    sites = [
        export_site(
            path.expanduser().resolve(),
            output_root,
            args.grid_max,
            args.texture_max,
        )
        for path in configs
    ]
    manifest = {
        "schemaVersion": SCHEMA_VERSION,
        "sites": sites,
    }
    (output_root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    validate_export(output_root, manifest)
    for item in sites:
        print(output_root / item["metadata"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
