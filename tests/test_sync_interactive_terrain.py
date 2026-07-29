from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).parents[1]
    / "apps"
    / "web"
    / "scripts"
    / "sync_interactive_terrain.py"
)
SPEC = importlib.util.spec_from_file_location("sync_interactive_terrain", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
SYNC = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SYNC)


class InteractiveTerrainSyncTests(unittest.TestCase):
    def test_sync_accepts_legacy_package_without_vector_isobaths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_root = root / "canonical"
            site_root = source_root / "example"
            site_root.mkdir(parents=True)
            files = {
                "metadata": site_root / "terrain.json",
                "height": site_root / "height.bin",
                "validMask": site_root / "valid-mask.bin",
                "isobathMask": site_root / "isobath-mask.bin",
                "topographicTexture": site_root / "topographic.webp",
                "orthophotoTexture": site_root / "orthophoto.webp",
            }
            for index, path in enumerate(files.values()):
                path.write_bytes(f"legacy-{index}".encode())
            records = {
                key: {
                    "path": path.relative_to(source_root).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": SYNC.sha256(path),
                }
                for key, path in files.items()
            }
            (source_root / "manifest.json").write_text(
                json.dumps(
                    {
                        "schemaVersion": 2,
                        "sites": [
                            {
                                "slug": "example",
                                "title": "Example",
                                "metadata": "example/terrain.json",
                                "files": records,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            output_root = root / "public" / "terrain"
            SYNC.sync_package(source_root, output_root)

            self.assertTrue((output_root / "example/terrain.json").is_file())
            self.assertFalse(
                (output_root / "example/isobaths-vector.json").exists()
            )

    def test_sync_copies_only_manifested_files_and_removes_stale_assets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_root = root / "canonical"
            site_root = source_root / "example"
            site_root.mkdir(parents=True)
            files = {
                "metadata": site_root / "terrain.json",
                "height": site_root / "height.bin",
                "validMask": site_root / "valid-mask.bin",
                "isobathMask": site_root / "isobath-mask.bin",
                "vectorIsobaths": site_root / "isobaths-vector.json",
                "topographicTexture": site_root / "topographic.webp",
                "orthophotoTexture": site_root / "orthophoto.webp",
            }
            for index, path in enumerate(files.values()):
                path.write_bytes(f"artifact-{index}".encode())

            records = {
                key: {
                    "path": path.relative_to(source_root).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": SYNC.sha256(path),
                }
                for key, path in files.items()
            }
            manifest = {
                "schemaVersion": 2,
                "sites": [
                    {
                        "slug": "example",
                        "title": "Example",
                        "metadata": "example/terrain.json",
                        "files": records,
                    }
                ],
            }
            (source_root / "manifest.json").write_text(
                json.dumps(manifest),
                encoding="utf-8",
            )

            output_root = root / "public" / "terrain"
            output_root.mkdir(parents=True)
            (output_root / "stale.bin").write_bytes(b"stale")

            SYNC.sync_package(source_root, output_root)

            self.assertFalse((output_root / "stale.bin").exists())
            self.assertTrue((output_root / "manifest.json").is_file())
            for record in records.values():
                copied = output_root / record["path"]
                self.assertTrue(copied.is_file())
                self.assertEqual(SYNC.sha256(copied), record["sha256"])

    def test_manifest_cannot_escape_the_canonical_package(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outside = root / "outside.bin"
            outside.write_bytes(b"outside")
            source_root = root / "canonical"
            source_root.mkdir()

            with self.assertRaisesRegex(ValueError, "escapes"):
                SYNC.checked_source(source_root, "../outside.bin")


if __name__ == "__main__":
    unittest.main()
