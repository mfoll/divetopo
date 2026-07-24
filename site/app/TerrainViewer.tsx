"use client";

import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

type SurfaceStyle = "topographic" | "orthophoto";

type TerrainMetadata = {
  physicalSizeM: { width: number; depth: number };
  grid: {
    width: number;
    height: number;
    heightFile: string;
    heightEncoding: {
      offsetM: number;
      scaleMPerUnit: number;
    };
    validMaskFile: string;
  };
  verticalExaggeration: number;
  view: {
    lookBearingDeg: number;
    gridLookBearingDeg: number;
    cameraTilt: number;
    alongViewProjectionScale: number;
    visibleWidthM?: number;
    coastFrameFraction?: number;
  };
  textures: {
    topographic: { file: string };
    orthophoto: { file: string };
  };
};

function validAt(mask: Uint8Array, index: number) {
  return (mask[index >> 3] >> (index & 7)) & 1;
}

function filterIndices(
  source: THREE.BufferAttribute,
  mask: Uint8Array,
): Uint32Array {
  const retained: number[] = [];
  for (let offset = 0; offset < source.count; offset += 3) {
    const a = source.getX(offset);
    const b = source.getX(offset + 1);
    const c = source.getX(offset + 2);
    if (validAt(mask, a) && validAt(mask, b) && validAt(mask, c)) {
      retained.push(a, b, c);
    }
  }
  return new Uint32Array(retained);
}

function median(values: number[]) {
  if (!values.length) return 0;
  values.sort((a, b) => a - b);
  const middle = Math.floor(values.length / 2);
  return values.length % 2
    ? values[middle]
    : (values[middle - 1] + values[middle]) / 2;
}

