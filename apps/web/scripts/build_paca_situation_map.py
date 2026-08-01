#!/usr/bin/env python3
"""Build the data-backed France situation map used by the PACA picker.

The background is the same version-pinned GEBCO WMS layer used by the
regional PACA relief: ``GEBCO_2024`` from the 2024 service.  The metropolitan
outline is read from Natural Earth's 10m Admin 0 countries data at build time;
it is not a hand-drawn or hand-simplified polygon.  Corsica is outside the
map frame so the Côte d'Azur extent remains readable.

The WMS already contains the terrain and bathymetric structure.  A small,
fixed land-only RGB grade keeps the map in the green/yellow land and blue sea
palette of the existing PACA regional raster without replacing the source
relief with a synthetic gradient.  The only graphic overlays are the real
metropolitan France coastline and the unlabeled Côte d'Azur extent rectangle,
matching the clean Réunion situation-map style.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
from osgeo import ogr
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "apps" / "web" / "public" / "maps" / "paca" / "france-metropolitan-situation.png"
SOURCE_CACHE = ROOT / ".tmp" / "paca-situation-map"

WIDTH, HEIGHT = 1000, 840
SCALE = 3

# The east edge is just beyond metropolitan France (Natural Earth reaches
# about 8.2°E here).  This keeps Corsica out of the frame while keeping the
# French Mediterranean coast readable in the situation view.
MAP_BOUNDS = (-5.5, 42.0, 8.7, 51.3)
LOCAL_BOUNDS = (5.65, 42.82, 7.0, 43.58)

GEBCO_WMS = "https://wms.gebco.net/2024/mapserv"
GEBCO_LAYER = "GEBCO_2024"
NATURAL_EARTH_ZIP = "https://naturalearth.s3.amazonaws.com/10m_cultural/ne_10m_admin_0_countries.zip"
NATURAL_EARTH_VERSION = "5.1.1"
NATURAL_EARTH_SHA256 = "ce1ac7036499a0edd641fbc093cd209a98f96a49d2eca8480aaacad35138a7f6"

# Columns are output channels; rows are input RGB channels.  This grade was
# calibrated once against the existing PACA regional raster.  It is applied
# only inside real country polygons; GEBCO sea pixels remain untouched.
LAND_GRADE_MATRIX = np.array(
    [
        [0.96896654, 0.179651594, 0.273949613],
        [-0.531720537, -0.026870366, -0.047987598],
        [-0.185126107, 0.166799996, -0.014648884],
    ],
    dtype=np.float32,
)
LAND_GRADE_OFFSET = np.array([125.549314, 153.529068, 100.267078], dtype=np.float32)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".part")
    temporary.unlink(missing_ok=True)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "DiveTopo PACA map generator/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            with temporary.open("wb") as handle:
                shutil.copyfileobj(response, handle)
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)


def ensure_source(url: str, output: Path, *, expected_sha256: str | None = None, refresh: bool) -> Path:
    if refresh or not output.is_file():
        download(url, output)
    if expected_sha256 is not None and sha256(output) != expected_sha256:
        raise ValueError(f"Unexpected source checksum for {output}")
    return output


def gebco_url() -> str:
    west, south, east, north = MAP_BOUNDS
    query = urllib.parse.urlencode(
        {
            "SERVICE": "WMS",
            "VERSION": "1.1.1",
            "REQUEST": "GetMap",
            "LAYERS": GEBCO_LAYER,
            "STYLES": "default",
            "SRS": "EPSG:4326",
            "BBOX": f"{west:.8f},{south:.8f},{east:.8f},{north:.8f}",
            "WIDTH": WIDTH,
            "HEIGHT": HEIGHT,
            "FORMAT": "image/png",
        }
    )
    return f"{GEBCO_WMS}?{query}"


def extract_natural_earth(zip_path: Path) -> Path:
    extracted = SOURCE_CACHE / "natural-earth-10m"
    shp = extracted / "ne_10m_admin_0_countries.shp"
    if shp.is_file():
        return shp
    extracted.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        required = {
            "ne_10m_admin_0_countries.shp",
            "ne_10m_admin_0_countries.shx",
            "ne_10m_admin_0_countries.dbf",
            "ne_10m_admin_0_countries.prj",
        }
        names = {Path(name).name: name for name in archive.namelist()}
        missing = sorted(required - set(names))
        if missing:
            raise ValueError(f"Natural Earth archive is missing {missing}")
        for name in required:
            destination = extracted / name
            with archive.open(names[name]) as source, destination.open("wb") as target:
                shutil.copyfileobj(source, target)
    return shp


def project(longitude: float, latitude: float, *, scale: int = 1) -> tuple[float, float]:
    west, south, east, north = MAP_BOUNDS
    return (
        (longitude - west) / (east - west) * WIDTH * scale,
        (north - latitude) / (north - south) * HEIGHT * scale,
    )


def iter_polygons(geometry: ogr.Geometry):
    name = geometry.GetGeometryName().upper()
    if name == "POLYGON":
        yield geometry
    elif name in {"MULTIPOLYGON", "GEOMETRYCOLLECTION"}:
        for index in range(geometry.GetGeometryCount()):
            yield from iter_polygons(geometry.GetGeometryRef(index))


def ring_points(ring: ogr.Geometry, *, scale: int) -> list[tuple[float, float]]:
    return [
        project(ring.GetX(index), ring.GetY(index), scale=scale)
        for index in range(ring.GetPointCount())
    ]


def geometry_mask(features: list[tuple[str, ogr.Geometry]]) -> Image.Image:
    mask = Image.new("L", (WIDTH, HEIGHT), 0)
    draw = ImageDraw.Draw(mask)
    for _name, geometry in features:
        for polygon in iter_polygons(geometry):
            if polygon.GetGeometryCount() == 0:
                continue
            draw.polygon(ring_points(polygon.GetGeometryRef(0), scale=1), fill=255)
            for index in range(1, polygon.GetGeometryCount()):
                draw.polygon(ring_points(polygon.GetGeometryRef(index), scale=1), fill=0)
    return mask


def load_country_features(shp: Path) -> list[tuple[str, ogr.Geometry]]:
    ogr.UseExceptions()
    dataset = ogr.Open(str(shp))
    if dataset is None:
        raise RuntimeError(f"Cannot open Natural Earth data: {shp}")
    layer = dataset.GetLayer(0)
    features: list[tuple[str, ogr.Geometry]] = []
    for feature in layer:
        geometry = feature.GetGeometryRef()
        if geometry is not None:
            features.append((str(feature.GetField("NAME") or ""), geometry.Clone()))
    dataset = None
    if not features:
        raise ValueError("Natural Earth country layer is empty")
    return features


def metropolitan_outline(features: list[tuple[str, ogr.Geometry]]) -> ogr.Geometry:
    candidates: list[ogr.Geometry] = []
    for name, geometry in features:
        if name != "France":
            continue
        for polygon in iter_polygons(geometry):
            min_x, max_x, min_y, max_y = polygon.GetEnvelope()
            if min_x < -4.0 and max_x > 7.5 and min_y > 40.0 and max_y > 50.0:
                candidates.append(polygon.Clone())
    if not candidates:
        raise ValueError("Natural Earth metropolitan France component not found")
    return max(candidates, key=lambda geometry: geometry.GetArea())


def grade_land(raw: Image.Image, land_mask: Image.Image) -> Image.Image:
    # Float64 avoids spurious Accelerate/BLAS overflow warnings on macOS when
    # this small matrix is applied to a non-contiguous Pillow view.
    pixels = np.asarray(raw.convert("RGB"), dtype=np.float64)
    flat = pixels.reshape(-1, 3)
    graded = np.clip(flat @ LAND_GRADE_MATRIX + LAND_GRADE_OFFSET, 0, 255)
    mask = np.asarray(land_mask, dtype=bool).reshape(-1)
    flat[mask] = graded[mask]
    return Image.fromarray(pixels.astype(np.uint8), mode="RGB")


def draw_map(raw: Image.Image, features: list[tuple[str, ogr.Geometry]]) -> Image.Image:
    image = grade_land(raw, geometry_mask(features)).resize(
        (WIDTH * SCALE, HEIGHT * SCALE), Image.Resampling.BICUBIC
    ).convert("RGBA")
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")

    local_west, local_south, local_east, local_north = LOCAL_BOUNDS
    rectangle = [
        project(local_west, local_north, scale=SCALE),
        project(local_east, local_north, scale=SCALE),
        project(local_east, local_south, scale=SCALE),
        project(local_west, local_south, scale=SCALE),
    ]
    draw.polygon(rectangle, fill=(255, 113, 84, 38))
    draw.line(
        rectangle + [rectangle[0]],
        fill=(255, 113, 84, 255),
        width=3 * SCALE,
        joint="curve",
    )

    # Draw the real coastline last so it stays legible through the translucent
    # extent fill and at the responsive display size.
    france = metropolitan_outline(features)
    for polygon in iter_polygons(france):
        for index in range(polygon.GetGeometryCount()):
            draw.line(
                ring_points(polygon.GetGeometryRef(index), scale=SCALE),
                fill=(10, 70, 82, 225),
                width=2 * SCALE,
                joint="curve",
            )

    return Image.alpha_composite(image, overlay).resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true", help="redownload the versioned source assets")
    args = parser.parse_args()

    wms_path = ensure_source(
        gebco_url(),
        SOURCE_CACHE / "france-gebco-2024.png",
        refresh=args.refresh,
    )
    natural_earth_zip = ensure_source(
        NATURAL_EARTH_ZIP,
        SOURCE_CACHE / "ne_10m_admin_0_countries.zip",
        expected_sha256=NATURAL_EARTH_SHA256,
        refresh=args.refresh,
    )
    features = load_country_features(extract_natural_earth(natural_earth_zip))
    with Image.open(wms_path) as raw:
        if raw.size != (WIDTH, HEIGHT):
            raise ValueError(f"Unexpected GEBCO WMS dimensions: {raw.size}")
        image = draw_map(raw, features)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(OUTPUT, format="PNG", optimize=True)
    print(f"GEBCO source: {gebco_url()}")
    print(f"Natural Earth source: {NATURAL_EARTH_ZIP} (v{NATURAL_EARTH_VERSION})")
    print(f"Output: {OUTPUT} ({WIDTH}x{HEIGHT}, {OUTPUT.stat().st_size} bytes, sha256={sha256(OUTPUT)})")


if __name__ == "__main__":
    main()
