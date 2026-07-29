from __future__ import annotations

from collections.abc import Mapping

import numpy as np


DEPTH_STOPS_M = np.array(
    [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 30, 40],
    dtype=np.float32,
)

LEGACY_COLORS_RGB = (
    (235, 35, 28),
    (246, 88, 28),
    (252, 154, 31),
    (250, 220, 42),
    (151, 226, 89),
    (67, 211, 199),
    (47, 170, 221),
    (39, 122, 210),
    (28, 82, 178),
    (16, 50, 135),
    (8, 31, 100),
    (4, 20, 78),
    (1, 9, 42),
)

_IFREMER_DEEP_COLORS_RGB = (
    (252, 123, 67),
    (253, 174, 82),
    (251, 216, 119),
    (222, 233, 145),
    (164, 224, 151),
    (99, 207, 166),
    (46, 181, 182),
    (31, 148, 190),
    (42, 94, 175),
    (82, 54, 137),
)

CORAL_BLUE_PHYSICAL_DEPTHS_M = np.array(
    [
        0.0,
        2.5,
        3.5,
        4.25,
        5.0,
        5.75,
        6.5,
        7.25,
        8.0,
        8.75,
        9.5,
        10.0,
        11.0,
        12.0,
        13.5,
        15.0,
        17.5,
        20.0,
        22.5,
        25.0,
        30.0,
        40.0,
    ],
    dtype=np.float32,
)
CORAL_BLUE_COLORS_RGB = (
    (250, 58, 54),
    (248, 65, 48),
    (250, 78, 43),
    (252, 98, 38),
    (255, 125, 34),
    (255, 160, 32),
    (255, 195, 38),
    (250, 215, 46),
    (225, 220, 58),
    (175, 223, 74),
    (100, 220, 105),
    (45, 214, 150),
    (10, 204, 190),
    (0, 190, 220),
    (15, 170, 224),
    (30, 151, 224),
    (28, 126, 207),
    (25, 98, 181),
    (22, 62, 150),
    (18, 51, 134),
    (12, 38, 112),
    (6, 24, 82),
)

BATHYMETRY_PALETTES_RGB: Mapping[str, tuple[tuple[int, int, int], ...]] = {
    "legacy": LEGACY_COLORS_RGB,
    "ifremer_deep_red": (
        (162, 20, 38),
        (205, 33, 43),
        (237, 63, 50),
        *_IFREMER_DEEP_COLORS_RGB,
    ),
    "ifremer_coral": (
        (190, 42, 54),
        (224, 61, 63),
        (246, 91, 67),
        *_IFREMER_DEEP_COLORS_RGB,
    ),
    "ifremer_red_orange": (
        (194, 43, 23),
        (228, 69, 27),
        (247, 104, 40),
        *_IFREMER_DEEP_COLORS_RGB,
    ),
    "coral_blue": CORAL_BLUE_COLORS_RGB,
}

# Soleil clair sans ligne 5, selected after full-resolution visual comparison. The
# C depth transform remains independent from these physical colour anchors.
# The legacy palette remains the runtime fallback for configurations that do
# not opt in explicitly.
VALIDATED_BATHYMETRY_PALETTE = "coral_blue"
BATHYMETRY_DEPTH_SCALES = frozenset({"legacy_linear", "coral_blue"})

CORAL_BLUE_DEPTH_ANCHORS_M = np.array(
    [0.0, 5.0, 10.0, 15.0, 20.0],
    dtype=np.float32,
)
CORAL_BLUE_PALETTE_FRACTIONS = np.array(
    [0.0, 0.34, 0.68, 0.82, 0.94],
    dtype=np.float32,
)

SEA_SLOPE_MAX_DEG = 30.0
SEA_SLOPE_MAX_DARKENING = 0.35
SEA_SLOPE_SMOOTHING_PASSES = 2
LAND_SLOPE_MAX_DEG = 30.0
LAND_SLOPE_MAX_DARKENING = 0.18
LAND_SLOPE_SMOOTHING_PASSES = 64