export default function TerrainViewer({
  slug,
  siteName,
  style,
}: {
  slug: string;
  siteName: string;
  style: SurfaceStyle;
}) {
  const hostRef = useRef<HTMLDivElement>(null);
  const materialRef = useRef<THREE.MeshStandardMaterial | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const cameraRef = useRef<THREE.OrthographicCamera | null>(null);
  const textureCacheRef = useRef<
    Partial<Record<SurfaceStyle, THREE.Texture>>
  >({});
  const metadataRef = useRef<TerrainMetadata | null>(null);
  const initialViewRef = useRef<{
    position: THREE.Vector3;
    target: THREE.Vector3;
    zoom: number;
  } | null>(null);
  const styleRef = useRef(style);
  const [status, setStatus] = useState<"loading" | "ready" | "error">(
    "loading",
  );

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    const mount: HTMLDivElement = host;

    let cancelled = false;
    let resizeObserver: ResizeObserver | null = null;
    let resizeFrame = 0;
    let lastWidth = 0;
    let lastHeight = 0;
    let scene: THREE.Scene | null = null;
    let geometry: THREE.BufferGeometry | null = null;
    let mesh: THREE.Mesh | null = null;

    async function initialise() {
      setStatus("loading");
      const base = `/terrain/${slug}`;
      const metadataResponse = await fetch(`${base}/terrain.json`);
      if (!metadataResponse.ok) {
        throw new Error(`Terrain metadata unavailable for ${slug}`);
      }
      const metadata = (await metadataResponse.json()) as TerrainMetadata;
      const [heightBuffer, maskBuffer] = await Promise.all([
        fetch(`${base}/${metadata.grid.heightFile}`).then((response) => {
          if (!response.ok) throw new Error("Heightfield unavailable");
          return response.arrayBuffer();
        }),
        fetch(`${base}/${metadata.grid.validMaskFile}`).then((response) => {
          if (!response.ok) throw new Error("Terrain mask unavailable");
          return response.arrayBuffer();
        }),
      ]);
      if (cancelled || !hostRef.current) return;

      metadataRef.current = metadata;
      const width = metadata.grid.width;
      const height = metadata.grid.height;
      geometry = new THREE.PlaneGeometry(
        metadata.physicalSizeM.width,
        metadata.physicalSizeM.depth,
        width - 1,
        height - 1,
      );
      geometry.rotateX(-Math.PI / 2);

      const positions = geometry.getAttribute("position");
      const heights = new DataView(heightBuffer);
      const mask = new Uint8Array(maskBuffer);
      const elevations = new Float32Array(width * height);
      const offsetM = metadata.grid.heightEncoding.offsetM;
      const scaleM = metadata.grid.heightEncoding.scaleMPerUnit;
      let minY = Number.POSITIVE_INFINITY;
      let maxY = Number.NEGATIVE_INFINITY;
      for (let index = 0; index < width * height; index += 1) {
        const elevationM =
          offsetM + heights.getUint16(index * 2, true) * scaleM;
        elevations[index] = elevationM;
        const y = elevationM * metadata.verticalExaggeration;
        positions.setY(index, y);
        minY = Math.min(minY, y);
        maxY = Math.max(maxY, y);
      }
      positions.needsUpdate = true;

      const sourceIndex = geometry.getIndex();
      if (sourceIndex) {
        geometry.setIndex(
          new THREE.BufferAttribute(
            filterIndices(sourceIndex, mask),
            1,
          ),
        );
      }
      geometry.computeVertexNormals();
      geometry.computeBoundingSphere();

      scene = new THREE.Scene();
      sceneRef.current = scene;

      const material = new THREE.MeshStandardMaterial({
        color: "#d8e0d5",
        roughness: 0.82,
        metalness: 0,
      });
      materialRef.current = material;
      mesh = new THREE.Mesh(geometry, material);
      scene.add(mesh);

      const hemisphere = new THREE.HemisphereLight("#dffbff", "#10262d", 1.7);
      scene.add(hemisphere);
      const keyLight = new THREE.DirectionalLight("#fff2d8", 2.1);
      keyLight.position.set(
        metadata.physicalSizeM.width * 0.35,
        Math.max(maxY * 1.6, 120),
        metadata.physicalSizeM.depth * 0.4,
      );
      scene.add(keyLight);

      const span = Math.max(
        metadata.physicalSizeM.width,
        metadata.physicalSizeM.depth,
      );
      const verticalCenter = (minY + maxY) / 2;
      const viewBearing = THREE.MathUtils.degToRad(
        metadata.view.gridLookBearingDeg,
      );
      const projectionSlope =
        metadata.view.cameraTilt *
        metadata.view.alongViewProjectionScale;
      const cameraElevation = Math.atan(projectionSlope);
      const verticalStretch = Math.sqrt(1 + projectionSlope ** 2);
      const visibleWidth = Math.min(
        metadata.view.visibleWidthM ?? metadata.physicalSizeM.width,
        span * 1.1,
      );
      const initialAspect =
        Math.max(mount.clientWidth, 1) / Math.max(mount.clientHeight, 1);
      const halfWidth = visibleWidth / 2;
      const halfHeight = halfWidth / (initialAspect * verticalStretch);

      const shoreXs: number[] = [];
      const shoreZs: number[] = [];
      const recordCrossing = (first: number, second: number) => {
        if (!validAt(mask, first) || !validAt(mask, second)) return;
        const firstElevation = elevations[first];
        const secondElevation = elevations[second];
        if (
          (firstElevation < 0 && secondElevation >= 0) ||
          (secondElevation < 0 && firstElevation >= 0)
        ) {
          const denominator =
            Math.abs(firstElevation) + Math.abs(secondElevation);
          const mix =
            denominator > 1e-6
              ? Math.abs(firstElevation) / denominator
              : 0.5;
          shoreXs.push(
            THREE.MathUtils.lerp(
              positions.getX(first),
              positions.getX(second),
              mix,
            ),
          );
          shoreZs.push(
            THREE.MathUtils.lerp(
              positions.getZ(first),
              positions.getZ(second),
              mix,
            ),
          );
        }
      };
      for (let row = 0; row < height; row += 1) {
        for (let column = 0; column < width; column += 1) {
          const index = row * width + column;
          if (column + 1 < width) recordCrossing(index, index + 1);
          if (row + 1 < height) recordCrossing(index, index + width);
        }
      }

      const shore = new THREE.Vector3(
        shoreXs.length ? median(shoreXs) : 0,
        0,
        shoreZs.length ? median(shoreZs) : 0,
      );
      const horizontalForward = new THREE.Vector3(
        Math.sin(viewBearing),
        0,
        -Math.cos(viewBearing),
      );
      const screenUp = new THREE.Vector3(
        Math.sin(cameraElevation) * horizontalForward.x,
        Math.cos(cameraElevation),
        Math.sin(cameraElevation) * horizontalForward.z,
      );
      const coastFrame = THREE.MathUtils.clamp(
        metadata.view.coastFrameFraction ?? 0.42,
        0.05,
        0.55,
      );
      const target = shore
        .clone()
        .addScaledVector(screenUp, -(0.5 - coastFrame) * halfHeight * 2);
      if (!shoreXs.length) target.y = verticalCenter * 0.25;

      const camera = new THREE.OrthographicCamera(
        -halfWidth,
        halfWidth,
        halfHeight,
        -halfHeight,
        0.5,
        span * 12,
      );
      const offshoreDistance = span * 2.2;
      camera.position
        .copy(target)
        .addScaledVector(horizontalForward, -offshoreDistance)
        .add(new THREE.Vector3(0, offshoreDistance * projectionSlope, 0));
      camera.lookAt(target);
      camera.updateProjectionMatrix();
      cameraRef.current = camera;

      const renderer = new THREE.WebGLRenderer({
        antialias: true,
        alpha: true,
        powerPreference: "high-performance",
      });
      renderer.outputColorSpace = THREE.SRGBColorSpace;
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.75));
      mount.appendChild(renderer.domElement);
      rendererRef.current = renderer;

      const controls = new OrbitControls(camera, renderer.domElement);
      controls.target.copy(target);
      controls.cursor.copy(controls.target);
      controls.enableDamping = false;
      controls.screenSpacePanning = true;
      controls.minZoom = 0.65;
      controls.maxZoom = 8;
      controls.zoomToCursor = true;
      controls.maxTargetRadius = span * 0.5;
      // Match the printable 3D perspective: start offshore and face the reef.
      // Keep only the under-surface angles out of reach; horizontal rotation
      // remains completely free.
      controls.minPolarAngle = Math.PI * 0.12;
      controls.maxPolarAngle = Math.PI * 0.42;
      controls.update();
      controlsRef.current = controls;
      initialViewRef.current = {
        position: camera.position.clone(),
        target: controls.target.clone(),
        zoom: camera.zoom,
      };

      const render = () => {
        if (scene && rendererRef.current && cameraRef.current) {
          rendererRef.current.render(scene, cameraRef.current);
        }
      };
      controls.addEventListener("change", render);

      const resize = () => {
        resizeFrame = 0;
        const currentHost = hostRef.current;
        const currentRenderer = rendererRef.current;
        const currentCamera = cameraRef.current;
        if (!currentHost || !currentRenderer || !currentCamera) return;
        const widthPx = Math.max(currentHost.clientWidth, 1);
        const heightPx = Math.max(currentHost.clientHeight, 1);
        if (widthPx === lastWidth && heightPx === lastHeight) return;
        lastWidth = widthPx;
        lastHeight = heightPx;
        currentRenderer.setSize(widthPx, heightPx, false);
        const aspect = widthPx / heightPx;
        const resizedHalfHeight =
          halfWidth / (aspect * verticalStretch);
        currentCamera.left = -halfWidth;
        currentCamera.right = halfWidth;
        currentCamera.top = resizedHalfHeight;
        currentCamera.bottom = -resizedHalfHeight;
        currentCamera.updateProjectionMatrix();
        render();
      };
      resizeObserver = new ResizeObserver(() => {
        if (resizeFrame) cancelAnimationFrame(resizeFrame);
        resizeFrame = requestAnimationFrame(resize);
      });
      resizeObserver.observe(mount);

      await setTexture(styleRef.current);
      render();
      if (!cancelled) setStatus("ready");
    }

    async function setTexture(nextStyle: SurfaceStyle) {
      const metadata = metadataRef.current;
      const material = materialRef.current;
      if (!metadata || !material) return;
      let texture = textureCacheRef.current[nextStyle];
      if (!texture) {
        const loadedTexture = await new THREE.TextureLoader().loadAsync(
          `/terrain/${slug}/${metadata.textures[nextStyle].file}`,
        );
        if (cancelled || !rendererRef.current || !materialRef.current) {
          loadedTexture.dispose();
          return;
        }
        loadedTexture.colorSpace = THREE.SRGBColorSpace;
        loadedTexture.anisotropy = Math.min(
          rendererRef.current?.capabilities.getMaxAnisotropy() ?? 1,
          8,
        );
        textureCacheRef.current[nextStyle] = loadedTexture;
        texture = loadedTexture;
      }
      if (cancelled || !materialRef.current) return;
      material.map = texture;
      material.needsUpdate = true;
    }

    initialise().catch(() => {
      if (!cancelled) setStatus("error");
    });

    return () => {
      cancelled = true;
      resizeObserver?.disconnect();
      if (resizeFrame) cancelAnimationFrame(resizeFrame);
      controlsRef.current?.dispose();
      rendererRef.current?.dispose();
      geometry?.dispose();
      materialRef.current?.dispose();
      Object.values(textureCacheRef.current).forEach((texture) =>
        texture?.dispose(),
      );
      textureCacheRef.current = {};
      rendererRef.current?.domElement.remove();
      rendererRef.current = null;
      sceneRef.current = null;
      controlsRef.current = null;
      cameraRef.current = null;
      materialRef.current = null;
      metadataRef.current = null;
      mesh = null;
      scene = null;
    };
  }, [slug]);

  useEffect(() => {
    styleRef.current = style;
    const metadata = metadataRef.current;
    const material = materialRef.current;
    if (!metadata || !material) return;
    let cancelled = false;

    async function updateTexture() {
      let texture = textureCacheRef.current[style];
      if (!texture) {
        const loadedTexture = await new THREE.TextureLoader().loadAsync(
          `/terrain/${slug}/${metadata!.textures[style].file}`,
        );
        if (cancelled || !materialRef.current || !rendererRef.current) {
          loadedTexture.dispose();
          return;
        }
        loadedTexture.colorSpace = THREE.SRGBColorSpace;
        loadedTexture.anisotropy = Math.min(
          rendererRef.current.capabilities.getMaxAnisotropy(),
          8,
        );
        textureCacheRef.current[style] = loadedTexture;
        texture = loadedTexture;
      }
      if (cancelled || !materialRef.current) return;
      materialRef.current.map = texture;
      materialRef.current.needsUpdate = true;
      const renderer = rendererRef.current;
      const camera = cameraRef.current;
      const controls = controlsRef.current;
      const scene = sceneRef.current;
      if (renderer && camera && controls && scene) {
        controls.update();
        renderer.render(scene, camera);
      }
    }

    updateTexture().catch(() => setStatus("error"));
    return () => {
      cancelled = true;
    };
  }, [slug, style]);

  function resetView() {
    const initial = initialViewRef.current;
    const camera = cameraRef.current;
    const controls = controlsRef.current;
    const renderer = rendererRef.current;
    if (!initial || !camera || !controls || !renderer) return;
    camera.position.copy(initial.position);
    camera.zoom = initial.zoom;
    camera.updateProjectionMatrix();
    controls.target.copy(initial.target);
    controls.update();
  }

  async function toggleFullscreen() {
    const host = hostRef.current;
    if (!host) return;
    if (document.fullscreenElement) {
      await document.exitFullscreen();
    } else {
      await host.requestFullscreen();
    }
  }

  return (
    <div
      className="terrain-host"
      ref={hostRef}
      aria-label={`Relief 3D interactif de ${siteName}`}
    >
      {status !== "ready" ? (
        <div className="terrain-status" role="status">
          {status === "error"
            ? "Le relief interactif n’est pas disponible sur cet appareil."
            : "Chargement du relief…"}
        </div>
      ) : null}
      <div className="terrain-actions">
        <button type="button" onClick={resetView}>
          Réinitialiser la vue
        </button>
        <button type="button" onClick={toggleFullscreen}>
          Plein écran
        </button>
      </div>
    </div>
  );
}
