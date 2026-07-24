from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from generate_interactive_terrain import (
    DEFAULT_OUTPUT,
    artifact_record,
    fitted_dimensions,
    swap_output,
    validate_export,
)
from site_config import ROOT


class InteractiveTerrainPackageTests(unittest.TestCase):
    def test_default_output_is_owned_by_the_map_pipeline(self) -> None:
        self.assertEqual(
            DEFAULT_OUTPUT,
            ROOT / "outputs" / "interactive-terrain",
        )

    def test_heightfield_resize_preserves_footprint_vertices(self) -> None:
        self.assertEqual(
            fitted_dimensions(513, 257, 257, preserve_vertices=True),
            (257, 129),
        )

    def test_atomic_swap_removes_stale_previous_sites(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output_root = root / "interactive-terrain"
            output_root.mkdir()
            (output_root / "stale.txt").write_text("stale", encoding="utf-8")
            build_root = root / "build"
            build_root.mkdir()
            (build_root / "manifest.json").write_text("{}\n", encoding="utf-8")

            swap_output(build_root, output_root)

            self.assertFalse((output_root / "stale.txt").exists())
            self.assertTrue((output_root / "manifest.json").is_file())

    def test_manifest_records_validate_all_five_site_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_root = Path(directory)
            site_root = output_root / "example"
            site_root.mkdir()

            metadata = site_root / "terrain.json"
            metadata.write_text(
                """
{
  "grid": {
    "width": 2,
    "height": 2,
    "heightFile": "height.bin",
    "validMaskFile": "valid-mask.bin"
  },
  "textures": {
    "width": 2,
    "height": 2,
    "topographic": {"file": "topographic.webp"},
    "orthophoto": {"file": "orthophoto.webp"}
  }
}
""".strip()
                + "\n",
                encoding="utf-8",
            )
            height = site_root / "height.bin"
            height.write_bytes(b"\x00\x00" * 4)
            valid_mask = site_root / "valid-mask.bin"
            valid_mask.write_bytes(b"\x0f")
            topographic = site_root / "topographic.webp"
            orthophoto = site_root / "orthophoto.webp"
            Image.new("RGB", (2, 2), "red").save(topographic, "WEBP")
            Image.new("RGB", (2, 2), "blue").save(orthophoto, "WEBP")

            manifest = {
                "schemaVersion": 1,
                "sites": [
                    {
                        "slug": "example",
                        "title": "Example",
                        "metadata": "example/terrain.json",
                        "files": {
                            "metadata": artifact_record(metadata, output_root),
                            "height": artifact_record(height, output_root),
                            "validMask": artifact_record(valid_mask, output_root),
                            "topographicTexture": artifact_record(
                                topographic,
                                output_root,
                            ),
                            "orthophotoTexture": artifact_record(
                                orthophoto,
                                output_root,
                            ),
                        },
                    }
                ],
            }

            validate_export(output_root, manifest)
            height.write_bytes(b"\x00\x00")
            with self.assertRaisesRegex(ValueError, "artifact size"):
                validate_export(output_root, manifest)


if __name__ == "__main__":
    unittest.main()
