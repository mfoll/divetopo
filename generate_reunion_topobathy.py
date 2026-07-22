from __future__ import annotations

import argparse
import html
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
from osgeo import gdal, osr

from render_fused_relief import make_clean_plan, make_locator_map, make_pretty_3d_from_offshore


ROOT = Path(__file__).resolve().parent
DEFAULT_CACHE = ROOT / ".tmp" / "bathy-renders"
RGE_ALTI_WMS = "https://data.geopf.fr/wms-r/wms"
RGE_ALTI_LAYER = "ELEVATION.ELEVATIONGRIDCOVERAGE.HIGHRES"
ORTHOPHOTO_LAYER = "HR.ORTHOIMAGERY.ORTHOPHOTOS"
GEBCO_WMS = "https://wms.gebco.net/mapserv"
GEBCO_LAYER = "GEBCO_LATEST"


def run(command: list[str]) -> None:
    print("+", " ".join(command))
    subprocess.run(command, check=True)


def as_path(value: str | None, default: Path) -> Path:
    path = Path(value).expanduser() if value else default
    return path if path.is_absolute() else ROOT / path


def bbox(config: dict, key: str) -> tuple[float, float, float, float]:
    values = tuple(map(float, config[key]))
    if len(values) != 4:
        raise ValueError(f"{key} must contain [min_x, min_y, max_x, max_y]")
    min_x, min_y, max_x, max_y = values
    if min_x >= max_x or min_y >= max_y:
        raise ValueError(f"Invalid {key}: {values}")
    return values


def contains(outer: tuple[float, float, float, float], inner: tuple[float, float, float, float]) -> bool:
    return outer[0] <= inner[0] and outer[1] <= inner[1] and outer[2] >= inner[2] and outer[3] >= inner[3]


def resolve_hyscores_tiff(config: dict) -> str:
    if config.get("hyscores_tiff_url"):
        return str(config["hyscores_tiff_url"])
    directory = str(config["hyscores_directory"]).rstrip("/") + "/"
    with urllib.request.urlopen(directory, timeout=60) as response:
        listing = response.read().decode("utf-8", errors="replace")
    candidates = [
        html.unescape(match)
        for match in re.findall(r'href="([^"]+MNTHS_flld[^"]+crop_TIFF\.tif)"', listing, flags=re.IGNORECASE)
    ]
    if not candidates:
        raise RuntimeError(f"No numeric HYSCORES GeoTIFF found in {directory}")
    return urllib.parse.urljoin(directory, candidates[0])


def extract_hyscores(source_url: str, extent: tuple[float, float, float, float], output: Path) -> None:
    min_x, min_y, max_x, max_y = extent
    output.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            "gdal_translate",
            "--config",
            "GDAL_DISABLE_READDIR_ON_OPEN",
            "EMPTY_DIR",
            "-projwin",
            str(min_x),
            str(max_y),
            str(max_x),
            str(min_y),
            "-of",
            "GTiff",
            "-co",
            "TILED=YES",
            "-co",
            "COMPRESS=DEFLATE",
            "-co",
            "PREDICTOR=3",
            f"/vsicurl/{source_url}",
            str(output),
        ]
    )


def positive_depth(source: Path, output: Path) -> None:
    dataset = gdal.Open(str(source))
    if dataset is None:
        raise RuntimeError(f"Cannot open {source}")
    values = dataset.GetRasterBand(1).ReadAsArray().astype(np.float32)
    depth = np.where(np.isfinite(values) & (values >= -80.0) & (values <= 0.0), -values, -99999.0).astype(np.float32)

    output.parent.mkdir(parents=True, exist_ok=True)
    driver = gdal.GetDriverByName("GTiff")
    target = driver.Create(
        str(output),
        dataset.RasterXSize,
        dataset.RasterYSize,
        1,
        gdal.GDT_Float32,
        options=["TILED=YES", "COMPRESS=DEFLATE", "PREDICTOR=3"],
    )
    target.SetGeoTransform(dataset.GetGeoTransform())
    target.SetProjection(dataset.GetProjection())
    band = target.GetRasterBand(1)
    band.SetNoDataValue(-99999.0)
    band.WriteArray(depth)
    band.FlushCache()
    target = None


