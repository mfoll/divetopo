#!/usr/bin/env python3
"""Build the PACA site-picker relief with Shom–IGN and EMODnet bathymetry.

Shom–IGN Litto3D PACA 2015 MNT5m tiles are used around the five site areas.
The EMODnet Bathymetry DTM 2024 is the offshore/background bathymetry, with
GEBCO 2024 retained only as a no-data fallback. IGN RGE ALTI remains the land
relief source. The official Shom–IGN Limite terre-mer vector is rasterized
once into the shared land mask and coastline edge, so the fill and the visible
coastline cannot diverge. No blur is applied across the coast.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import math
import shutil
import subprocess
import time
import urllib.parse
import urllib.request
import zipfile
import zlib
from pathlib import Path

import numpy as np
from osgeo import gdal, ogr, osr
from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[3]
WEB_ROOT = ROOT / "apps" / "web"
OUTPUT = WEB_ROOT / "public" / "maps" / "paca" / "paca-regional-relief.png"
MANIFEST = WEB_ROOT / "content" / "paca-map-manifest.json"
CACHE = ROOT / ".tmp" / "paca-regional-relief"
SITE_CONFIG_DIR = ROOT / "regions" / "paca" / "sites"
REGION_SLUG = "paca"
NATURAL_EARTH_ZIP = (
    "https://naturalearth.s3.amazonaws.com/10m_cultural/"
    "ne_10m_admin_0_countries.zip"
)
NATURAL_EARTH_SHA256 = (
    "ce1ac7036499a0edd641fbc093cd209a98f96a49d2eca8480aaacad35138a7f6"
)

WIDTH, HEIGHT = 1864, 1440
MAP_BOUNDS = (5.65, 42.82, 7.0, 43.58)

GEBCO_WMS = "https://wms.gebco.net/2024/mapserv"
GEBCO_LAYER = "GEBCO_2024"
EMODNET_WCS = "https://ows.emodnet-bathymetry.eu/wcs"
EMODNET_COVERAGE = "emodnet:mean"
EMODNET_CELL_DEG = 1.0 / 16.0 / 60.0
EMODNET_REQUEST_WIDTH = round((MAP_BOUNDS[2] - MAP_BOUNDS[0]) / EMODNET_CELL_DEG)
EMODNET_REQUEST_HEIGHT = round((MAP_BOUNDS[3] - MAP_BOUNDS[1]) / EMODNET_CELL_DEG)
LITTO3D_GROUP_URL = (
    "https://services.data.shom.fr/INSPIRE/telechargement/"
    "prepackageGroup/LITTO3D_PACA_2015_PACK_DL"
)
LITTO3D_CRS = "EPSG:2154"
LITTO3D_NODATA = -99999.0
LITTO3D_CELL_SIZE_M = 5.0
LIMTM_WFS_ENDPOINT = "https://services.data.shom.fr/INSPIRE/wfs"
LIMTM_WFS_TYPENAME = (
    "LIMTM_2154_WFS:limite_terre_mer_france_metropolitaine_ligne"
)
LIMTM_LINE_WIDTH_PX = 2.0
LIMTM_CLOSE_RADIUS_PX = 2
LIMTM_ISOLATED_COMPONENT_MAX_PX = 96
RGE_WMTS = "https://data.geopf.fr/wmts"
RGE_LAYER = "ELEVATION.ELEVATIONGRIDCOVERAGE.HIGHRES"
RGE_TILE_MATRIX_SET = "WGS84G_6_14"
RGE_ZOOM = 11
TILE_SIZE = 256
RGE_VALID_MIN_M = -100.0
SHOM_COAST_BAND_PX = 12
SHOM_EDGE_FEATHER_PX = 3.0
SHOM_MARINE_BLEND = 0.65


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def decode_response(data: bytes, encoding: str) -> bytes:
    if not encoding:
        return data
    if "gzip" in encoding:
        return zlib.decompress(data, 31)
    if "deflate" in encoding:
        return zlib.decompress(data)
    raise RuntimeError(f"Unsupported HTTP content encoding: {encoding}")


def download(url: str, output: Path, *, refresh: bool) -> None:
    if output.is_file() and not refresh:
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "DiveTopo PACA regional relief/1.0"},
    )
    temporary = output.with_suffix(output.suffix + ".part")
    temporary.unlink(missing_ok=True)
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            encoding = response.headers.get("Content-Encoding", "")
            if encoding:
                temporary.write_bytes(decode_response(response.read(), encoding))
            else:
                with temporary.open("wb") as stream:
                    shutil.copyfileobj(response, stream, length=1024 * 1024)
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)


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


def emodnet_url() -> str:
    west, south, east, north = MAP_BOUNDS
    query = urllib.parse.urlencode(
        {
            "service": "WCS",
            "version": "1.0.0",
            "request": "GetCoverage",
            "coverage": EMODNET_COVERAGE,
            "bbox": f"{west:.8f},{south:.8f},{east:.8f},{north:.8f}",
            "crs": "EPSG:4326",
            "response_crs": "EPSG:4326",
            "width": EMODNET_REQUEST_WIDTH,
            "height": EMODNET_REQUEST_HEIGHT,
            "format": "GeoTIFF",
        }
    )
    return f"{EMODNET_WCS}?{query}"


def limtm_url() -> str:
    west, south, east, north = MAP_BOUNDS
    query = urllib.parse.urlencode(
        {
            "SERVICE": "WFS",
            "VERSION": "2.0.0",
            "REQUEST": "GetFeature",
            "TYPENAMES": LIMTM_WFS_TYPENAME,
            "SRSNAME": "EPSG:4326",
            "BBOX": f"{west:.8f},{south:.8f},{east:.8f},{north:.8f},EPSG:4326",
            "OUTPUTFORMAT": "application/json",
        }
    )
    return f"{LIMTM_WFS_ENDPOINT}?{query}"


def matrix_dimensions(zoom: int) -> tuple[int, int]:
    return 2 ** (zoom + 1), 2**zoom


def global_pixel(longitude: float, latitude: float, zoom: int) -> tuple[float, float]:
    matrix_width, matrix_height = matrix_dimensions(zoom)
    return (
        (longitude + 180.0) / 360.0 * matrix_width * TILE_SIZE,
        (90.0 - latitude) / 180.0 * matrix_height * TILE_SIZE,
    )


def tile_url(row: int, column: int) -> str:
    query = urllib.parse.urlencode(
        {
            "SERVICE": "WMTS",
            "REQUEST": "GetTile",
            "VERSION": "1.0.0",
            "LAYER": RGE_LAYER,
            "STYLE": "normal",
            "FORMAT": "image/x-bil;bits=32",
            "TILEMATRIXSET": RGE_TILE_MATRIX_SET,
            "TILEMATRIX": RGE_ZOOM,
            "TILEROW": row,
            "TILECOL": column,
        }
    )
    return f"{RGE_WMTS}?{query}"


def ensure_natural_earth(*, refresh: bool) -> Path:
    archive = CACHE / "ne_10m_admin_0_countries.zip"
    extracted = CACHE / "natural-earth-10m"
    shp = extracted / "ne_10m_admin_0_countries.shp"
    if refresh or not archive.is_file():
        download(NATURAL_EARTH_ZIP, archive, refresh=True)
    if sha256(archive) != NATURAL_EARTH_SHA256:
        raise ValueError(f"Unexpected Natural Earth checksum for {archive}")
    if shp.is_file() and not refresh:
        return shp
    extracted.mkdir(parents=True, exist_ok=True)
    required = {
        "ne_10m_admin_0_countries.shp",
        "ne_10m_admin_0_countries.shx",
        "ne_10m_admin_0_countries.dbf",
        "ne_10m_admin_0_countries.prj",
    }
    with zipfile.ZipFile(archive) as source:
        names = {Path(name).name: name for name in source.namelist()}
        missing = sorted(required - set(names))
        if missing:
            raise ValueError(f"Natural Earth archive is missing {missing}")
        for name in required:
            with source.open(names[name]) as source_file, (
                extracted / name
            ).open("wb") as target_file:
                shutil.copyfileobj(source_file, target_file)
    return shp


def iter_polygons(geometry: ogr.Geometry):
    name = geometry.GetGeometryName().upper()
    if name == "POLYGON":
        yield geometry
    elif name in {"MULTIPOLYGON", "GEOMETRYCOLLECTION"}:
        for index in range(geometry.GetGeometryCount()):
            yield from iter_polygons(geometry.GetGeometryRef(index))


def map_point(longitude: float, latitude: float) -> tuple[float, float]:
    west, south, east, north = MAP_BOUNDS
    return (
        (longitude - west) / (east - west) * WIDTH,
        (north - latitude) / (north - south) * HEIGHT,
    )


def natural_earth_land_mask(*, refresh: bool) -> Image.Image:
    ogr.UseExceptions()
    dataset = ogr.Open(str(ensure_natural_earth(refresh=refresh)))
    if dataset is None:
        raise RuntimeError("Cannot open the Natural Earth country layer")
    layer = dataset.GetLayer(0)
    west, south, east, north = MAP_BOUNDS
    mask = Image.new("L", (WIDTH, HEIGHT), 0)
    draw = ImageDraw.Draw(mask)
    for feature in layer:
        geometry = feature.GetGeometryRef()
        if geometry is None:
            continue
        min_x, max_x, min_y, max_y = geometry.GetEnvelope()
        if max_x < west or min_x > east or max_y < south or min_y > north:
            continue
        for polygon in iter_polygons(geometry):
            if polygon.GetGeometryCount() == 0:
                continue
            exterior = polygon.GetGeometryRef(0)
            draw.polygon(
                [map_point(exterior.GetX(i), exterior.GetY(i)) for i in range(exterior.GetPointCount())],
                fill=255,
            )
            for index in range(1, polygon.GetGeometryCount()):
                hole = polygon.GetGeometryRef(index)
                draw.polygon(
                    [map_point(hole.GetX(i), hole.GetY(i)) for i in range(hole.GetPointCount())],
                    fill=0,
                )
    dataset = None
    return mask


def litto3d_member_at_5m(member: str) -> str:
    """Map the configured 1 m member to the matching 5 m member."""
    if "/MNT1m/" not in member or "_MNT_" not in member:
        raise ValueError(f"Unexpected Litto3D MNT1m member: {member}")
    return member.replace("/MNT1m/", "/MNT5m/").replace("_MNT_", "_MNT5_")


def litto3d_package_specs() -> list[dict[str, object]]:
    """Collect the six official Litto3D packages referenced by the sites."""
    packages: dict[str, dict[str, object]] = {}
    for config_path in sorted(SITE_CONFIG_DIR.glob("*.json")):
        config = json.loads(config_path.read_text(encoding="utf-8"))
        entries: list[tuple[str, list[str]]] = []
        archive_url = config.get("litto3d_archive_url")
        archive_members = config.get("litto3d_archive_members")
        if archive_url and archive_members:
            entries.append((str(archive_url), [str(member) for member in archive_members]))
        for archive in config.get("litto3d_archives", []):
            entries.append(
                (str(archive["url"]), [str(member) for member in archive["members"]])
            )
        for url, members in entries:
            package = packages.setdefault(url, {"url": url, "members": set()})
            package_members = package["members"]
            assert isinstance(package_members, set)
            mnt_members = [
                member
                for member in members
                if "/MNT1m/" in member
                and "_MNT_" in member
                and member.endswith(".asc")
            ]
            package_members.update(
                litto3d_member_at_5m(member) for member in mnt_members
            )

    return [
        {"url": url, "members": sorted(package["members"])}
        for url, package in sorted(packages.items())
    ]


def litto3d_archive_path(url: str) -> Path:
    filename = Path(urllib.parse.urlparse(url).path).name
    if not filename:
        raise ValueError(f"Cannot determine Litto3D archive name from {url}")
    return CACHE / "litto3d" / filename


def litto3d_archive_members(archive: Path) -> list[str]:
    """Return every MNT5m grid in a downloaded official package."""
    listing = subprocess.check_output(["bsdtar", "-tf", str(archive)], text=True)
    members = sorted(
        name
        for name in listing.splitlines()
        if "/MNT5m/" in name and name.endswith(".asc")
    )
    if not members:
        raise RuntimeError(f"No MNT5m ASCII grid found in {archive}")
    return members


def ensure_litto3d_ascii_tiles(*, refresh: bool) -> tuple[list[Path], int]:
    """Download and extract the complete MNT5m footprint of each site package."""
    packages = litto3d_package_specs()
    ascii_root = CACHE / "litto3d-mnt5m"
    paths: list[Path] = []
    for package in packages:
        url = str(package["url"])
        archive = litto3d_archive_path(url)
        download(url, archive, refresh=refresh)
        for member in litto3d_archive_members(archive):
            member_path = Path(str(member))
            output = ascii_root / f"{archive.stem}__{member_path.name}"
            if refresh or not output.is_file():
                output.parent.mkdir(parents=True, exist_ok=True)
                temporary = output.with_suffix(output.suffix + ".part")
                temporary.unlink(missing_ok=True)
                try:
                    with temporary.open("wb") as stream:
                        subprocess.run(
                            ["bsdtar", "-xOf", str(archive), str(member)],
                            check=True,
                            stdout=stream,
                        )
                    temporary.replace(output)
                finally:
                    temporary.unlink(missing_ok=True)
            paths.append(output)
    if not paths:
        raise RuntimeError("No Litto3D MNT5m tile is configured for PACA")
    return paths, len(packages)


def read_litto3d_ascii(path: Path) -> tuple[np.ndarray, tuple[float, float, float, float, float, float]]:
    headers: dict[str, float] = {}
    with path.open("r", encoding="ascii") as stream:
        for _ in range(6):
            key, value = stream.readline().split()[:2]
            headers[key.lower()] = float(value)
    values = np.loadtxt(path, dtype=np.float32, skiprows=6)
    ncols = int(headers["ncols"])
    nrows = int(headers["nrows"])
    cellsize = headers["cellsize"]
    if values.shape != (nrows, ncols):
        raise ValueError(f"Unexpected Litto3D grid shape in {path}: {values.shape}")
    if abs(cellsize - LITTO3D_CELL_SIZE_M) > 0.01:
        raise ValueError(f"Unexpected Litto3D cell size in {path}: {cellsize}")
    xllcenter = headers["xllcenter"]
    yllcenter = headers["yllcenter"]
    geotransform = (
        xllcenter - cellsize / 2.0,
        cellsize,
        0.0,
        yllcenter + (nrows - 0.5) * cellsize,
        0.0,
        -cellsize,
    )
    return values, geotransform


def ensure_litto3d_tile_geotiff(path: Path, *, refresh: bool) -> Path:
    output = CACHE / "litto3d-tif" / f"{path.stem}.tif"
    if output.is_file() and not refresh:
        return output
    values, geotransform = read_litto3d_ascii(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".part")
    temporary.unlink(missing_ok=True)
    spatial_reference = osr.SpatialReference()
    spatial_reference.ImportFromEPSG(2154)
    dataset = gdal.GetDriverByName("GTiff").Create(
        str(temporary),
        values.shape[1],
        values.shape[0],
        1,
        gdal.GDT_Float32,
        options=["TILED=YES", "COMPRESS=DEFLATE", "PREDICTOR=2"],
    )
    if dataset is None:
        raise RuntimeError(f"Cannot create Litto3D GeoTIFF {temporary}")
    dataset.SetGeoTransform(geotransform)
    dataset.SetProjection(spatial_reference.ExportToWkt())
    band = dataset.GetRasterBand(1)
    band.SetNoDataValue(LITTO3D_NODATA)
    band.WriteArray(values)
    band.FlushCache()
    dataset.FlushCache()
    dataset = None
    temporary.replace(output)
    return output


def load_litto3d_crop(*, refresh: bool) -> tuple[np.ndarray, np.ndarray, int, int]:
    ascii_paths, package_count = ensure_litto3d_ascii_tiles(refresh=refresh)
    tile_paths = [
        ensure_litto3d_tile_geotiff(path, refresh=refresh) for path in ascii_paths
    ]
    output = CACHE / f"litto3d-wgs84-all-mnt5m-{WIDTH}x{HEIGHT}.tif"
    if refresh or not output.is_file():
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_suffix(output.suffix + ".part")
        temporary.unlink(missing_ok=True)
        west, south, east, north = MAP_BOUNDS
        options = gdal.WarpOptions(
            format="GTiff",
            outputBounds=(west, south, east, north),
            dstSRS="EPSG:4326",
            width=WIDTH,
            height=HEIGHT,
            srcNodata=LITTO3D_NODATA,
            dstNodata=LITTO3D_NODATA,
            outputType=gdal.GDT_Float32,
            resampleAlg="bilinear",
            multithread=True,
            creationOptions=["TILED=YES", "COMPRESS=DEFLATE", "PREDICTOR=2"],
        )
        dataset = gdal.Warp(str(temporary), [str(path) for path in tile_paths], options=options)
        if dataset is None:
            raise RuntimeError("Cannot reproject the Litto3D MNT5m mosaic")
        dataset.FlushCache()
        dataset = None
        temporary.replace(output)
    dataset = gdal.Open(str(output), gdal.GA_ReadOnly)
    if dataset is None:
        raise RuntimeError(f"Cannot open Litto3D mosaic {output}")
    values = dataset.GetRasterBand(1).ReadAsArray().astype(np.float32)
    dataset = None
    valid = np.isfinite(values) & (values > LITTO3D_NODATA + 1.0)
    return values, valid, package_count, len(tile_paths)


def load_emodnet_crop(*, refresh: bool) -> tuple[np.ndarray, np.ndarray]:
    """Load the official EMODnet DTM and resample it to the output frame."""
    native = CACHE / "emodnet-mean-paca-native.tif"
    if refresh or not native.is_file():
        download(emodnet_url(), native, refresh=True)
    source = gdal.Open(str(native), gdal.GA_ReadOnly)
    if source is None:
        native.unlink(missing_ok=True)
        download(emodnet_url(), native, refresh=True)
        source = gdal.Open(str(native), gdal.GA_ReadOnly)
    if source is None:
        raise RuntimeError(f"Cannot open the EMODnet bathymetry grid {native}")
    source = None

    output = CACHE / f"emodnet-mean-wgs84-{WIDTH}x{HEIGHT}.tif"
    if refresh or not output.is_file():
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_suffix(output.suffix + ".part")
        temporary.unlink(missing_ok=True)
        options = gdal.WarpOptions(
            format="GTiff",
            outputBounds=MAP_BOUNDS,
            dstSRS="EPSG:4326",
            width=WIDTH,
            height=HEIGHT,
            outputType=gdal.GDT_Float32,
            resampleAlg="cubic",
            multithread=True,
            creationOptions=["TILED=YES", "COMPRESS=DEFLATE", "PREDICTOR=2"],
        )
        dataset = gdal.Warp(str(temporary), str(native), options=options)
        if dataset is None:
            raise RuntimeError("Cannot resample the EMODnet bathymetry grid")
        dataset.FlushCache()
        dataset = None
        temporary.replace(output)

    dataset = gdal.Open(str(output), gdal.GA_ReadOnly)
    if dataset is None:
        raise RuntimeError(f"Cannot open the resampled EMODnet grid {output}")
    values = dataset.GetRasterBand(1).ReadAsArray().astype(np.float32)
    dataset = None
    valid = np.isfinite(values) & (values > -10000.0)
    return values, valid


def iter_geojson_lines(geometry: dict[str, object]):
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if geometry_type == "LineString":
        yield coordinates
    elif geometry_type == "MultiLineString":
        yield from coordinates
    elif geometry_type == "GeometryCollection":
        for child in geometry.get("geometries", []):
            yield from iter_geojson_lines(child)


def limtm_land_mask(
    *, refresh: bool, natural_land_array: np.ndarray
) -> tuple[np.ndarray, int, int]:
    """Build one coherent land mask from the official Shom–IGN boundary.

    The WFS contains both natural coastline (COALNE) and constructed coastal
    limits (SLCONS). Keeping both closes the small harbour/port gaps that made
    the old vector overlay discontinuous. Natural Earth is used only to tell
    the flood fill which map-border pixels are ocean and as a sanity check.
    """
    source_path = CACHE / "limtm-paca-ligne.geojson"
    download(limtm_url(), source_path, refresh=refresh)
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    coastline_mask = Image.new("L", (WIDTH, HEIGHT), 0)
    constructed_mask = Image.new("L", (WIDTH, HEIGHT), 0)
    coastline_draw = ImageDraw.Draw(coastline_mask)
    constructed_draw = ImageDraw.Draw(constructed_mask)
    drawn_features = 0
    drawn_vertices = 0
    for feature in payload.get("features", []):
        properties = feature.get("properties", {})
        feature_type = properties.get("typetc")
        if feature_type not in {"COALNE", "SLCONS"}:
            continue
        geometry = feature.get("geometry")
        if not geometry:
            continue
        for line in iter_geojson_lines(geometry):
            points = []
            for longitude, latitude, *_ in line:
                x, y = map_point(longitude, latitude)
                points.append((x, y))
            if len(points) < 2:
                continue
            width = max(1, round(LIMTM_LINE_WIDTH_PX))
            draw = coastline_draw if feature_type == "COALNE" else constructed_draw
            draw.line(points, fill=255, width=width, joint="curve")
            drawn_features += 1
            drawn_vertices += len(points)
    if drawn_features == 0:
        raise RuntimeError("The Shom–IGN Limite terre-mer response contained no coastline lines")

    # Keep all boundary classes while closing the land/sea topology. Some
    # SLCONS segments are required to bridge harbour gaps in COALNE; detached
    # structures are removed later as isolated raster components.
    coastline_array = np.asarray(coastline_mask, dtype=np.uint8)
    constructed_array = np.asarray(constructed_mask, dtype=np.uint8)
    boundary_source = (coastline_array > 0) | (constructed_array > 0)

    # Close only one or two output pixels. This repairs clipped WFS segment
    # joins without changing the coastline at the map's scale.
    close_size = LIMTM_CLOSE_RADIUS_PX * 2 + 1
    boundary = np.asarray(
        Image.fromarray(boundary_source.astype(np.uint8) * 255, mode="L").filter(
            ImageFilter.MaxFilter(close_size)
        ),
        dtype=np.uint8,
    ) > 0

    # Flood the connected ocean from the frame border. Natural Earth land at
    # the frame border is protected so a WFS segment clipped by the frame
    # cannot turn an adjacent land wedge into ocean.
    walk = Image.fromarray(
        np.where(boundary, 255, 0).astype(np.uint8), mode="L"
    ).copy()
    walk_pixels = np.asarray(walk, dtype=np.uint8).copy()
    walk_pixels[0, natural_land_array[0, :]] = 255
    walk_pixels[-1, natural_land_array[-1, :]] = 255
    walk_pixels[natural_land_array[:, 0], 0] = 255
    walk_pixels[natural_land_array[:, -1], -1] = 255
    walk = Image.fromarray(walk_pixels, mode="L").copy()

    def flood_seed(x: int, y: int) -> None:
        if not natural_land_array[y, x] and walk.getpixel((x, y)) == 0:
            ImageDraw.floodfill(walk, (x, y), 128, thresh=0)

    for x in range(WIDTH):
        flood_seed(x, 0)
        flood_seed(x, HEIGHT - 1)
    for y in range(HEIGHT):
        flood_seed(0, y)
        flood_seed(WIDTH - 1, y)

    official_land_array = np.asarray(walk, dtype=np.uint8) != 128

    # Drop detached structures that are below the regional display scale only
    # when they have no COALNE support. This preserves small real islands while
    # removing isolated SLCONS rectangles from the public overview.
    component_image = Image.fromarray(
        np.where(official_land_array, 255, 0).astype(np.uint8), mode="L"
    ).copy()
    coastline_pixels = coastline_array > 0
    removed_components = 0
    for y in range(HEIGHT):
        row_pixels = np.asarray(component_image, dtype=np.uint8)[y]
        for x in np.flatnonzero(row_pixels == 255):
            if component_image.getpixel((int(x), y)) != 255:
                continue
            ImageDraw.floodfill(component_image, (int(x), y), 64, thresh=0)
            component = np.asarray(component_image, dtype=np.uint8) == 64
            component_size = int(component.sum())
            if (
                component_size <= LIMTM_ISOLATED_COMPONENT_MAX_PX
                and not np.any(component & coastline_pixels)
            ):
                official_land_array[component] = False
                removed_components += 1
    natural_area = float(natural_land_array.mean())
    official_area = float(official_land_array.mean())
    area_delta = abs(official_area - natural_area)
    if area_delta > 0.05:
        # Small autonomous-region frames can clip a LIMTM segment at the map
        # edge. Reconcile that incomplete flood fill conservatively with the
        # Natural Earth topology already used to seed and validate it:
        # restore missing land, or remove an implausible flooded sea. This
        # keeps every official boundary pixel while preventing an open WFS
        # segment from erasing or flooding most of the regional frame.
        if official_area < natural_area:
            official_land_array |= natural_land_array
        else:
            official_land_array &= natural_land_array
        official_area = float(official_land_array.mean())
        area_delta = abs(official_area - natural_area)
    if area_delta > 0.05 or not official_land_array.any() or official_land_array.all():
        raise RuntimeError(
            "The Shom–IGN land-mask flood fill is implausible: "
            f"Natural Earth area={natural_area:.3f}, official area={official_area:.3f}"
        )
    print(
        "Built Shom–IGN Limite terre-mer land mask: "
        f"{drawn_features} segments, {drawn_vertices} vertices, "
        f"removed isolated components={removed_components}, "
        f"land area={official_area:.3f}, delta vs Natural Earth={area_delta:.3f}"
    )
    return official_land_array, drawn_features, drawn_vertices


def download_rge_tile(row: int, column: int, *, refresh: bool) -> Path:
    path = CACHE / f"rge-z{RGE_ZOOM}-r{row}-c{column}.bil"
    if path.is_file() and not refresh:
        return path
    for attempt in range(3):
        try:
            download(tile_url(row, column), path, refresh=True)
            raw = np.fromfile(path, dtype="<f4")
            if raw.size != TILE_SIZE * TILE_SIZE:
                raise ValueError(
                    f"Unexpected RGE ALTI tile size for {row}/{column}: {raw.size}"
                )
            return path
        except Exception:
            path.unlink(missing_ok=True)
            if attempt == 2:
                raise
            time.sleep(1.0 + attempt)
    raise AssertionError("unreachable")


def load_rge_crop(*, refresh: bool) -> tuple[np.ndarray, np.ndarray]:
    west, south, east, north = MAP_BOUNDS
    left, top = global_pixel(west, north, RGE_ZOOM)
    right, bottom = global_pixel(east, south, RGE_ZOOM)
    x_start, y_start = math.floor(left), math.floor(top)
    x_end, y_end = math.ceil(right), math.ceil(bottom)
    column_start = x_start // TILE_SIZE
    column_end = (x_end - 1) // TILE_SIZE
    row_start = y_start // TILE_SIZE
    row_end = (y_end - 1) // TILE_SIZE
    mosaic = np.full(
        (
            (row_end - row_start + 1) * TILE_SIZE,
            (column_end - column_start + 1) * TILE_SIZE,
        ),
        -99999.0,
        dtype=np.float32,
    )
    requests = [
        (row, column)
        for row in range(row_start, row_end + 1)
        for column in range(column_start, column_end + 1)
    ]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(
                download_rge_tile,
                row,
                column,
                refresh=refresh,
            ): (row, column)
            for row, column in requests
        }
        for future in concurrent.futures.as_completed(futures):
            row, column = futures[future]
            tile = np.fromfile(future.result(), dtype="<f4").reshape(
                TILE_SIZE, TILE_SIZE
            )
            y_offset = (row - row_start) * TILE_SIZE
            x_offset = (column - column_start) * TILE_SIZE
            mosaic[
                y_offset : y_offset + TILE_SIZE,
                x_offset : x_offset + TILE_SIZE,
            ] = tile

    crop = mosaic[
        y_start - row_start * TILE_SIZE : y_end - row_start * TILE_SIZE,
        x_start - column_start * TILE_SIZE : x_end - column_start * TILE_SIZE,
    ]
    valid = np.isfinite(crop) & (crop >= RGE_VALID_MIN_M)
    return crop, valid


def terrain_palette(elevation: np.ndarray) -> np.ndarray:
    stops = np.array([0, 20, 80, 200, 400, 700, 1100, 1600, 2400], dtype=np.float32)
    colors = np.array(
        [
            [119, 181, 119],
            [137, 190, 124],
            [166, 199, 132],
            [199, 202, 138],
            [207, 185, 132],
            [177, 148, 111],
            [148, 117, 96],
            [124, 102, 88],
            [215, 207, 188],
        ],
        dtype=np.float32,
    )
    values = np.clip(elevation, stops[0], stops[-1])
    result = np.empty((*values.shape, 3), dtype=np.float32)
    result.fill(0)
    for index in range(len(stops) - 1):
        low, high = stops[index], stops[index + 1]
        selected = (values >= low) & (values <= high)
        weight = ((values[selected] - low) / (high - low))[:, None]
        result[selected] = colors[index] * (1 - weight) + colors[index + 1] * weight
    result[values >= stops[-1]] = colors[-1]
    return result


def marine_palette(surface: np.ndarray) -> np.ndarray:
    """Render negative bathymetry as a continuous nearshore-to-offshore palette."""
    depth = np.clip(-surface, 0.0, 3000.0)
    stops = np.array(
        [0, 1, 3, 8, 15, 30, 60, 100, 250, 500, 1000, 3000],
        dtype=np.float32,
    )
    colors = np.array(
        [
            # Keep the Réunion locator's light turquoise nearshore scale,
            # while retaining a blue offshore tail for the deep basin.
            [175, 224, 218],
            [165, 221, 218],
            [155, 216, 215],
            [145, 211, 213],
            [135, 205, 211],
            [122, 198, 207],
            [110, 191, 202],
            [100, 184, 198],
            [87, 176, 193],
            [75, 169, 189],
            [63, 162, 184],
            [27, 132, 165],
        ],
        dtype=np.float32,
    )
    values = np.clip(depth, stops[0], stops[-1])
    result = np.empty((*values.shape, 3), dtype=np.float32)
    result.fill(0)
    for index in range(len(stops) - 1):
        low, high = stops[index], stops[index + 1]
        selected = (values >= low) & (values <= high)
        weight = ((values[selected] - low) / (high - low))[:, None]
        result[selected] = colors[index] * (1 - weight) + colors[index + 1] * weight
    result[values >= stops[-1]] = colors[-1]
    return result


def render_land(elevation: np.ndarray, valid: np.ndarray) -> tuple[Image.Image, Image.Image]:
    filled = np.where(valid, elevation, 0.0).astype(np.float32)
    elevation_image = Image.fromarray(filled, mode="F").resize(
        (WIDTH, HEIGHT), Image.Resampling.BICUBIC
    )
    valid_image = Image.fromarray((valid.astype(np.uint8) * 255), mode="L").resize(
        (WIDTH, HEIGHT), Image.Resampling.LANCZOS
    )
    terrain = np.asarray(elevation_image, dtype=np.float32)
    pixel_x_m = (MAP_BOUNDS[2] - MAP_BOUNDS[0]) * 111320.0 * math.cos(
        math.radians((MAP_BOUNDS[1] + MAP_BOUNDS[3]) / 2.0)
    ) / WIDTH
    pixel_y_m = (MAP_BOUNDS[3] - MAP_BOUNDS[1]) * 111320.0 / HEIGHT
    gradient_y, gradient_x = np.gradient(terrain, pixel_y_m, pixel_x_m)
    normal_x = -gradient_x
    normal_y = gradient_y
    normal_z = np.ones_like(terrain)
    normal_length = np.sqrt(normal_x**2 + normal_y**2 + normal_z**2)
    normal_x /= normal_length
    normal_y /= normal_length
    normal_z /= normal_length
    light = np.array([-0.42, 0.48, 0.77], dtype=np.float32)
    light /= np.linalg.norm(light)
    illumination = np.clip(
        0.62
        + 0.62
        * np.clip(
            normal_x * light[0]
            + normal_y * light[1]
            + normal_z * light[2],
            0.0,
            1.0,
        ),
        0.48,
        1.18,
    )
    rgb = np.clip(terrain_palette(terrain) * illumination[:, :, None], 0, 255)
    return (
        Image.fromarray(rgb.astype(np.uint8), mode="RGB").convert("RGBA"),
        valid_image,
    )


def render(*, refresh: bool) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    gebco_path = CACHE / f"gebco-{WIDTH}x{HEIGHT}.png"
    download(gebco_url(), gebco_path, refresh=refresh)
    base = Image.open(gebco_path).convert("RGB")
    if base.size != (WIDTH, HEIGHT):
        raise ValueError(f"Unexpected GEBCO image dimensions: {base.size}")

    natural_land = natural_earth_land_mask(refresh=refresh)
    natural_land_array = np.asarray(natural_land, dtype=bool)
    land_mask, _, _ = limtm_land_mask(
        refresh=refresh, natural_land_array=natural_land_array
    )

    emodnet_surface, emodnet_valid = load_emodnet_crop(refresh=refresh)
    # EMODnet is the primary marine field. GEBCO remains available only for
    # cells where the official DTM has no valid value, so its coarse grid can
    # no longer tile the visible sea by default.
    gebco_rgb = np.asarray(base, dtype=np.float32)
    ocean_y = np.linspace(0.0, 1.0, HEIGHT, dtype=np.float32)[:, None, None]
    ocean_top = np.array([100, 184, 218], dtype=np.float32)
    ocean_bottom = np.array([60, 139, 187], dtype=np.float32)
    ocean_gradient = np.repeat(
        ocean_top[None, None, :] * (1.0 - ocean_y)
        + ocean_bottom[None, None, :] * ocean_y,
        WIDTH,
        axis=1,
    )
    gebco_rgb = gebco_rgb * 0.90 + ocean_gradient * 0.10
    ocean_rgb = ocean_gradient.copy()
    emodnet_marine = (
        emodnet_valid
        & (emodnet_surface < 0.0)
        & ~land_mask
    )
    emodnet_rgb = marine_palette(emodnet_surface)
    # Use the same 82/18 bathymetry-to-gradient balance as the Réunion
    # locator, without its broad raster blur: EMODnet is already cubic-
    # resampled and should keep its finer regional detail.
    emodnet_rgb = emodnet_rgb * 0.82 + ocean_gradient * 0.18
    emodnet_alpha = emodnet_marine.astype(np.float32) * 0.96
    ocean_rgb = (
        ocean_rgb * (1.0 - emodnet_alpha[:, :, None])
        + emodnet_rgb * emodnet_alpha[:, :, None]
    )
    fallback_alpha = (~emodnet_marine).astype(np.float32) * (~land_mask).astype(
        np.float32
    )
    ocean_rgb = (
        ocean_rgb * (1.0 - fallback_alpha[:, :, None])
        + gebco_rgb * fallback_alpha[:, :, None]
    )

    shom_surface, shom_valid, package_count, tile_count = load_litto3d_crop(
        refresh=refresh
    )
    # Litto3D is authoritative for nearshore water depth. The interior guard
    # avoids drawing archive-edge seams; the same official land mask drives
    # both this transition and the land relief below.
    shom_coverage = Image.fromarray(
        np.where(shom_valid, 255, 0).astype(np.uint8), mode="L"
    )
    shom_interior = np.asarray(
        shom_coverage.filter(ImageFilter.MinFilter(3)), dtype=np.uint8
    ) > 127
    coast_band = np.asarray(
        Image.fromarray((land_mask.astype(np.uint8) * 255), mode="L").filter(
            ImageFilter.MaxFilter(SHOM_COAST_BAND_PX * 2 + 1)
        ),
        dtype=np.uint8,
    ) > 127
    shom_marine = (
        shom_interior
        & (shom_surface < 0.0)
        & ~land_mask
        & coast_band
    )
    shom_rgb = marine_palette(shom_surface)
    shom_alpha = np.asarray(
        Image.fromarray((shom_marine.astype(np.uint8) * 255), mode="L").filter(
            ImageFilter.GaussianBlur(SHOM_EDGE_FEATHER_PX)
        ),
        dtype=np.float32,
    ) / 255.0
    shom_alpha *= (~land_mask).astype(np.float32)
    shom_alpha *= SHOM_MARINE_BLEND
    composite_rgb = ocean_rgb * (1.0 - shom_alpha[:, :, None]) + shom_rgb * shom_alpha[:, :, None]

    elevation, valid = load_rge_crop(refresh=refresh)
    land, valid_image = render_land(elevation, valid)
    alpha = (
        np.asarray(valid_image, dtype=np.float32)
        / 255.0
        * land_mask.astype(np.float32)
    )
    land_rgb = np.asarray(land, dtype=np.float32)
    composite_rgb = composite_rgb * (1.0 - alpha[:, :, None]) + land_rgb[:, :, :3] * alpha[:, :, None]
    composite = Image.fromarray(np.clip(composite_rgb, 0, 255).astype(np.uint8), mode="RGB").convert("RGBA")

    # The visible edge is derived from the exact mask used for both land and
    # sea compositing. It therefore cannot float away from the land fill or
    # become discontinuous at a COALNE/SLCONS feature join.
    edge = np.zeros_like(land_mask, dtype=bool)
    edge[1:, :] |= land_mask[1:, :] != land_mask[:-1, :]
    edge[:-1, :] |= land_mask[:-1, :] != land_mask[1:, :]
    edge[:, 1:] |= land_mask[:, 1:] != land_mask[:, :-1]
    edge[:, :-1] |= land_mask[:, :-1] != land_mask[:, 1:]
    edge_alpha = Image.fromarray(np.where(edge, 190, 0).astype(np.uint8), mode="L")
    coastline = Image.new("RGBA", (WIDTH, HEIGHT), (23, 91, 102, 0))
    coastline.putalpha(edge_alpha)
    composite = Image.alpha_composite(composite, coastline)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    composite.convert("RGB").save(OUTPUT, format="PNG", optimize=True)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    locator = manifest["westCoastLocator"]
    locator.update(
        {
            "src": f"/maps/{REGION_SLUG}/{REGION_SLUG}-regional-relief.png",
            "width": WIDTH,
            "height": HEIGHT,
            "bytes": OUTPUT.stat().st_size,
            "sha256": sha256(OUTPUT),
            "source": (
                f"Shom–IGN Limite terre-mer for the visible {REGION_SLUG} coastline; "
                "Shom–IGN Litto3D PACA 2015 MNT5m for nearshore bathymetry; "
                "EMODnet Bathymetry DTM 2024 for offshore bathymetry; "
                "GEBCO Compilation Group (2024), GEBCO 2024 Grid, WMS layer "
                "GEBCO_2024 only as no-data fallback; IGN RGE ALTI for land relief"
            ),
            "sourceUrl": EMODNET_WCS,
            "layer": EMODNET_COVERAGE,
            "marineSourceUrl": EMODNET_WCS,
            "marineLayer": EMODNET_COVERAGE,
            "marineResolution": "1/16 arc minute native DTM grid (~115 m)",
            "detailSourceUrl": RGE_WMTS,
            "detailLayer": RGE_LAYER,
            "detailTileMatrixSet": RGE_TILE_MATRIX_SET,
            "detailZoom": RGE_ZOOM,
            "detailBathymetrySourceUrl": LITTO3D_GROUP_URL,
            "detailBathymetryLayer": "LITTO3D PACA 2015 MNT5m",
            "detailBathymetryCrs": LITTO3D_CRS,
            "detailBathymetryResolutionM": LITTO3D_CELL_SIZE_M,
            "detailBathymetryArchiveCount": package_count,
            "detailBathymetryTileCount": tile_count,
            "coastlineSource": (
                "Shom–IGN Limite terre-mer COALNE + SLCONS vector features, "
                "LIMTM_2154_WFS:limite_terre_mer_france_metropolitaine_ligne; "
                "Natural Earth 10m Admin 0 Countries v5.1.1 is used only for "
                "border flood-fill seeding and sanity checking"
            ),
            "coastlineSourceUrl": LIMTM_WFS_ENDPOINT,
            "coastlineLayer": LIMTM_WFS_TYPENAME,
            "coastlineFeatureTypes": "COALNE + SLCONS",
            "coastlineResolution": "1–7 m product resolution",
            "render": (
                "EMODnet DTM 2024 offshore bathymetry resampled with cubic "
                "interpolation; Shom–IGN Litto3D nearshore bathymetry; one "
                "Shom–IGN land mask for fill and coastline edge; IGN RGE ALTI "
                "land hillshade; no cross-coast blur"
            ),
        }
    )
    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT} ({WIDTH} x {HEIGHT})")
    print(f"Updated {MANIFEST}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="redownload the regional bathymetry, coastline, and terrain sources",
    )
    args = parser.parse_args()
    render(refresh=args.refresh)


if __name__ == "__main__":
    main()
