"""Temporarily expose pending regional packages to the local Web dev server.

The published Web contract intentionally filters ``web.published`` sites out
of routes and ``apps/web/public``.  This helper is a reversible development
overlay for camera calibration only: it restores the already validated public
assets from their site-package commits, appends the pending sites to the
regional manifests, and removes every generated file on exit.
"""

from __future__ import annotations

import io
import json
import shutil
import subprocess
import sys
import tarfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
WEB_ROOT = REPOSITORY_ROOT / "apps" / "web"
PUBLIC_ROOT = WEB_ROOT / "public"
MANIFEST_ROOT = WEB_ROOT / "content"
SCRIPTS_ROOT = WEB_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


def load_region_configs(repository_root: Path, region_slug: str) -> list[dict[str, Any]]:
    """Load inventory configs without requiring the cartography runtime."""
    region_path = repository_root / "regions" / region_slug / "region.json"
    region = json.loads(region_path.read_text(encoding="utf-8"))
    configs: list[dict[str, Any]] = []
    seen: set[str] = set()
    for site in region.get("sites", []):
        config_path = repository_root / str(site["config"])
        config = json.loads(config_path.read_text(encoding="utf-8"))
        if config.get("slug") != site.get("slug"):
            raise PendingPreviewError(
                f"{config_path}: slug does not match its region inventory entry"
            )
        slug = str(config["slug"])
        if slug in seen:
            raise PendingPreviewError(f"{region_slug}: duplicate slug: {slug}")
        seen.add(slug)
        config["_config_path"] = config_path.relative_to(
            repository_root
        ).as_posix()
        configs.append(config)
    return configs


@dataclass(frozen=True)
class PendingPackage:
    region: str
    slug: str
    source_commit: str


# These are the authoritative site-package commits audited by the regional
# coordinators.  They are deliberately local-only provenance references, not
# release dependencies.
PENDING_PACKAGES = (
    PendingPackage(
        "bouches-du-rhone",
        "imperial-du-milieu-riou",
        "7d4c6ee6f79dcb050974779bdcd55ed112c4cde6",
    ),
    PendingPackage(
        "var-ouest",
        "plate-aux-merous",
        "59b824b3ce7183b997c6b629d44095cf7d21ab10",
    ),
    PendingPackage(
        "var-ouest",
        "pierre-du-jas",
        "b17046ef3a00d0edee022bf496742fee05240543",
    ),
    PendingPackage(
        "var-centre",
        "pointe-escampobariou",
        "40c100f18bb501f2b17734956696be98d59288a1",
    ),
    PendingPackage(
        "var-est",
        "sec-des-suisses-cigales",
        "119c76c8c597d63a8b794cdac5a046c3f1bbe6cd",
    ),
    PendingPackage(
        "alpes-maritimes",
        "cap-gros",
        "690f174cf6e11827d86b7d79a160ce70f3fdf6f6",
    ),
)


class PendingPreviewError(RuntimeError):
    """The reversible pending-site overlay could not be prepared."""


