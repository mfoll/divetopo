import * as THREE from "three";

type GridPoint = [number, number];
type Bounds = { left: number; right: number; top: number; bottom: number };

export function createDrapedDepthLabels(
  levels: Record<string, GridPoint[][]>,
  visibleDepths: number[],
  cellWidthM: number,
  cellDepthM: number,
  terrainWidthM: number,
  terrainDepthM: number,
  elevationAt: (x: number, z: number) => number,
  slopeAt: (point: GridPoint) => number,
) {
  const pixelsPerM = 2048 / Math.max(terrainWidthM, terrainDepthM);
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(terrainWidthM * pixelsPerM);
  canvas.height = Math.round(terrainDepthM * pixelsPerM);
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Depth label texture unavailable");
  const context = ctx;

  context.scale(canvas.width / terrainWidthM, canvas.height / terrainDepthM);
  context.textAlign = "center";
  context.textBaseline = "middle";
  context.lineJoin = "round";
  const texture = new THREE.CanvasTexture(canvas);
  texture.anisotropy = 8;
  const contours = visibleDepths.flatMap((level) => {
    const lines = levels[level] ?? [];
    const candidates = lines.flatMap((line) => line.slice(2, -2).map(([column, row], index) => {
      const [startX, startY] = line[index];
      const [endX, endY] = line[index + 4];
      return {
        x: column * cellWidthM - terrainWidthM / 2,
        z: row * cellDepthM - terrainDepthM / 2,
        angle: Math.atan2((endY - startY) * cellDepthM, (endX - startX) * cellWidthM),
        slope: slopeAt([column, row]),
      };
    })).filter(({ slope }) => Number.isFinite(slope));
    return candidates.length ? [{ level, candidates }] : [];
  }).sort((a, b) => (a.level % 10) - (b.level % 10) || a.level - b.level);

  function update(
    camera: THREE.OrthographicCamera,
    widthPx: number,
    heightPx: number,
    isVisible: (point: THREE.Vector3) => boolean,
  ) {
    camera.updateMatrixWorld();
    context.fillStyle = "#000";
    context.fillRect(0, 0, terrainWidthM, terrainDepthM);
    const occupied: Bounds[] = [];
    const placedLevels = new Set<number>();
    const worldUnitsPerPixel = (camera.right - camera.left) / (camera.zoom * widthPx);
    const project = (x: number, z: number) =>
      new THREE.Vector3(x, elevationAt(x, z), z).project(camera);
    const screenX = (x: number) => (x + 1) * widthPx / 2;
    const screenY = (y: number) => (1 - y) * heightPx / 2;

    // Fit more depths on wide views, while keeping room between labels on phones.
    const labelLimit = Math.min(contours.length, THREE.MathUtils.clamp(Math.floor(widthPx / 85), 3, 10));

    function placeLabels(fontSizePx: number, angleOffset: number, maxWarpPx: number, widthScale = 1) {
      const fontSizeM = fontSizePx * worldUnitsPerPixel;
      context.font = `650 ${fontSizeM}px system-ui, sans-serif`;
      context.lineWidth = fontSizeM * 0.16;
      for (const { level, candidates } of contours) {
        if (occupied.length >= labelLimit) break;
        if (placedLevels.has(level)) continue;
        const label = `${level} m`;
        const inkHalfWidth = context.measureText(label).width / 2 + fontSizeM * 0.22;
        const halfWidth = inkHalfWidth * widthScale;
        const halfHeight = fontSizeM * 0.66;
        const placements = [];
        for (const { x, z, angle: tangent, slope } of candidates) {
          const angle = tangent + angleOffset;
          const center = project(x, z);
          if (!Number.isFinite(center.y) || Math.abs(center.x) > 0.91 ||
              Math.abs(center.y) > 0.86 || Math.abs(center.z) > 1) continue;

          let dx = Math.cos(angle);
          let dz = Math.sin(angle);
          const right = project(x + halfWidth * dx, z + halfWidth * dz);
          const flip = right.x < center.x;
          if (flip) { dx = -dx; dz = -dz; }

          const sample = (along: number, across: number) =>
            project(x + along * dx - across * dz, z + along * dz + across * dx);
          const rightward = sample(halfWidth, 0);
          const down = sample(0, halfHeight);
          const alongX = screenX(rightward.x) - screenX(center.x);
          const alongY = screenY(rightward.y) - screenY(center.y);
          const alongLength = Math.hypot(alongX, alongY);
          const downX = screenX(down.x) - screenX(center.x);
          const downY = screenY(down.y) - screenY(center.y);
          const thickness = (downY * alongX - downX * alongY) / Math.max(alongLength, 0.01);
          if (!(thickness > 1.4)) continue;

          // Correct the local stretch and shear introduced by the camera angle.
          const stretch = THREE.MathUtils.clamp(9 / thickness, 0.22, 2.2);
          const shear = THREE.MathUtils.clamp(
            -(downX * alongX + downY * alongY) / (alongLength ** 2) * halfWidth / halfHeight,
            -2, 2,
          ) * stretch;
          const at = (along: number, across: number) =>
            sample(along + across * shear, across * stretch);
          const corners = [
            at(-halfWidth, -halfHeight), at(-halfWidth, halfHeight),
            at(halfWidth, -halfHeight), at(halfWidth, halfHeight),
          ];
          if (corners.some(({ x, y }) => !Number.isFinite(y) || Math.abs(x) > 0.96 || Math.abs(y) > 0.92)) continue;
          const [tl, bl, tr, br] = corners;
          const baselineX = screenX(br.x) - screenX(bl.x);
          const baselineY = screenY(br.y) - screenY(bl.y);
          const length = Math.hypot(baselineX, baselineY);
          const capHeight = ((screenX(bl.x) - screenX(tl.x)) * -baselineY +
            (screenY(bl.y) - screenY(tl.y)) * baselineX) / Math.max(length, 0.01);
          // Reject upside-down or foreshortened text in this camera pose.
          if (length < 17 || baselineX < length * 0.55 || capHeight < 9 || capHeight > 25) continue;

          // Check the interior, too: a ridge can stretch a single letter while the corners look fine.
          let warpPx = 0;
          const flatEnough = [0, 0.25, 0.5, 0.75, 1].every((u) =>
            [0, 0.25, 0.5, 0.75, 1].every((v) => {
              const actual = at((2 * u - 1) * halfWidth, (2 * v - 1) * halfHeight);
              const expectedY = tl.y + u * (tr.y - tl.y) + v * (bl.y - tl.y);
              warpPx = Math.max(warpPx, Math.abs(actual.y - expectedY) * heightPx / 2);
              return warpPx < maxWarpPx;
            }),
          );
          if (!flatEnough) continue;

          const xs = corners.map(({ x }) => screenX(x));
          const ys = corners.map(({ y }) => screenY(y));
          const bounds = { left: Math.min(...xs), right: Math.max(...xs), top: Math.min(...ys), bottom: Math.max(...ys) };
          if (occupied.some((other) => bounds.left < other.right + 10 &&
              bounds.right > other.left - 10 && bounds.top < other.bottom + 8 &&
              bounds.bottom > other.top - 8)) continue;
          const score = Math.min(capHeight, 22) * 1.5 + baselineX / length * 9 -
            Math.hypot(center.x, center.y) * 12 - Math.min(slope, 4) * 3 - warpPx * 6;
          placements.push({ x, z, dx, dz, angle: angle + (flip ? Math.PI : 0), bounds, score, stretch, shear });
        }

        placements.sort((a, b) => b.score - a.score);
        const best = placements.find(({ x, z, dx, dz }) =>
          [-0.7, 0, 0.7].every((fraction) => {
            const px = x + fraction * halfWidth * dx;
            const pz = z + fraction * halfWidth * dz;
            return isVisible(new THREE.Vector3(px, elevationAt(px, pz), pz));
          }),
        );
        if (!best) continue;
        context.save();
        context.translate(best.x + terrainWidthM / 2, best.z + terrainDepthM / 2);
        context.rotate(best.angle);
        context.transform(widthScale, 0, best.shear, best.stretch, 0, 0);
        // Green reserves space in the contour. Red and blue mask the ink and halo.
        context.fillStyle = "#00ff00";
        context.fillRect(-inkHalfWidth, -halfHeight, inkHalfWidth * 2, halfHeight * 2);
        context.strokeStyle = "#00ffff";
        context.strokeText(label, 0, 0);
        context.fillStyle = "#ffff00";
        context.fillText(label, 0, 0);
        context.restore();
        occupied.push(best.bounds);
        placedLevels.add(level);
      }
    }

    placeLabels(15, 0, 3);
    // Fill missing depths with shorter footprints and a slight turn on irregular slopes.
    for (const angle of [0, -Math.PI / 8, Math.PI / 8]) {
      if (occupied.length >= labelLimit) break;
      placeLabels(13, angle, 4.5);
    }
    // On steep faces, a narrower label can fit between two breaks in the slope.
    for (const angle of [0, -Math.PI / 8, Math.PI / 8, -Math.PI / 4, Math.PI / 4]) {
      if (occupied.length >= Math.min(labelLimit, 5)) break;
      placeLabels(13, angle, 4.5, 0.78);
    }
    texture.needsUpdate = true;
    return occupied.length;
  }

  return { texture, update };
}
