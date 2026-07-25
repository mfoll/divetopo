from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from cartography.config import ROOT, bbox, region_manifest


RGE_ALTI_WMS = "https://data.geopf.fr/wms-r/wms"
RGE_ALTI_LAYER = "ELEVATION.ELEVATIONGRIDCOVERAGE.HIGHRES"
ORTHOPHOTO_LAYER = "HR.ORTHOIMAGERY.ORTHOPHOTOS"
GEBCO_WMS = "https://wms.gebco.net/2024/mapserv"
GEBCO_LAYER = "GEBCO_2024"
EXPECTED_CRS = str(region_manifest({"region": "reunion"})["crs"]["code"])
CACHE_MANIFEST_SCHEMA = 1


def cache_artifact_keys(config: Mapping[str, Any]) -> tuple[str, ...]:
    keys = [
        "context_depth_raw",
        "context_depth",
        "context_elevation",
        "focus_depth",
        "focus_elevation",
    ]
    if config.get("orthophoto_enabled", False):
        keys.extend(("context_orthophoto", "focus_orthophoto"))
    if config.get("locator_map_enabled", False):
        keys.append("locator_elevation")
        if config.get("locator_bathymetry_enabled", False):
            keys.append("locator_bathymetry")
    return tuple(keys)


def cache_manifest_path(
    config: Mapping[str, Any],
    paths: Mapping[str, Path],
) -> Path:
    return paths["context_depth"].parent / f"{config['slug']}-cache-manifest.json"


def source_contract(config: Mapping[str, Any]) -> dict[str, Any]:
    manifest = region_manifest(config)
    focus = list(bbox(config, "focus_bbox_utm40s"))
    context = list(bbox(config, "context_bbox_utm40s"))
    focus_resolution = float(config.get("topography_resolution_m", 0.5))
    context_resolution = float(
        config.get("context_topography_resolution_m", focus_resolution)
    )
    contract: dict[str, Any] = {
        "crs": str(manifest["crs"]["code"]),
        "hyscores": {
            "tiff_url": str(config["hyscores_tiff_url"]),
            "focus_bbox_utm40s": focus,
            "context_bbox_utm40s": context,
        },
        "rge_alti": {
            "wms_url": RGE_ALTI_WMS,
            "layer": RGE_ALTI_LAYER,
            "focus_resolution_m": focus_resolution,
            "context_resolution_m": context_resolution,
        },
        "orthophoto": None,
        "locator": None,
    }
    if config.get("orthophoto_enabled", False):
        contract["orthophoto"] = {
            "wms_url": RGE_ALTI_WMS,
            "layer": str(config["orthophoto_layer"]),
            "capture_date": str(config["orthophoto_capture_date"]),
            "focus_resolution_m": float(config.get("orthophoto_resolution_m", 0.2)),
            "context_resolution_m": float(
                config.get("orthophoto_3d_resolution_m", 0.4)
            ),
        }
    if config.get("locator_map_enabled", False):
        locator: dict[str, Any] = {
            "bbox_utm40s": list(bbox(config, "locator_bbox_utm40s")),
            "rge_alti_wms_url": RGE_ALTI_WMS,
            "rge_alti_layer": RGE_ALTI_LAYER,
            "resolution_m": float(config.get("locator_resolution_m", 20.0)),
            "bathymetry": None,
        }
        if config.get("locator_bathymetry_enabled", False):
            locator["bathymetry"] = {
                "wms_url": str(config["locator_gebco_wms_url"]),
                "layer": str(config["locator_gebco_layer"]),
                "request_width_px": int(
                    config.get("locator_gebco_request_width_px", 2000)
                ),
            }
        contract["locator"] = locator
    return contract


def _portable_path(path: Path) -> str:
    resolved = path.resolve(strict=False)
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        return str(resolved)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_cache_manifest(
    config: Mapping[str, Any],
    paths: Mapping[str, Path],
) -> dict[str, Any]:
    manifest_path = cache_manifest_path(config, paths)
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"Missing cache provenance manifest: {manifest_path}"
        )
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Invalid cache provenance manifest: {manifest_path}") from error
    if not isinstance(manifest, dict):
        raise ValueError(f"Invalid cache provenance manifest: {manifest_path}")
    return manifest


def validate_cache_manifest(
    config: Mapping[str, Any],
    paths: Mapping[str, Path],
    *,
    verify_hashes: bool,
) -> dict[str, Any]:
    manifest = read_cache_manifest(config, paths)
    manifest_path = cache_manifest_path(config, paths)
    if manifest.get("schema_version") != CACHE_MANIFEST_SCHEMA:
        raise ValueError(f"Unsupported cache manifest schema: {manifest_path}")
    if manifest.get("source_contract") != source_contract(config):
        raise ValueError(
            f"Cached sources no longer match the site configuration: {manifest_path}"
        )
    records = manifest.get("artifacts")
    if not isinstance(records, dict):
        raise ValueError(f"Cache manifest has no artifact records: {manifest_path}")
    expected_keys = set(cache_artifact_keys(config))
    if set(records) != expected_keys:
        raise ValueError(
            f"Cache manifest artifact set does not match the site configuration: {manifest_path}"
        )
    for key in sorted(expected_keys):
        record = records.get(key)
        if not isinstance(record, dict):
            raise ValueError(f"Invalid cache manifest record for {key}: {manifest_path}")
        path = paths[key]
        if record.get("path") != _portable_path(path):
            raise ValueError(
                f"Cached path for {key} no longer matches the configuration: {manifest_path}"
            )
        if verify_hashes:
            if not path.exists():
                raise FileNotFoundError(f"Missing cached artifact {key}: {path}")
            if record.get("sha256") != sha256_file(path):
                raise ValueError(
                    f"Cached artifact {key} has changed since acquisition: {path}"
                )
    return manifest


def write_cache_manifest(
    config: Mapping[str, Any],
    paths: Mapping[str, Path],
) -> Path:
    artifacts = {}
    for key in cache_artifact_keys(config):
        path = paths[key]
        if not path.exists():
            raise FileNotFoundError(f"Cannot record missing cached artifact {key}: {path}")
        artifacts[key] = {
            "path": _portable_path(path),
            "sha256": sha256_file(path),
        }
    manifest = {
        "schema_version": CACHE_MANIFEST_SCHEMA,
        "source_contract": source_contract(config),
        "artifacts": artifacts,
    }
    output = cache_manifest_path(config, paths)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f"{output.name}.part")
    try:
        temporary.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    return output


def preflight_cache_manifest(
    config: Mapping[str, Any],
    paths: Mapping[str, Path],
    *,
    refresh: bool,
) -> dict[str, Any] | None:
    if refresh:
        return None
    manifest_path = cache_manifest_path(config, paths)
    if manifest_path.exists():
        return validate_cache_manifest(config, paths, verify_hashes=False)
    if any(paths[key].exists() for key in cache_artifact_keys(config)):
        raise ValueError(
            f"Existing cache has no source provenance manifest: {manifest_path}"
        )
    return None