def download_rge_alti(extent: tuple[float, float, float, float], resolution: float, output: Path) -> None:
    min_x, min_y, max_x, max_y = extent
    width = int(round((max_x - min_x) / resolution))
    height = int(round((max_y - min_y) / resolution))
    if width > 5000 or height > 5000:
        raise ValueError(f"RGE ALTI WMS request is too large: {width} x {height}; enlarge the resolution")
    query = urllib.parse.urlencode(
        {
            "SERVICE": "WMS",
            "VERSION": "1.3.0",
            "REQUEST": "GetMap",
            "LAYERS": RGE_ALTI_LAYER,
            "STYLES": "",
            "CRS": "EPSG:32740",
            "BBOX": f"{min_x},{min_y},{max_x},{max_y}",
            "WIDTH": width,
            "HEIGHT": height,
            "FORMAT": "image/geotiff",
        }
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".part")
    urllib.request.urlretrieve(f"{RGE_ALTI_WMS}?{query}", temporary)
    os.replace(temporary, output)


def download_orthophoto(extent: tuple[float, float, float, float], resolution: float, layer: str, output: Path) -> None:
    min_x, min_y, max_x, max_y = extent
    width = int(round((max_x - min_x) / resolution))
    height = int(round((max_y - min_y) / resolution))
    if width > 5000 or height > 5000:
        raise ValueError(f"Orthophoto WMS request is too large: {width} x {height}; enlarge the resolution")
    query = urllib.parse.urlencode(
        {
            "SERVICE": "WMS",
            "VERSION": "1.3.0",
            "REQUEST": "GetMap",
            "LAYERS": layer,
            "STYLES": "",
            "CRS": "EPSG:32740",
            "BBOX": f"{min_x},{min_y},{max_x},{max_y}",
            "WIDTH": width,
            "HEIGHT": height,
            "FORMAT": "image/geotiff",
        }
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".part")
    urllib.request.urlretrieve(f"{RGE_ALTI_WMS}?{query}", temporary)
    os.replace(temporary, output)