def remap_bathymetric_depth(
    depth: np.ndarray,
    *,
    maximum_depth_m: float,
    depth_scale: str,
) -> np.ndarray:
    if maximum_depth_m <= 0.0:
        raise ValueError("Maximum bathymetric depth must be positive")

    if depth_scale == "legacy_linear":
        shallow_colour_depth_m = 2.0
        if maximum_depth_m > shallow_colour_depth_m:
            return (
                np.maximum(depth - shallow_colour_depth_m, 0.0)
                * maximum_depth_m
                / (maximum_depth_m - shallow_colour_depth_m)
            )
        return np.maximum(depth - shallow_colour_depth_m, 0.0)

    if depth_scale == "coral_blue":
        if maximum_depth_m < CORAL_BLUE_DEPTH_ANCHORS_M[-1]:
            raise ValueError(
                "The coral_blue scale needs a maximum depth of at least 20 m"
            )
        clipped_depth = np.clip(depth, 0.0, maximum_depth_m)
        if np.isclose(
            maximum_depth_m,
            float(CORAL_BLUE_DEPTH_ANCHORS_M[-1]),
        ):
            physical_anchors = CORAL_BLUE_DEPTH_ANCHORS_M
            palette_fractions = np.array(
                [0.0, 0.34, 0.68, 0.82, 1.0],
                dtype=np.float32,
            )
        else:
            physical_anchors = np.append(
                CORAL_BLUE_DEPTH_ANCHORS_M,
                maximum_depth_m,
            )
            palette_fractions = np.append(
                CORAL_BLUE_PALETTE_FRACTIONS,
                1.0,
            )
        return np.interp(
            clipped_depth,
            physical_anchors,
            palette_fractions * maximum_depth_m,
        )

    raise ValueError(
        "Bathymetric depth scale must be 'legacy_linear' or "
        "'coral_blue'"
    )


def bathymetry_palette(
    depth: np.ndarray,
    *,
    maximum_depth_m: float = 40.0,
    palette_name: str = "legacy",
    depth_scale: str = "legacy_linear",
) -> np.ndarray:
    try:
        colors = np.asarray(
            BATHYMETRY_PALETTES_RGB[palette_name],
            dtype=np.float32,
        )
    except KeyError as error:
        choices = ", ".join(sorted(BATHYMETRY_PALETTES_RGB))
        raise ValueError(
            f"Unknown bathymetric palette {palette_name!r}; choose {choices}"
        ) from error

    remapped_depth = remap_bathymetric_depth(
        np.asarray(depth, dtype=np.float32),
        maximum_depth_m=maximum_depth_m,
        depth_scale=depth_scale,
    )
    if palette_name == "coral_blue":
        selected = CORAL_BLUE_PHYSICAL_DEPTHS_M <= maximum_depth_m
        physical_stops = CORAL_BLUE_PHYSICAL_DEPTHS_M[selected]
        colors = colors[selected]
        if not np.isclose(physical_stops[-1], maximum_depth_m):
            interpolated_color = np.array(
                [
                    np.interp(
                        maximum_depth_m,
                        CORAL_BLUE_PHYSICAL_DEPTHS_M,
                        np.asarray(CORAL_BLUE_COLORS_RGB)[:, channel],
                    )
                    for channel in range(3)
                ],
                dtype=np.float32,
            )
            physical_stops = np.append(physical_stops, maximum_depth_m)
            colors = np.vstack((colors, interpolated_color))
        palette_stops = remap_bathymetric_depth(
            physical_stops,
            maximum_depth_m=maximum_depth_m,
            depth_scale=depth_scale,
        )
    else:
        palette_stops = DEPTH_STOPS_M
    values = np.clip(remapped_depth, palette_stops[0], palette_stops[-1])
    result = np.zeros((*values.shape, 3), dtype=np.float32)
    for index in range(len(palette_stops) - 1):
        low = palette_stops[index]
        high = palette_stops[index + 1]
        selected = (values >= low) & (values <= high)
        weight = ((values[selected] - low) / (high - low))[:, None]
        result[selected] = (
            colors[index] * (1.0 - weight)
            + colors[index + 1] * weight
        )
    result[values >= palette_stops[-1]] = colors[-1]
    return result.astype(np.uint8)
