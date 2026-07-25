/**
 * Keep a resized orthographic camera inside its canonical initial frustum.
 *
 * A narrower viewport crops the horizontal span; a wider viewport crops the
 * vertical span. Neither axis is ever expanded, so portrait fullscreen cannot
 * reveal terrain edges that were outside the validated initial view.
 *
 * @param {number} canonicalHalfWidth
 * @param {number} canonicalHalfHeight
 * @param {number} aspect
 * @param {number} verticalStretch
 */
export function coveredOrthographicHalfExtents(
  canonicalHalfWidth,
  canonicalHalfHeight,
  aspect,
  verticalStretch,
) {
  return {
    halfWidth: Math.min(
      canonicalHalfWidth,
      canonicalHalfHeight * aspect * verticalStretch,
    ),
    halfHeight: Math.min(
      canonicalHalfHeight,
      canonicalHalfWidth / (aspect * verticalStretch),
    ),
  };
}
