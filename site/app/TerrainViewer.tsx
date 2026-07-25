"use client";

import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { topoReunionCopy } from "../content/copy";
import type { Language } from "../content/preferences";
import {
  bathymetryColorCss,
  bathymetryColorRgb,
} from "./bathymetryPalette.mjs";
import { coveredOrthographicHalfExtents } from "./terrainCamera.mjs";

type SurfaceStyle = "topographic" | "orthophoto";

const RELIEF_EXPOSURE = 1.55;
const ISOBATH_INTERVAL_M = 5;
const ISOBATH_SHADER_CACHE_KEY = "analytic-isobaths-v6";
const ISOBATH_COLOR_COUNT = 8;

type NumberUniform = { value: number };

type TerrainMetadata = {
  physicalSizeM: { width: number; depth: number };
  elevationRangeM: { min: number; max: number };
  orientation: {
    rotationQuarterTurnsCounterClockwise: number;
  };
  grid: {
    width: number;
    height: number;
    heightFile: string;
    heightEncoding: {
      offsetM: number;
      scaleMPerUnit: number;
    };
    validMaskFile: string;
    isobathMaskFile: string;
  };
  verticalExaggeration: number;
  view: {
    lookBearingDeg: number;
    gridLookBearingDeg: number;
    cameraTilt: number;
    alongViewProjectionScale: number;
    visibleWidthM?: number;
    coastFrameFraction?: number;
    horizontalCenterOffsetM?: number;
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

function visibleIsobathLevels(maximumDepthM: number) {
  const levels: number[] = [];
  for (
    let level = ISOBATH_INTERVAL_M;
    level < maximumDepthM - 0.001;
    level += ISOBATH_INTERVAL_M
  ) {
    levels.push(level);
  }
  return levels;
}

function updateCompassDial(
  dial: HTMLDivElement | null,
  camera: THREE.Camera,
  target: THREE.Vector3,
  rotationQuarterTurnsCounterClockwise: number,
) {
  if (!dial) return;
  const directionX = target.x - camera.position.x;
  const directionZ = target.z - camera.position.z;
  if (Math.hypot(directionX, directionZ) < 1e-6) return;
  const gridBearingDeg = THREE.MathUtils.radToDeg(
    Math.atan2(directionX, -directionZ),
  );
  const geographicBearingDeg = THREE.MathUtils.euclideanModulo(
    gridBearingDeg + 90 * rotationQuarterTurnsCounterClockwise,
    360,
  );
  dial.style.setProperty(
    "--compass-rotation",
    `${-geographicBearingDeg}deg`,
  );
  dial.style.setProperty(
    "--compass-label-rotation",
    `${geographicBearingDeg}deg`,
  );
}

function installAnalyticIsobaths(
  material: THREE.MeshStandardMaterial,
  enabledUniform: NumberUniform,
  pixelRatioUniform: NumberUniform,
  maximumDepthM: number,
) {
  material.onBeforeCompile = (shader) => {
    shader.uniforms.uIsobathsEnabled = enabledUniform;
    shader.uniforms.uIsobathPixelRatio = pixelRatioUniform;
    shader.uniforms.uIsobathIntervalM = {
      value: ISOBATH_INTERVAL_M,
    };
    shader.uniforms.uIsobathMaximumDepthM = {
      value: maximumDepthM,
    };
    shader.uniforms.uIsobathOutlineColor = {
      value: new THREE.Color("#05070a"),
    };
    shader.uniforms.uIsobathLevelColors = {
      // Use the exact bathymetric palette of the static maps. The renderer
      // applies the same linear exposure, so pre-compensate the overlay core
      // to preserve the source palette colour on screen and in the legend.
      value: Array.from({ length: ISOBATH_COLOR_COUNT }, (_, index) => {
        const [red, green, blue] = bathymetryColorRgb(
          (index + 1) * ISOBATH_INTERVAL_M,
          maximumDepthM,
        );
        return new THREE.Color()
          .setRGB(
            red / 255,
            green / 255,
            blue / 255,
            THREE.SRGBColorSpace,
          )
          .multiplyScalar(1 / RELIEF_EXPOSURE);
      }),
    };

    shader.vertexShader = shader.vertexShader
      .replace(
        "#include <common>",
        `#include <common>
attribute float terrainElevationM;
attribute float isobathSource;
varying float vTerrainElevationM;
varying float vIsobathSource;`,
      )
      .replace(
        "#include <begin_vertex>",
        `#include <begin_vertex>
vTerrainElevationM = terrainElevationM;
vIsobathSource = isobathSource;`,
      );

    shader.fragmentShader = shader.fragmentShader
      .replace(
        "#include <common>",
        `#include <common>
uniform float uIsobathsEnabled;
uniform float uIsobathIntervalM;
uniform float uIsobathMaximumDepthM;
uniform float uIsobathPixelRatio;
uniform vec3 uIsobathOutlineColor;
uniform vec3 uIsobathLevelColors[8];
varying float vTerrainElevationM;
varying float vIsobathSource;`,
      )
      .replace(
        "#include <opaque_fragment>",
        `#include <opaque_fragment>

float isobathIntervalM = max(uIsobathIntervalM, 0.001);
float isobathDepthM = -vTerrainElevationM;
float isobathLevelIndex =
  floor(isobathDepthM / isobathIntervalM + 0.5);
float isobathLevelDepthM = isobathLevelIndex * isobathIntervalM;
float isobathDistanceM =
  abs(isobathDepthM - isobathLevelDepthM);
float isobathPixelSpanM = fwidth(isobathDepthM);
float isobathDistanceCssPx =
  isobathDistanceM /
  max(isobathPixelSpanM * uIsobathPixelRatio, 0.0001);
float isobathMask = step(0.5, isobathLevelIndex);
isobathMask *=
  1.0 - step(uIsobathMaximumDepthM - 0.001, isobathLevelDepthM);
isobathMask *= step(0.000001, isobathPixelSpanM);
isobathMask *= step(0.999, vIsobathSource);
isobathMask *= uIsobathsEnabled;

float isobathOutlineCoverage =
  1.0 - smoothstep(1.35, 1.75, isobathDistanceCssPx);
float isobathCenterCoverage =
  1.0 - smoothstep(0.3, 0.82, isobathDistanceCssPx);
isobathOutlineCoverage *= isobathMask;
isobathCenterCoverage *= isobathMask;

vec3 isobathCenterColor = uIsobathLevelColors[0];
if (isobathLevelIndex > 1.5) isobathCenterColor = uIsobathLevelColors[1];
if (isobathLevelIndex > 2.5) isobathCenterColor = uIsobathLevelColors[2];
if (isobathLevelIndex > 3.5) isobathCenterColor = uIsobathLevelColors[3];
if (isobathLevelIndex > 4.5) isobathCenterColor = uIsobathLevelColors[4];
if (isobathLevelIndex > 5.5) isobathCenterColor = uIsobathLevelColors[5];
if (isobathLevelIndex > 6.5) isobathCenterColor = uIsobathLevelColors[6];
if (isobathLevelIndex > 7.5) isobathCenterColor = uIsobathLevelColors[7];

gl_FragColor.rgb = mix(
  gl_FragColor.rgb,
  uIsobathOutlineColor,
  isobathOutlineCoverage * 0.96
);
gl_FragColor.rgb = mix(
  gl_FragColor.rgb,
  isobathCenterColor,
  isobathCenterCoverage * 0.97
);`,
      );
  };
  material.customProgramCacheKey = () => ISOBATH_SHADER_CACHE_KEY;
}

export default function TerrainViewer({
  slug,
  siteName,
  style,
  language,
}: {
  slug: string;
  siteName: string;
  style: SurfaceStyle;
  language: Language;
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
  const compassDialRef = useRef<HTMLDivElement>(null);
  const isobathsEnabledUniformRef = useRef<NumberUniform>({ value: 1 });
  const styleRef = useRef(style);
  const [isobathsEnabled, setIsobathsEnabled] = useState(true);
  const [isNativeFullscreen, setIsNativeFullscreen] = useState(false);
  const [isCssFullscreen, setIsCssFullscreen] = useState(false);
  const [maximumDepthM, setMaximumDepthM] = useState(0);
  const [status, setStatus] = useState<"loading" | "ready" | "error">(
    "loading",
  );

  useEffect(() => {
    const syncFullscreenState = () => {
      const hostIsFullscreen =
        document.fullscreenElement === hostRef.current;
      setIsNativeFullscreen(hostIsFullscreen);
      if (hostIsFullscreen) {
        setIsCssFullscreen(false);
      }
    };
    document.addEventListener("fullscreenchange", syncFullscreenState);
    return () => {
      document.removeEventListener("fullscreenchange", syncFullscreenState);
    };
  }, []);

  useEffect(() => {
    if (!isCssFullscreen) {
      return;
    }

    const body = document.body;
    const root = document.documentElement;
    const viewerFrame = hostRef.current?.closest(".viewer-frame");
    const scrollX = window.scrollX;
    const scrollY = window.scrollY;
    const previousBodyStyles = {
      overflow: body.style.overflow,
      overscrollBehavior: body.style.overscrollBehavior,
      position: body.style.position,
      top: body.style.top,
      left: body.style.left,
      right: body.style.right,
      width: body.style.width,
    };
    const previousRootStyles = {
      overflow: root.style.overflow,
      overscrollBehavior: root.style.overscrollBehavior,
    };

    body.style.overflow = "hidden";
    body.style.overscrollBehavior = "none";
    body.style.position = "fixed";
    body.style.top = `-${scrollY}px`;
    body.style.left = "0";
    body.style.right = "0";
    body.style.width = "100%";
    root.style.overflow = "hidden";
    root.style.overscrollBehavior = "none";
    viewerFrame?.classList.add("has-css-fullscreen");

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsCssFullscreen(false);
      }
    }

    window.addEventListener("keydown", handleKeyDown);

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      viewerFrame?.classList.remove("has-css-fullscreen");
      Object.assign(body.style, previousBodyStyles);
      Object.assign(root.style, previousRootStyles);
      window.scrollTo(scrollX, scrollY);
    };
  }, [isCssFullscreen]);

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
      const [heightBuffer, maskBuffer, isobathMaskBuffer] = await Promise.all([
        fetch(`${base}/${metadata.grid.heightFile}`).then((response) => {
          if (!response.ok) throw new Error("Heightfield unavailable");
          return response.arrayBuffer();
        }),
        fetch(`${base}/${metadata.grid.validMaskFile}`).then((response) => {
          if (!response.ok) throw new Error("Terrain mask unavailable");
          return response.arrayBuffer();
        }),
        fetch(`${base}/${metadata.grid.isobathMaskFile}`).then((response) => {
          if (!response.ok) throw new Error("Isobath mask unavailable");
          return response.arrayBuffer();
        }),
      ]);
      if (cancelled || !hostRef.current) return;

      metadataRef.current = metadata;
      const maximumDepthM = Math.max(-metadata.elevationRangeM.min, 0);
      setMaximumDepthM(maximumDepthM);
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
      const isobathMask = new Uint8Array(isobathMaskBuffer);
      const elevations = new Float32Array(width * height);
      const isobathSource = new Float32Array(width * height);
      const offsetM = metadata.grid.heightEncoding.offsetM;
      const scaleM = metadata.grid.heightEncoding.scaleMPerUnit;
      let minY = Number.POSITIVE_INFINITY;
      let maxY = Number.NEGATIVE_INFINITY;
      for (let index = 0; index < width * height; index += 1) {
        const elevationM =
          offsetM + heights.getUint16(index * 2, true) * scaleM;
        elevations[index] = elevationM;
        isobathSource[index] = validAt(isobathMask, index);
        const y = elevationM * metadata.verticalExaggeration;
        positions.setY(index, y);
        minY = Math.min(minY, y);
        maxY = Math.max(maxY, y);
      }
      positions.needsUpdate = true;
      geometry.setAttribute(
        "terrainElevationM",
        new THREE.BufferAttribute(elevations, 1),
      );
      geometry.setAttribute(
        "isobathSource",
        new THREE.BufferAttribute(isobathSource, 1),
      );

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
      const pixelRatioUniform: NumberUniform = {
        value: Math.min(window.devicePixelRatio, 1.75),
      };
      installAnalyticIsobaths(
        material,
        isobathsEnabledUniformRef.current,
        pixelRatioUniform,
        maximumDepthM,
      );
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
      const screenRight = new THREE.Vector3(
        Math.cos(viewBearing),
        0,
        Math.sin(viewBearing),
      );
      if (metadata.view.horizontalCenterOffsetM !== undefined) {
        shore.addScaledVector(
          screenRight,
          metadata.view.horizontalCenterOffsetM - shore.dot(screenRight),
        );
      }
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
      // Match the static relief pipeline: apply exposure in linear light
      // before the final sRGB conversion instead of brightening the canvas.
      renderer.toneMapping = THREE.LinearToneMapping;
      renderer.toneMappingExposure = RELIEF_EXPOSURE;
      renderer.setPixelRatio(pixelRatioUniform.value);
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
          updateCompassDial(
            compassDialRef.current,
            cameraRef.current,
            controls.target,
            metadata.orientation.rotationQuarterTurnsCounterClockwise,
          );
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
        const pixelRatio = Math.min(window.devicePixelRatio, 1.75);
        if (currentRenderer.getPixelRatio() !== pixelRatio) {
          currentRenderer.setPixelRatio(pixelRatio);
          pixelRatioUniform.value = pixelRatio;
        }
        const widthPx = Math.max(currentHost.clientWidth, 1);
        const heightPx = Math.max(currentHost.clientHeight, 1);
        if (widthPx === lastWidth && heightPx === lastHeight) return;
        lastWidth = widthPx;
        lastHeight = heightPx;
        currentRenderer.setSize(widthPx, heightPx, false);
        const aspect = widthPx / heightPx;
        const resized = coveredOrthographicHalfExtents(
          halfWidth,
          halfHeight,
          aspect,
          verticalStretch,
        );
        currentCamera.left = -resized.halfWidth;
        currentCamera.right = resized.halfWidth;
        currentCamera.top = resized.halfHeight;
        currentCamera.bottom = -resized.halfHeight;
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

  function renderCurrentScene() {
    const renderer = rendererRef.current;
    const camera = cameraRef.current;
    const scene = sceneRef.current;
    if (renderer && camera && scene) renderer.render(scene, camera);
  }

  function toggleIsobaths() {
    const nextValue = !isobathsEnabled;
    isobathsEnabledUniformRef.current.value = nextValue ? 1 : 0;
    setIsobathsEnabled(nextValue);
    renderCurrentScene();
  }

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

    if (isCssFullscreen) {
      setIsCssFullscreen(false);
      return;
    }

    if (document.fullscreenElement) {
      await document.exitFullscreen();
      return;
    }

    if (typeof host.requestFullscreen === "function") {
      try {
        await host.requestFullscreen();
        if (document.fullscreenElement === host) {
          return;
        }
      } catch {
        // iOS Safari may expose fullscreen-related APIs without supporting
        // arbitrary elements. The CSS fallback below preserves the control.
      }
    }

    setIsCssFullscreen(true);
  }

  const isobathLevels = visibleIsobathLevels(maximumDepthM);
  const text = topoReunionCopy[language].terrain;
  const isFullscreen = isNativeFullscreen || isCssFullscreen;

  return (
    <div
      className={`terrain-host${isCssFullscreen ? " is-css-fullscreen" : ""}`}
      ref={hostRef}
      role="region"
      aria-label={`${text.interactiveTerrain} ${siteName}`}
    >
      {status !== "ready" ? (
        <div className="terrain-status" role="status">
          {status === "error"
            ? text.unavailable
            : text.loading}
        </div>
      ) : null}
      <div
        className={`terrain-compass${status === "ready" ? " is-visible" : ""}`}
        data-testid="terrain-compass"
        role="img"
        aria-label={text.orientation}
      >
        <div className="terrain-compass-dial" ref={compassDialRef}>
          <span
            className="terrain-compass-axis is-north-south"
            aria-hidden="true"
          />
          <span
            className="terrain-compass-axis is-east-west"
            aria-hidden="true"
          />
          <span className="terrain-compass-north-tip" aria-hidden="true" />
          <span className="terrain-cardinal is-north">
            <span>N</span>
          </span>
          <span className="terrain-cardinal is-east">
            <span>E</span>
          </span>
          <span className="terrain-cardinal is-south">
            <span>S</span>
          </span>
          <span className="terrain-cardinal is-west">
            <span>{text.westCardinal}</span>
          </span>
        </div>
      </div>
      {status === "ready" &&
      isobathsEnabled &&
      isobathLevels.length > 0 ? (
        <div
          className="terrain-depth-legend"
          data-testid="terrain-depth-legend"
          role="group"
          aria-label={`${text.isobathLegend} ${ISOBATH_INTERVAL_M} m`}
        >
          <ul>
            {isobathLevels.map((level) => (
              <li key={level}>
                <span
                  className="terrain-isobath-swatch"
                  style={{
                    backgroundColor: bathymetryColorCss(
                      level,
                      maximumDepthM,
                    ),
                  }}
                  aria-hidden="true"
                />
                <span>−{level} m</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      <div className="terrain-actions">
        <button
          type="button"
          className="terrain-icon-button"
          aria-pressed={isobathsEnabled}
          aria-label={
            isobathsEnabled
              ? text.hideIsobaths
              : text.showIsobaths
          }
          title={
            isobathsEnabled
              ? text.hideIsobathsShort
              : text.showIsobathsShort
          }
          data-testid="isobath-toggle"
          onClick={toggleIsobaths}
        >
          <span
            className="terrain-action-icon is-isobaths"
            aria-hidden="true"
          />
        </button>
        <button
          type="button"
          className="terrain-icon-button"
          aria-label={text.resetView}
          title={text.resetView}
          onClick={resetView}
        >
          <span
            className="terrain-action-icon is-reset"
            aria-hidden="true"
          />
        </button>
        <button
          type="button"
          className="terrain-icon-button"
          aria-pressed={isFullscreen}
          aria-label={
            isFullscreen ? text.exitFullscreen : text.enterFullscreen
          }
          title={
            isFullscreen ? text.exitFullscreen : text.enterFullscreen
          }
          onClick={toggleFullscreen}
        >
          <span
            className="terrain-action-icon is-fullscreen"
            aria-hidden="true"
          />
        </button>
      </div>
    </div>
  );
}
