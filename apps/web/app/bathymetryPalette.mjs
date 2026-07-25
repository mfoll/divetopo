const DEPTH_STOPS_M = [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 30, 40];
const DEPTH_COLORS_RGB = [
  [235, 35, 28],
  [246, 88, 28],
  [252, 154, 31],
  [250, 220, 42],
  [151, 226, 89],
  [67, 211, 199],
  [47, 170, 221],
  [39, 122, 210],
  [28, 82, 178],
  [16, 50, 135],
  [8, 31, 100],
  [4, 20, 78],
  [1, 9, 42],
];
const SHALLOW_RED_DEPTH_M = 2;

/**
 * Match render_fused_relief.palette() exactly for a displayed depth.
 *
 * @param {number} depthM
 * @param {number} maximumDepthM
 * @returns {[number, number, number]}
 */
export function bathymetryColorRgb(depthM, maximumDepthM) {
  const remappedDepth =
    maximumDepthM > SHALLOW_RED_DEPTH_M
      ? Math.max(depthM - SHALLOW_RED_DEPTH_M, 0) *
        (maximumDepthM / (maximumDepthM - SHALLOW_RED_DEPTH_M))
      : Math.max(depthM - SHALLOW_RED_DEPTH_M, 0);
  const value = Math.min(
    Math.max(remappedDepth, DEPTH_STOPS_M[0]),
    Math.min(maximumDepthM, DEPTH_STOPS_M.at(-1)),
  );

  for (let index = 0; index < DEPTH_STOPS_M.length - 1; index += 1) {
    const low = DEPTH_STOPS_M[index];
    const high = DEPTH_STOPS_M[index + 1];
    if (value < low || value > high) continue;
    const weight = (value - low) / (high - low);
    return DEPTH_COLORS_RGB[index].map((channel, channelIndex) =>
      Math.trunc(
        channel * (1 - weight) +
          DEPTH_COLORS_RGB[index + 1][channelIndex] * weight,
      ),
    );
  }

  return [...DEPTH_COLORS_RGB.at(-1)];
}

/**
 * @param {number} depthM
 * @param {number} maximumDepthM
 */
export function bathymetryColorCss(depthM, maximumDepthM) {
  return `rgb(${bathymetryColorRgb(depthM, maximumDepthM).join(", ")})`;
}
