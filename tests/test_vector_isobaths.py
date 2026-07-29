from __future__ import annotations

import unittest

import numpy as np

from cartography.vector_isobaths import (
    extract_vector_isobaths,
    validate_vector_isobath_payload,
)


class VectorIsobathTests(unittest.TestCase):
    @staticmethod
    def planar_depth(size: int = 80) -> np.ndarray:
        x = np.broadcast_to(
            np.arange(size, dtype=np.float64),
            (size, size),
        )
        y = np.arange(size, dtype=np.float64)[:, None]
        return (4.0 + x + 3.0 * np.sin(y / 5.0)).copy()

    def test_extracts_grid_pixel_payload_and_diagnostics(self) -> None:
        depth = self.planar_depth()

        payload, diagnostics = extract_vector_isobaths(
            depth,
            np.ones_like(depth, dtype=bool),
            (20, 40),
        )

        self.assertEqual(
            set(payload),
            {"coordinateSpace", "levels"},
        )
        self.assertEqual(payload["coordinateSpace"], "grid-pixels")
        self.assertEqual(set(payload["levels"]), {"20", "40"})
        self.assertGreaterEqual(diagnostics["totals"]["polylines"], 2)
        self.assertGreater(diagnostics["totals"]["points"], 0)
        self.assertTrue(diagnostics["schemaValid"])
        self.assertTrue(diagnostics["bounds"]["valid"])
        self.assertEqual(
            diagnostics["grid"],
            {"width": 80, "height": 80},
        )
        self.assertTrue(
            diagnostics["reprojectionResidualM"]["withinTolerance"]
        )
        self.assertLessEqual(
            diagnostics["reprojectionResidualM"]["max"],
            0.05,
        )

    def test_elevation_source_matches_positive_depth_source(self) -> None:
        depth = self.planar_depth()
        sea_mask = np.ones_like(depth, dtype=bool)

        depth_payload, _ = extract_vector_isobaths(
            depth,
            sea_mask,
            (25,),
        )
        elevation_payload, _ = extract_vector_isobaths(
            -depth,
            sea_mask,
            (25,),
            source_kind="elevation",
        )

        self.assertEqual(elevation_payload, depth_payload)

    def test_mask_excludes_contours_outside_the_sea(self) -> None:
        depth = self.planar_depth()
        sea_mask = np.zeros_like(depth, dtype=bool)
        sea_mask[:, :30] = True

        payload, diagnostics = extract_vector_isobaths(
            depth,
            sea_mask,
            (20, 40),
        )

        self.assertGreater(len(payload["levels"]["20"]), 0)
        self.assertEqual(payload["levels"]["40"], [])
        self.assertEqual(diagnostics["levels"]["40"]["points"], 0)

    def test_rejects_incompatible_or_invalid_inputs(self) -> None:
        depth = self.planar_depth(10)
        mask = np.ones_like(depth, dtype=bool)

        with self.assertRaisesRegex(ValueError, "same shape"):
            extract_vector_isobaths(depth, mask[:-1], (5,))
        with self.assertRaisesRegex(ValueError, "duplicates"):
            extract_vector_isobaths(depth, mask, (5, 5))
        with self.assertRaisesRegex(ValueError, "non-negative"):
            extract_vector_isobaths(depth, mask, (-5,))
        with self.assertRaisesRegex(ValueError, "non-negative depths"):
            extract_vector_isobaths(-depth, mask, (5,))

    def test_validation_rejects_wrong_schema_and_out_of_bounds_points(
        self,
    ) -> None:
        with self.assertRaisesRegex(ValueError, "coordinateSpace"):
            validate_vector_isobath_payload(
                {"coordinateSpace": "meters", "levels": {}},
                width=10,
                height=10,
            )

        payload = {
            "coordinateSpace": "grid-pixels",
            "levels": {
                "5": [
                    [
                        [1.0, 1.0],
                        [2.0, 2.0],
                        [11.0, 3.0],
                    ]
                ]
            },
        }
        with self.assertRaisesRegex(ValueError, "outside"):
            validate_vector_isobath_payload(
                payload,
                width=10,
                height=10,
            )

    def test_validation_reports_reprojection_residuals(self) -> None:
        depth = self.planar_depth(20)
        depth = np.broadcast_to(
            np.arange(20, dtype=np.float64),
            (20, 20),
        ).copy()
        payload = {
            "coordinateSpace": "grid-pixels",
            "levels": {
                "5": [
                    [
                        [5.0, 1.0],
                        [5.25, 2.0],
                    ]
                ]
            },
        }

        diagnostics = validate_vector_isobath_payload(
            payload,
            width=20,
            height=20,
            depth=depth,
            residual_tolerance_m=0.1,
        )

        self.assertEqual(
            diagnostics["reprojectionResidualM"]["samples"],
            2,
        )
        self.assertAlmostEqual(
            diagnostics["reprojectionResidualM"]["max"],
            0.25,
        )
        self.assertFalse(
            diagnostics["reprojectionResidualM"]["withinTolerance"]
        )


if __name__ == "__main__":
    unittest.main()