class PendingPreview:
    """Stage pending site assets and restore the repository on exit."""

    def __init__(self) -> None:
        self._manifests: dict[Path, bytes] = {}
        self._staged_roots: list[Path] = []
        self._active = False

    @staticmethod
    def _run_git(*arguments: str) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            ("git", *arguments),
            cwd=REPOSITORY_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def _archive_exists(self, package: PendingPackage) -> None:
        result = self._run_git("cat-file", "-e", f"{package.source_commit}^{{commit}}")
        if result.returncode != 0:
            raise PendingPreviewError(
                f"Missing local source commit for {package.region}/{package.slug}: "
                f"{package.source_commit}"
            )

    def _extract_assets(self, package: PendingPackage) -> None:
        map_root = PUBLIC_ROOT / "maps" / package.region / package.slug
        terrain_root = PUBLIC_ROOT / "terrain" / package.slug
        if map_root.exists() or terrain_root.exists():
            raise PendingPreviewError(
                f"Refusing to overwrite existing pending preview paths for "
                f"{package.region}/{package.slug}"
            )
        archive_paths = (
            f"apps/web/public/maps/{package.region}/{package.slug}",
            f"apps/web/public/terrain/{package.slug}",
        )
        available_paths: list[str] = []
        for archive_path in archive_paths:
            listing = self._run_git(
                "ls-tree",
                "-r",
                "--name-only",
                package.source_commit,
                "--",
                archive_path,
            )
            if listing.returncode != 0:
                raise PendingPreviewError(
                    f"Could not inspect local assets for {package.region}/{package.slug}"
                )
            if listing.stdout.strip():
                available_paths.append(archive_path)
        if not available_paths:
            raise PendingPreviewError(
                f"No local public assets found for {package.region}/{package.slug}"
            )
        result = self._run_git(
            "archive",
            package.source_commit,
            *available_paths,
        )
        if result.returncode != 0:
            detail = result.stderr.decode().strip()
            raise PendingPreviewError(
                f"Could not read local assets for {package.region}/{package.slug}: "
                f"{detail or 'git archive failed'}"
            )
        try:
            with tarfile.open(fileobj=io.BytesIO(result.stdout), mode="r:") as archive:
                repository_root = REPOSITORY_ROOT.resolve()
                for member in archive.getmembers():
                    target = (REPOSITORY_ROOT / member.name).resolve()
                    if target != repository_root and repository_root not in target.parents:
                        raise PendingPreviewError(
                            f"Unsafe asset path in source package: {member.name}"
                        )
                archive.extractall(REPOSITORY_ROOT)
        except tarfile.TarError as error:
            raise PendingPreviewError(
                f"Could not unpack local assets for {package.region}/{package.slug}"
            ) from error
        if not terrain_root.exists():
            source_terrain = (
                REPOSITORY_ROOT
                / "regions"
                / package.region
                / "outputs"
                / "interactive-terrain"
                / package.slug
            )
            if not source_terrain.is_dir():
                raise PendingPreviewError(
                    f"Missing local interactive terrain for {package.region}/{package.slug}"
                )
            terrain_root.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source_terrain, terrain_root)
        self._staged_roots.extend((map_root, terrain_root))

    @staticmethod
    def _manifest_path(region: str) -> Path:
        return MANIFEST_ROOT / f"{region}-map-manifest.json"

    def _append_site_to_manifest(
        self,
        package: PendingPackage,
        config: dict[str, Any],
    ) -> None:
        import build_paca_map_assets as builder

        manifest_path = self._manifest_path(package.region)
        if manifest_path not in self._manifests:
            self._manifests[manifest_path] = manifest_path.read_bytes()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        locator_bounds = manifest["westCoastLocator"].get("boundsWgs84")
        if not isinstance(locator_bounds, dict):
            raise PendingPreviewError(
                f"{package.region}: regional locator has no WGS84 bounds"
            )

        builder.REGION_SLUG = package.region
        builder.OUTPUT_ROOT = (
            REPOSITORY_ROOT / "regions" / package.region / "outputs"
        )
        builder.MANIFEST_PATH = manifest_path
        if any(site.get("slug") == package.slug for site in manifest["sites"]):
            return
        manifest["sites"].append(builder.build_site(config, locator_bounds))
        all_configs = load_region_configs(REPOSITORY_ROOT, package.region)
        manifest["plannedSites"] = [
            builder.build_planned_site(site_config, locator_bounds)
            for site_config in all_configs
        ]
        manifest["schemaVersion"] = 2
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def _build_manifests_with_runtime(self) -> None:
        runtime = REPOSITORY_ROOT / ".venv" / "bin" / "python"
        if not runtime.is_file():
            runtime = Path(sys.executable)
        result = subprocess.run(
            (str(runtime), str(Path(__file__).resolve()), "build-manifests"),
            cwd=REPOSITORY_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode != 0:
            detail = result.stderr.decode().strip() or result.stdout.decode().strip()
            raise PendingPreviewError(
                "Could not build pending local manifests with the project "
                f"runtime: {detail or 'builder failed'}"
            )

    def enable(self) -> None:
        if self._active:
            return
        try:
            for package in PENDING_PACKAGES:
                self._archive_exists(package)
                self._extract_assets(package)
                configs = load_region_configs(REPOSITORY_ROOT, package.region)
                config = next(
                    (
                        candidate
                        for candidate in configs
                        if candidate.get("slug") == package.slug
                    ),
                    None,
                )
                if config is None:
                    raise PendingPreviewError(
                        f"Missing pending config for {package.region}/{package.slug}"
                    )
                if config.get("web", {}).get("published") is True:
                    raise PendingPreviewError(
                        f"{package.region}/{package.slug} is already published"
                    )
            for region in {package.region for package in PENDING_PACKAGES}:
                manifest_path = self._manifest_path(region)
                self._manifests[manifest_path] = manifest_path.read_bytes()
            self._build_manifests_with_runtime()
            self._active = True
        except Exception:
            self.disable()
            raise

    def disable(self) -> None:
        for manifest_path, contents in self._manifests.items():
            manifest_path.write_bytes(contents)
        for root in reversed(self._staged_roots):
            if root.exists():
                shutil.rmtree(root)
        self._manifests.clear()
        self._staged_roots.clear()
        self._active = False


def build_manifests_for_active_preview() -> None:
    """Build the temporary manifests from a dependency-capable runtime."""
    preview = PendingPreview()
    for package in PENDING_PACKAGES:
        configs = load_region_configs(REPOSITORY_ROOT, package.region)
        config = next(
            (
                candidate
                for candidate in configs
                if candidate.get("slug") == package.slug
            ),
            None,
        )
        if config is None:
            raise PendingPreviewError(
                f"Missing pending config for {package.region}/{package.slug}"
            )
        preview._append_site_to_manifest(package, config)


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] != "build-manifests":
        raise SystemExit("usage: pending_preview.py build-manifests")
    build_manifests_for_active_preview()
