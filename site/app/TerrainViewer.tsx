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
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const textureCacheRef = useRef<
    Partial<Record<SurfaceStyle, THREE.Texture>>
  >({});
  const metadataRef = useRef<TerrainMetadata | null>(null);
  const initialViewRef = useRef<{
    position: THREE.Vector3;
    target: THREE.Vector3;
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
      const offsetM = metadata.grid.heightEncoding.offsetM;
      const scaleM = metadata.grid.heightEncoding.scaleMPerUnit;
      let minY = Number.POSITIVE_INFINITY;
      let maxY = Number.NEGATIVE_INFINITY;
      for (let index = 0; index < width * height; index += 1) {
        const elevationM =
          offsetM + heights.getUint16(index * 2, true) * scaleM;
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
            filterIndices(sourceIndex, new Uint8Array(maskBuffer)),
            1,
          ),
        );
      }
      geometry.computeVertexNormals();
      geometry.computeBoundingSphere();

      scene = new THREE.Scene();
      scene.background = new THREE.Color("#07151c");
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

      const camera = new THREE.PerspectiveCamera(34, 1, 0.5, 6000);
      const span = Math.max(
        metadata.physicalSizeM.width,
        metadata.physicalSizeM.depth,
      );
      const verticalCenter = (minY + maxY) / 2;
      camera.position.set(span * 0.65, span * 1.05, span * 0.72);
      cameraRef.current = camera;

      const renderer = new THREE.WebGLRenderer({
        antialias: true,
        powerPreference: "high-performance",
      });
      renderer.outputColorSpace = THREE.SRGBColorSpace;
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.75));
      mount.appendChild(renderer.domElement);
      rendererRef.current = renderer;

      const controls = new OrbitControls(camera, renderer.domElement);
      controls.target.set(0, verticalCenter * 0.32, 0);
      controls.cursor.copy(controls.target);
      controls.enableDamping = false;
      controls.screenSpacePanning = true;
      controls.minDistance = span * 0.22;
      controls.maxDistance = span * 2.4;
      controls.maxTargetRadius = span * 0.28;
      // The exported terrain is an open heightfield, not a closed solid. Keep
      // its orbit inside the useful oblique arc so the sheet cannot collapse
      // into a misleading foreground ribbon when viewed almost edge-on.
      controls.minPolarAngle = Math.PI * 0.16;
      controls.maxPolarAngle = Math.PI * 0.26;
      controls.update();
      const initialAzimuth = controls.getAzimuthalAngle();
      controls.minAzimuthAngle = initialAzimuth - Math.PI * 0.18;
      controls.maxAzimuthAngle = initialAzimuth + Math.PI * 0.18;
      controlsRef.current = controls;
      initialViewRef.current = {
        position: camera.position.clone(),
        target: controls.target.clone(),
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
        currentCamera.aspect = widthPx / heightPx;
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
        texture = await new THREE.TextureLoader().loadAsync(
          `/terrain/${slug}/${metadata.textures[nextStyle].file}`,
        );
        texture.colorSpace = THREE.SRGBColorSpace;
        texture.anisotropy = Math.min(
          rendererRef.current?.capabilities.getMaxAnisotropy() ?? 1,
          8,
        );
        textureCacheRef.current[nextStyle] = texture;
      }
      if (cancelled) return;
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
        texture = await new THREE.TextureLoader().loadAsync(
          `/terrain/${slug}/${metadata!.textures[style].file}`,
        );
        texture.colorSpace = THREE.SRGBColorSpace;
        textureCacheRef.current[style] = texture;
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