def download_gebco_relief(
    extent_utm40s: tuple[float, float, float, float],
    target_width: int,
    target_height: int,
    request_width: int,
    layer: str,
    output: Path,
) -> None:
    geographic = osr.SpatialReference()
    geographic.ImportFromEPSG(4326)
    geographic.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    projected = osr.SpatialReference()
    projected.ImportFromEPSG(32740)
    projected.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    to_wgs84 = osr.CoordinateTransformation(projected, geographic)
    min_x, min_y, max_x, max_y = extent_utm40s
    corners = [to_wgs84.TransformPoint(x, y) for x in (min_x, max_x) for y in (min_y, max_y)]
    longitudes = [point[0] for point in corners]
    latitudes = [point[1] for point in corners]
    min_lon, max_lon = min(longitudes), max(longitudes)
    min_lat, max_lat = min(latitudes), max(latitudes)
    mean_latitude = np.deg2rad((min_lat + max_lat) / 2.0)
    request_height = int(round(request_width * (max_lat - min_lat) / ((max_lon - min_lon) * np.cos(mean_latitude))))
    query = urllib.parse.urlencode(
        {
            "SERVICE": "WMS",
            "VERSION": "1.1.1",
            "REQUEST": "GetMap",
            "LAYERS": layer,
            "STYLES": "",
            "SRS": "EPSG:4326",
            "BBOX": f"{min_lon},{min_lat},{max_lon},{max_lat}",
            "WIDTH": request_width,
            "HEIGHT": request_height,
            "FORMAT": "image/tiff",
        }
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    geographic_tiff = output.with_suffix(".wgs84.part.tif")
    urllib.request.urlretrieve(f"{GEBCO_WMS}?{query}", geographic_tiff)
    result = gdal.Warp(
        str(output),
        str(geographic_tiff),
        dstSRS="EPSG:32740",
        outputBounds=extent_utm40s,
        width=target_width,
        height=target_height,
        resampleAlg=gdal.GRA_Cubic,
        creationOptions=["TILED=YES", "COMPRESS=DEFLATE"],
    )
    if result is None:
        raise RuntimeError("Failed to reproject the GEBCO locator relief")
    result = None
    geographic_tiff.unlink(missing_ok=True)


def crop_raster(source: Path, extent: tuple[float, float, float, float], output: Path) -> None:
    min_x, min_y, max_x, max_y = extent
    output.parent.mkdir(parents=True, exist_ok=True)
    result = gdal.Translate(
        str(output),
        str(source),
        projWin=[min_x, max_y, max_x, min_y],
        creationOptions=["TILED=YES", "COMPRESS=DEFLATE", "PREDICTOR=3"],
    )
    if result is None:
        raise RuntimeError(f"Failed to crop {source}")
    result = None


def raster_summary(path: Path) -> str:
    dataset = gdal.Open(str(path))
    if dataset is None:
        return f"missing: {path}"
    transform = dataset.GetGeoTransform()
    width_m = dataset.RasterXSize * abs(transform[1])
    height_m = dataset.RasterYSize * abs(transform[5])
    return f"{path.name}: {dataset.RasterXSize} x {dataset.RasterYSize} px, {width_m:.0f} x {height_m:.0f} m"


def paths_for(config: dict) -> dict[str, Path]:
    slug = str(config["slug"])
    cache = as_path(config.get("cache_dir"), DEFAULT_CACHE)
    overrides = config.get("paths", {})
    defaults = {
        "context_depth_raw": cache / f"{slug}-context-depth.tif",
        "context_depth": cache / f"{slug}-context-depth-positive.tif",
        "context_elevation": cache / f"{slug}-context-elevation.tif",
        "context_orthophoto": cache / f"{slug}-context-orthophoto.tif",
        "focus_depth": cache / f"{slug}-focus-depth-positive.tif",
        "focus_elevation": cache / f"{slug}-focus-elevation.tif",
        "focus_orthophoto": cache / f"{slug}-focus-orthophoto.tif",
        "locator_elevation": cache / "reunion-locator-elevation.tif",
        "locator_bathymetry": cache / "reunion-locator-gebco-relief.tif",
        "output_2d": ROOT / "outputs" / f"{slug}-topobathy-2d.jpg",
        "output_2d_ortho": ROOT / "outputs" / f"{slug}-topobathy-2d-ortho.jpg",
        "output_3d": ROOT / "outputs" / f"{slug}-topobathy-3d.jpg",
        "output_3d_ortho": ROOT / "outputs" / f"{slug}-topobathy-3d-ortho.jpg",
        "output_locator": ROOT / "outputs" / f"{slug}-locator-reunion.jpg",
    }
    return {key: as_path(overrides.get(key), default) for key, default in defaults.items()}


def acquire(config: dict, paths: dict[str, Path], refresh: bool) -> None:
    focus = bbox(config, "focus_bbox_utm40s")
    context = bbox(config, "context_bbox_utm40s")
    if not contains(context, focus):
        raise ValueError("context_bbox_utm40s must contain focus_bbox_utm40s")

    source_url = resolve_hyscores_tiff(config)
    if refresh or not paths["context_depth_raw"].exists():
        extract_hyscores(source_url, context, paths["context_depth_raw"])
    if refresh or not paths["context_depth"].exists():
        positive_depth(paths["context_depth_raw"], paths["context_depth"])
    if refresh or not paths["context_elevation"].exists():
        download_rge_alti(context, float(config.get("topography_resolution_m", 0.5)), paths["context_elevation"])
    if refresh or not paths["focus_depth"].exists():
        crop_raster(paths["context_depth"], focus, paths["focus_depth"])
    if refresh or not paths["focus_elevation"].exists():
        crop_raster(paths["context_elevation"], focus, paths["focus_elevation"])
    if config.get("orthophoto_enabled", False) and (refresh or not paths["focus_orthophoto"].exists()):
        download_orthophoto(
            focus,
            float(config.get("orthophoto_resolution_m", 0.2)),
            str(config.get("orthophoto_layer", ORTHOPHOTO_LAYER)),
            paths["focus_orthophoto"],
        )
    if config.get("orthophoto_enabled", False) and (refresh or not paths["context_orthophoto"].exists()):
        download_orthophoto(
            context,
            float(config.get("orthophoto_3d_resolution_m", 0.4)),
            str(config.get("orthophoto_layer", ORTHOPHOTO_LAYER)),
            paths["context_orthophoto"],
        )
    if config.get("locator_map_enabled", False) and (refresh or not paths["locator_elevation"].exists()):
        download_rge_alti(
            bbox(config, "locator_bbox_utm40s"),
            float(config.get("locator_resolution_m", 20.0)),
            paths["locator_elevation"],
        )
    if config.get("locator_map_enabled", False) and config.get("locator_bathymetry_enabled", False) and (refresh or not paths["locator_bathymetry"].exists()):
        locator_dataset = gdal.Open(str(paths["locator_elevation"]))
        if locator_dataset is None:
            raise RuntimeError(f"Cannot open {paths['locator_elevation']} for the GEBCO target grid")
        download_gebco_relief(
            bbox(config, "locator_bbox_utm40s"),
            locator_dataset.RasterXSize,
            locator_dataset.RasterYSize,
            int(config.get("locator_gebco_request_width_px", 2000)),
            str(config.get("locator_gebco_layer", GEBCO_LAYER)),
            paths["locator_bathymetry"],
        )


def render(config: dict, paths: dict[str, Path]) -> None:
    title = str(config["title"])
    rotation_k = int(config.get("rotation_k", 0))
    author = str(config.get("plate_author", "")).strip()
    copyright_year = int(config.get("copyright_year", 2026))
    map_license = str(config.get("map_license", "")).strip()
    copyright_text = f"© {copyright_year} {author}" if author else None
    if copyright_text and map_license:
        copyright_text += f" · {map_license}"
    detailed_sources = (
        "Bathymétrie : Projet HYSCORES (Ifremer, UBO, Office de l'Eau Réunion), 2015, "
        "incluant Litto3D · Topographie : IGN RGE ALTI, mise à jour arrêtée en 2024"
    )
    orthophoto_sources = detailed_sources + " · Orthophoto : IGN BD ORTHO, prise de vue 22-07-2025"
    for key in ("context_depth", "context_elevation", "focus_depth", "focus_elevation"):
        if not paths[key].exists():
            raise FileNotFoundError(f"Missing {paths[key]}; run without --render-only first")

    if config.get("locator_map_enabled", False):
        if not paths["locator_elevation"].exists():
            raise FileNotFoundError(f"Missing {paths['locator_elevation']}; run without --render-only first")
        marker = tuple(map(float, config["locator_marker_utm40s"]))
        if len(marker) != 2:
            raise ValueError("locator_marker_utm40s must contain [easting, northing]")
        make_locator_map(
            paths["locator_elevation"],
            paths["output_locator"],
            marker,
            str(config.get("locator_label", title)),
            output_width=int(config.get("locator_output_width_px", 2400)),
            bathymetry_path=paths["locator_bathymetry"] if config.get("locator_bathymetry_enabled", False) else None,
            bathymetry_blur_px=float(config.get("locator_gebco_blur_px", 8.0)),
        )

    make_clean_plan(
        paths["focus_depth"],
        paths["focus_elevation"],
        Path("-"),
        paths["output_2d"],
        title,
        max_depth=float(config.get("max_depth_m", 20)),
        rotation_k=rotation_k,
        output_scale=float(config.get("output_scale", 1.0)),
        copyright_text=copyright_text,
        source_text=detailed_sources,
        open_label_offsets_px=config.get("plan_open_label_offsets_px"),
    )
    if config.get("orthophoto_enabled", False):
        if not paths["focus_orthophoto"].exists():
            raise FileNotFoundError(f"Missing {paths['focus_orthophoto']}; run without --render-only first")
        make_clean_plan(
            paths["focus_depth"],
            paths["focus_elevation"],
            Path("-"),
            paths["output_2d_ortho"],
            title,
            max_depth=float(config.get("max_depth_m", 20)),
            rotation_k=rotation_k,
            output_scale=float(config.get("output_scale", 1.0)),
            land_imagery_path=paths["focus_orthophoto"],
            copyright_text=copyright_text,
            source_text=orthophoto_sources,
            open_label_offsets_px=config.get("plan_open_label_offsets_px"),
        )
    make_pretty_3d_from_offshore(
        paths["context_depth"],
        paths["context_elevation"],
        Path("-"),
        paths["output_3d"],
        title,
        max_depth=float(config.get("max_depth_m", 20)),
        decorate=False,
        rotation_k=rotation_k,
        camera_tilt=float(config.get("camera_tilt", 0.34)),
        north_south_projection_scale=float(config.get("north_south_projection_scale", 1.0)),
        horizontal_crop_fraction=float(config.get("horizontal_crop_fraction", 0.0)),
        east_crop_fraction=float(config.get("east_crop_fraction", config.get("horizontal_crop_fraction", 0.0))),
        west_crop_fraction=float(config.get("west_crop_fraction", config.get("horizontal_crop_fraction", 0.0))),
        south_crop_fraction=float(config.get("south_crop_fraction", 0.0)),
        coast_frame_fraction=float(config.get("coast_frame_fraction", 0.44)),
        vertical_exaggeration=float(config.get("vertical_exaggeration", 7.6)),
        output_scale=float(config.get("output_scale", 1.0)),
        bridge_decks=config.get("bridge_decks"),
        copyright_text=copyright_text,
        source_text=detailed_sources,
    )
    if config.get("orthophoto_enabled", False):
        if not paths["context_orthophoto"].exists():
            raise FileNotFoundError(f"Missing {paths['context_orthophoto']}; run without --render-only first")
        make_pretty_3d_from_offshore(
            paths["context_depth"],
            paths["context_elevation"],
            Path("-"),
            paths["output_3d_ortho"],
            title,
            max_depth=float(config.get("max_depth_m", 20)),
            decorate=False,
            rotation_k=rotation_k,
            camera_tilt=float(config.get("camera_tilt", 0.34)),
            north_south_projection_scale=float(config.get("north_south_projection_scale", 1.0)),
            horizontal_crop_fraction=float(config.get("horizontal_crop_fraction", 0.0)),
            east_crop_fraction=float(config.get("east_crop_fraction", config.get("horizontal_crop_fraction", 0.0))),
            west_crop_fraction=float(config.get("west_crop_fraction", config.get("horizontal_crop_fraction", 0.0))),
            south_crop_fraction=float(config.get("south_crop_fraction", 0.0)),
            coast_frame_fraction=float(config.get("coast_frame_fraction", 0.44)),
            vertical_exaggeration=float(config.get("vertical_exaggeration", 7.6)),
            output_scale=float(config.get("output_scale", 1.0)),
            land_imagery_path=paths["context_orthophoto"],
            bridge_decks=config.get("bridge_decks"),
            copyright_text=copyright_text,
            source_text=orthophoto_sources,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate 2D and 3D topo-bathymetric maps for a Reunion coastal site")
    parser.add_argument("config", type=Path, help="Site JSON configuration")
    parser.add_argument("--refresh", action="store_true", help="Redownload and rebuild every source raster")
    parser.add_argument("--render-only", action="store_true", help="Reuse existing source rasters")
    args = parser.parse_args()

    config_path = args.config.expanduser().resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    paths = paths_for(config)
    if not args.render_only:
        acquire(config, paths, args.refresh)
    render(config, paths)

    print("\nSources")
    print(raster_summary(paths["focus_depth"]))
    print(raster_summary(paths["context_depth"]))
    print("\nOutputs")
    print(paths["output_2d"])
    if config.get("orthophoto_enabled", False):
        print(paths["output_2d_ortho"])
    print(paths["output_3d"])
    if config.get("orthophoto_enabled", False):
        print(paths["output_3d_ortho"])
    if config.get("locator_map_enabled", False):
        print(paths["output_locator"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
