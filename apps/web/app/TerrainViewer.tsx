"use client";

import { useEffect, useLayoutEffect, useRef, useState } from "react";
import * as THREE from "three";
import WebGL from "three/examples/jsm/capabilities/WebGL.js";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { Line2 } from "three/examples/jsm/lines/Line2.js";
import { LineGeometry } from "three/examples/jsm/lines/LineGeometry.js";
import { LineMaterial } from "three/examples/jsm/lines/LineMaterial.js";
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
const VECTOR_ISOBATH_OUTLINE = 0xf5efd2;
const VECTOR_ISOBATH_CENTER = 0x05070a;
const VECTOR_ISOBATH_DEPTH_BIAS = 0.0002;
const LABEL_WIDTH_CSS_PX = 68;
const LABEL_HEIGHT_CSS_PX = 28;

type NumberUniform = { value: number };

type CameraCalibrationOrigin = {
  horizontalOffset: THREE.Vector3;
  panOriginTarget: THREE.Vector3;
};

type CameraCalibrationSnapshot = {
  schema: "divetopo-camera-calibration-v1";
  slug: string;
  siteName: string;
  capturedAt: string;
  interactiveInitialView: {
    zoom: number;
    orbitAzimuthDeg: number;
    cameraElevationDeg: number;
    panRightM: number;
    panUpM: number;
    centerOffsetEastM: number;
    centerOffsetSouthM: number;
    isobathLabelFocusXNdc?: number;
  };
  diagnostic: {
    cameraPosition: { x: number; y: number; z: number };
    target: { x: number; y: number; z: number };
    panResidualForwardM: number;
  };
};

function rounded(value: number, digits = 4) {
  return Number(value.toFixed(digits));
}

function normalisedAngleDeg(value: number) {
  return ((value + 180) % 360 + 360) % 360 - 180;
}

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
    alongCenterOffsetM?: number;
    vectorLabelVerticalInsetFraction?: number;
    vectorLabelCollisionPaddingNdc?: number;
    reselectVectorLabelsOnCameraEnd?: boolean;
    requiredVectorLabelLevelsM?: number[];
    featuredVectorLabelLevelsM?: number[];
  };
  textures: {
    topographic: { file: string; attribution: string };
    orthophoto: { file: string; attribution: string };
  };
  credits: {
    copyright: string;
    license: string;
    requiredDisplay: string;
  };
};

type VectorIsobaths = {
  coordinateSpace: "grid-pixels";
  levels: Record<string, Array<Array<[number, number]>>>;
};

type VectorLabelCandidate = {
  levelM: number;
  polylineKey: string;
  point: THREE.Vector3;
  tangent: THREE.Vector3;
  reliefSlope: number;
  sourceScore: number;
};

type VectorLabel = {
  levelM: number;
  candidatePolylineKey: string | null;
  sprite: THREE.Sprite;
  texture: THREE.CanvasTexture;
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

function installFragmentDepthBias(
  material: THREE.Material,
  depthBias: number,
) {
  material.onBeforeCompile = (shader) => {
    shader.fragmentShader = shader.fragmentShader.replace(
      "void main() {",
      `void main() {
gl_FragDepth = max(gl_FragCoord.z - ${depthBias.toFixed(6)}, 0.0);`,
    );
  };
  material.customProgramCacheKey = () =>
    `fragment-depth-bias-${depthBias.toFixed(6)}`;
}

function createDepthLabelTexture(levelM: number) {
  const scale = 3;
  const canvas = document.createElement("canvas");
  canvas.width = LABEL_WIDTH_CSS_PX * scale;
  canvas.height = LABEL_HEIGHT_CSS_PX * scale;
  const context = canvas.getContext("2d");
  if (!context) {
    throw new Error("Canvas 2D unavailable for isobath labels");
  }

  context.scale(scale, scale);
  context.font =
    "700 20px Arial, Helvetica, sans-serif";
  context.textAlign = "center";
  context.textBaseline = "middle";
  context.lineJoin = "round";
  context.lineWidth = 3.3;
  context.strokeStyle = "#f5efd2";
  context.fillStyle = "#05070a";
  const label = `−${levelM} m`;
  context.strokeText(
    label,
    LABEL_WIDTH_CSS_PX / 2,
    LABEL_HEIGHT_CSS_PX / 2 + 0.5,
  );
  context.fillText(
    label,
    LABEL_WIDTH_CSS_PX / 2,
    LABEL_HEIGHT_CSS_PX / 2 + 0.5,
  );

  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.minFilter = THREE.LinearFilter;
  texture.magFilter = THREE.LinearFilter;
  texture.generateMipmaps = false;
  texture.needsUpdate = true;
  return texture;
}

function niceScaleDistance(targetM: number) {
  if (!Number.isFinite(targetM) || targetM <= 0) return 1;
  const magnitude = 10 ** Math.floor(Math.log10(targetM));
  return [1, 2, 5, 10]
    .map((factor) => factor * magnitude)
    .reduce((best, candidate) =>
      Math.abs(Math.log(candidate / targetM)) <
      Math.abs(Math.log(best / targetM))
        ? candidate
        : best,
    );
}

function updateTerrainScale(
  scale: HTMLDivElement | null,
  label: HTMLSpanElement | null,
  camera: THREE.OrthographicCamera,
  host: HTMLDivElement,
) {
  if (!scale || !label) return;
  const worldUnitsPerCssPixel =
    (camera.right - camera.left) /
    (Math.max(host.clientWidth, 1) * camera.zoom);
  const targetWidthPx = THREE.MathUtils.clamp(
    host.clientWidth * 0.11,
    72,
    112,
  );
  const distanceM = niceScaleDistance(
    worldUnitsPerCssPixel * targetWidthPx,
  );
  const widthPx = distanceM / worldUnitsPerCssPixel;
  scale.style.setProperty("--terrain-scale-width", `${widthPx}px`);
  label.textContent =
    distanceM >= 1000
      ? `${distanceM / 1000} km`
      : `${distanceM} m`;
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
  vectorIsobathsPath,
  initialZoom = 1,
  initialOrbitAzimuthDeg = 0,
  initialCameraElevationDeg,
  initialPanRightM = 0,
  initialPanUpM = 0,
  initialCenterOffsetEastM = 0,
  initialCenterOffsetSouthM = 0,
  isobathLabelFocusXNdc,
  onReady,
  onError,
  onContextRestored,
  downloadHref,
  downloadFilename,
  downloadLabel,
  compactAttributions,
}: {
  slug: string;
  siteName: string;
  style: SurfaceStyle;
  language: Language;
  vectorIsobathsPath?: string;
  initialZoom?: number;
  initialOrbitAzimuthDeg?: number;
  initialCameraElevationDeg?: number;
  initialPanRightM?: number;
  initialPanUpM?: number;
  initialCenterOffsetEastM?: number;
  initialCenterOffsetSouthM?: number;
  isobathLabelFocusXNdc?: number;
  onReady?: () => void;
  onError?: () => void;
  onContextRestored?: () => void;
  downloadHref?: string;
  downloadFilename?: string;
  downloadLabel?: string;
  compactAttributions?: Record<SurfaceStyle, string>;
}) {
  const hostRef = useRef<HTMLDivElement>(null);
  const materialRef = useRef<THREE.MeshStandardMaterial | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const cameraRef = useRef<THREE.OrthographicCamera | null>(null);
  const vectorIsobathGroupRef = useRef<THREE.Group | null>(null);
  const textureCacheRef = useRef<
    Partial<Record<SurfaceStyle, THREE.Texture>>
  >({});
  const metadataRef = useRef<TerrainMetadata | null>(null);
  const initialViewRef = useRef<{
    position: THREE.Vector3;
    target: THREE.Vector3;
    zoom: number;
  } | null>(null);
  const cameraCalibrationOriginRef =
    useRef<CameraCalibrationOrigin | null>(null);
  const compassDialRef = useRef<HTMLDivElement>(null);
  const scaleBarRef = useRef<HTMLDivElement>(null);
  const scaleLabelRef = useRef<HTMLSpanElement>(null);
  const isobathsEnabledUniformRef = useRef<NumberUniform>({ value: 1 });
  const isobathsEnabledRef = useRef(true);
  const styleRef = useRef(style);
  const [isobathsEnabled, setIsobathsEnabled] = useState(true);
  const [isNativeFullscreen, setIsNativeFullscreen] = useState(false);
  const [isCssFullscreen, setIsCssFullscreen] = useState(false);
  const [maximumDepthM, setMaximumDepthM] = useState(0);
  const [usesVectorIsobaths, setUsesVectorIsobaths] = useState(false);
  const [terrainAttribution, setTerrainAttribution] = useState<{
    copyright: string;
    requiredDisplay: string;
    sources: Record<SurfaceStyle, string>;
  } | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">(
    "loading",
  );
  const [cameraCalibrationEnabled, setCameraCalibrationEnabled] =
    useState(false);
  const [cameraCalibrationMessage, setCameraCalibrationMessage] =
    useState("");

  useEffect(() => {
    const isLocal =
      window.location.hostname === "localhost" ||
      window.location.hostname === "127.0.0.1";
    if (!isLocal) return;
    const search = new URLSearchParams(window.location.search);
    if (search.has("camera-calibration")) {
      window.sessionStorage.setItem(
        "divetopo-camera-calibration-enabled",
        "true",
      );
    }
    const enableCalibration =
      search.has("camera-calibration") ||
      window.sessionStorage.getItem(
        "divetopo-camera-calibration-enabled",
      ) === "true";
    const frame = window.requestAnimationFrame(() => {
      setCameraCalibrationEnabled(enableCalibration);
    });
    return () => window.cancelAnimationFrame(frame);
  }, []);

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

  useLayoutEffect(() => {
    if (!isCssFullscreen) {
      return;
    }

    const body = document.body;
    const root = document.documentElement;
    const viewerFrame = hostRef.current?.closest(".viewer-frame");
    const previousBodyStyles = {
      overflow: body.style.overflow,
      overscrollBehavior: body.style.overscrollBehavior,
    };
    const previousRootStyles = {
      overflow: root.style.overflow,
      overscrollBehavior: root.style.overscrollBehavior,
    };

    body.style.overflow = "hidden";
    body.style.overscrollBehavior = "none";
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
    let rendererCanvas: HTMLCanvasElement | null = null;
    let contextWasLost = false;
    const vectorLineGeometries: LineGeometry[] = [];
    const vectorLineMaterials: LineMaterial[] = [];
    const vectorLabels: VectorLabel[] = [];

    function handleContextLost(event: Event) {
      event.preventDefault();
      contextWasLost = true;
      if (!cancelled) {
        setStatus("error");
        onError?.();
      }
    }

    function handleContextRestored() {
      if (!cancelled && contextWasLost) {
        onContextRestored?.();
      }
    }

    async function initialise() {
      setStatus("loading");
      setUsesVectorIsobaths(false);
      setTerrainAttribution(null);
      if (!WebGL.isWebGL2Available()) {
        throw new Error("WebGL 2 unavailable");
      }
      const base = `/terrain/${slug}`;
      const metadataResponse = await fetch(`${base}/terrain.json`);
      if (!metadataResponse.ok) {
        throw new Error(`Terrain metadata unavailable for ${slug}`);
      }
      const metadata = (await metadataResponse.json()) as TerrainMetadata;
      const [
        heightBuffer,
        maskBuffer,
        isobathMaskBuffer,
        vectorIsobaths,
      ] = await Promise.all([
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
        vectorIsobathsPath
          ? fetch(vectorIsobathsPath).then((response) => {
              if (!response.ok) {
                throw new Error("Vector isobaths unavailable");
              }
              return response.json() as Promise<VectorIsobaths>;
            })
          : Promise.resolve(null),
      ]);
      if (cancelled || !hostRef.current) return;
      if (
        vectorIsobaths &&
        (vectorIsobaths.coordinateSpace !== "grid-pixels" ||
          !vectorIsobaths.levels ||
          typeof vectorIsobaths.levels !== "object")
      ) {
        throw new Error("Unsupported vector isobath payload");
      }

      metadataRef.current = metadata;
      setUsesVectorIsobaths(Boolean(vectorIsobaths));
      setTerrainAttribution({
        copyright: metadata.credits.copyright,
        requiredDisplay: metadata.credits.requiredDisplay,
        sources: {
          orthophoto:
            compactAttributions?.orthophoto ??
            metadata.textures.orthophoto.attribution,
          topographic:
            compactAttributions?.topographic ??
            metadata.textures.topographic.attribution,
        },
      });
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
      const cellWidthM =
        metadata.physicalSizeM.width / Math.max(width - 1, 1);
      const cellDepthM =
        metadata.physicalSizeM.depth / Math.max(height - 1, 1);
      const reliefSlopeAt = ([gridX, gridY]: [number, number]) => {
        const column = THREE.MathUtils.clamp(
          Math.round(gridX),
          0,
          width - 1,
        );
        const row = THREE.MathUtils.clamp(
          Math.round(gridY),
          0,
          height - 1,
        );
        const leftColumn = Math.max(column - 2, 0);
        const rightColumn = Math.min(column + 2, width - 1);
        const topRow = Math.max(row - 2, 0);
        const bottomRow = Math.min(row + 2, height - 1);
        const sampleIndices = [
          row * width + leftColumn,
          row * width + rightColumn,
          topRow * width + column,
          bottomRow * width + column,
        ];
        if (sampleIndices.some((index) => !validAt(mask, index))) {
          return Number.POSITIVE_INFINITY;
        }
        const horizontalDistanceM =
          Math.max(rightColumn - leftColumn, 1) * cellWidthM;
        const verticalDistanceM =
          Math.max(bottomRow - topRow, 1) * cellDepthM;
        const horizontalSlope =
          (elevations[sampleIndices[1]] -
            elevations[sampleIndices[0]]) /
          horizontalDistanceM;
        const verticalSlope =
          (elevations[sampleIndices[3]] -
            elevations[sampleIndices[2]]) /
          verticalDistanceM;
        return (
          Math.hypot(horizontalSlope, verticalSlope) *
          metadata.verticalExaggeration
        );
      };
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
      if (!vectorIsobaths) {
        installAnalyticIsobaths(
          material,
          isobathsEnabledUniformRef.current,
          pixelRatioUniform,
          maximumDepthM,
        );
      }
      materialRef.current = material;
      mesh = new THREE.Mesh(geometry, material);
      scene.add(mesh);

      const labelCandidates: VectorLabelCandidate[] = [];
      const closedLoopCandidates: Array<{
        levelM: number;
        polylineKey: string;
        score: number;
      }> = [];
      if (vectorIsobaths) {
        const vectorGroup = new THREE.Group();
        vectorGroup.renderOrder = 2;
        vectorGroup.visible = isobathsEnabledRef.current;
        vectorIsobathGroupRef.current = vectorGroup;
        scene.add(vectorGroup);

        const vectorPoint = (
          [gridX, gridY]: [number, number],
          depthM: number,
        ) =>
          new THREE.Vector3(
            (gridX / Math.max(width - 1, 1) - 0.5) *
              metadata.physicalSizeM.width,
            -depthM * metadata.verticalExaggeration,
            (gridY / Math.max(height - 1, 1) - 0.5) *
              metadata.physicalSizeM.depth,
          );
        const outlineMaterial = new LineMaterial({
          color: VECTOR_ISOBATH_OUTLINE,
          linewidth: 3.6,
          worldUnits: false,
          alphaToCoverage: false,
          depthTest: true,
          depthWrite: false,
        });
        outlineMaterial.toneMapped = false;
        installFragmentDepthBias(
          outlineMaterial,
          VECTOR_ISOBATH_DEPTH_BIAS,
        );
        const centerMaterial = new LineMaterial({
          color: VECTOR_ISOBATH_CENTER,
          linewidth: 1.7,
          worldUnits: false,
          alphaToCoverage: false,
          depthTest: true,
          depthWrite: false,
        });
        centerMaterial.toneMapped = false;
        installFragmentDepthBias(
          centerMaterial,
          VECTOR_ISOBATH_DEPTH_BIAS,
        );
        vectorLineMaterials.push(outlineMaterial, centerMaterial);

        for (const [levelText, polylines] of Object.entries(
          vectorIsobaths.levels,
        )) {
          const levelM = Number(levelText);
          if (
            !Number.isFinite(levelM) ||
            levelM >= maximumDepthM - 0.001
          ) {
            continue;
          }
          for (const [polylineIndex, polyline] of polylines.entries()) {
            if (polyline.length < 2) continue;
            const polylineKey = `${levelText}-${polylineIndex}`;
            const linePoints = polyline.map((point) =>
              vectorPoint(point, levelM),
            );
            const lineGeometry = new LineGeometry();
            lineGeometry.setPositions(
              linePoints.flatMap((point) => [
                point.x,
                point.y,
                point.z,
              ]),
            );
            vectorLineGeometries.push(lineGeometry);

            const outline = new Line2(
              lineGeometry,
              outlineMaterial,
            );
            outline.computeLineDistances();
            outline.renderOrder = 2;
            const center = new Line2(lineGeometry, centerMaterial);
            center.computeLineDistances();
            center.renderOrder = 3;
            vectorGroup.add(outline, center);

            const firstPoint = polyline[0];
            const lastPoint = polyline[polyline.length - 1];
            const closed =
              Math.hypot(
                firstPoint[0] - lastPoint[0],
                firstPoint[1] - lastPoint[1],
              ) < 2;
            if (closed) {
              const gridXs = polyline.map(([gridX]) => gridX);
              const gridYs = polyline.map(([, gridY]) => gridY);
              const loopWidthM =
                (Math.max(...gridXs) - Math.min(...gridXs)) *
                cellWidthM;
              const loopDepthM =
                (Math.max(...gridYs) - Math.min(...gridYs)) *
                cellDepthM;
              if (loopWidthM >= 45 && loopDepthM >= 35) {
                closedLoopCandidates.push({
                  levelM,
                  polylineKey,
                  score: loopWidthM * loopDepthM,
                });
              }
            }

            if (linePoints.length < 5) continue;
            const stride = Math.max(
              1,
              Math.floor((linePoints.length - 4) / 24),
            );
            for (
              let index = 2;
              index < linePoints.length - 2;
              index += stride
            ) {
              const tangent = linePoints[index + 2]
                .clone()
                .sub(linePoints[index - 2])
                .normalize();
              labelCandidates.push({
                levelM,
                polylineKey,
                point: linePoints[index].clone(),
                tangent,
                reliefSlope: reliefSlopeAt(polyline[index]),
                sourceScore: Math.min(linePoints.length, 300),
              });
            }
          }
        }
      }

      const hemisphere = new THREE.HemisphereLight("#dffbff", "#10262d", 1.7);
      scene.add(hemisphere);
      const fillLight = new THREE.AmbientLight("#fff7e8", 0.28);
      scene.add(fillLight);
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
      const hasExplicitCenterOffset =
        initialCenterOffsetEastM !== 0 || initialCenterOffsetSouthM !== 0;
      // A page-level center translation is already the canonical override for
      // legacy captures that encoded the along-view shift in world axes.
      if (
        !hasExplicitCenterOffset &&
        metadata.view.alongCenterOffsetM !== undefined
      ) {
        shore.addScaledVector(
          horizontalForward,
          metadata.view.alongCenterOffsetM - shore.dot(horizontalForward),
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
      target.x += initialCenterOffsetEastM;
      target.z += initialCenterOffsetSouthM;

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
      camera.zoom = THREE.MathUtils.clamp(initialZoom, 0.65, 8);
      camera.updateProjectionMatrix();
      cameraRef.current = camera;

      const vectorGroup = vectorIsobathGroupRef.current;
      let updateVectorLabels: (
        chooseAnchors: boolean,
        useInteractionInset?: boolean,
      ) => void = () => {};
      if (vectorGroup && labelCandidates.length) {
        const requiredLevels = new Set(
          metadata.view.requiredVectorLabelLevelsM ?? [],
        );
        const featuredLevelPreference = new Set(
          metadata.view.featuredVectorLabelLevelsM ?? [],
        );
        const featuredLoopPool = featuredLevelPreference.size
          ? closedLoopCandidates.filter(({ levelM }) =>
              featuredLevelPreference.has(levelM),
            )
          : closedLoopCandidates;
        const featuredLoops = featuredLoopPool
          .sort((first, second) => second.score - first.score)
          .filter(
            (candidate, index, candidates) =>
              index ===
              candidates.findIndex(
                (other) => other.levelM === candidate.levelM,
              ),
          )
          .slice(0, featuredLevelPreference.size || 2);
        const featuredPolylineKeys = new Set(
          featuredLoops.map(({ polylineKey }) => polylineKey),
        );
        const featuredLevels = new Set(
          featuredLoops.map(({ levelM }) => levelM),
        );
        const levels = Array.from(
          new Set(labelCandidates.map((candidate) => candidate.levelM)),
        ).sort((first, second) => first - second);
        const addVectorLabel = (
          levelM: number,
          candidatePolylineKey: string | null,
        ) => {
          const texture = createDepthLabelTexture(levelM);
          const spriteMaterial = new THREE.SpriteMaterial({
            map: texture,
            transparent: true,
            // Labels are annotations rather than contour geometry. Their
            // anchors stay fixed while the camera moves, so the text remains
            // stable; opt-in sites may reselect them once interaction ends.
            depthTest: false,
            depthWrite: false,
            toneMapped: false,
          });
          const sprite = new THREE.Sprite(spriteMaterial);
          sprite.renderOrder = 4;
          sprite.visible = false;
          vectorGroup.add(sprite);
          vectorLabels.push({
            levelM,
            candidatePolylineKey,
            sprite,
            texture,
          });
        };
        for (const { levelM, polylineKey } of featuredLoops) {
          addVectorLabel(levelM, polylineKey);
        }
        for (const levelM of levels) {
          if (
            requiredLevels.has(levelM) &&
            featuredLevels.has(levelM)
          ) {
            continue;
          }
          addVectorLabel(levelM, null);
        }

        updateVectorLabels = (
          chooseAnchors: boolean,
          useInteractionInset = false,
        ) => {
          if (!vectorLabels.length) return;
          const currentHost = hostRef.current;
          if (!currentHost) return;
          camera.updateMatrixWorld();
          const worldUnitsPerCssPixel =
            (camera.top - camera.bottom) /
            (Math.max(currentHost.clientHeight, 1) * camera.zoom);
          for (const label of vectorLabels) {
            label.sprite.scale.set(
              LABEL_WIDTH_CSS_PX * worldUnitsPerCssPixel,
              LABEL_HEIGHT_CSS_PX * worldUnitsPerCssPixel,
              1,
            );
          }
          if (!chooseAnchors) return;

          const occupied: Array<{
            left: number;
            right: number;
            top: number;
            bottom: number;
          }> = [];
          const halfWidthNdc =
            LABEL_WIDTH_CSS_PX /
            Math.max(currentHost.clientWidth, 1);
          const halfHeightNdc =
            LABEL_HEIGHT_CSS_PX /
            Math.max(currentHost.clientHeight, 1);
          const verticalInsetFraction = THREE.MathUtils.clamp(
            useInteractionInset
              ? (metadata.view.vectorLabelVerticalInsetFraction ?? 0.12)
              : 0.12,
            0.01,
            0.25,
          );
          const verticalLimitNdc = 1 - verticalInsetFraction * 2;
          const collisionPaddingNdc = THREE.MathUtils.clamp(
            metadata.view.vectorLabelCollisionPaddingNdc ?? 0.025,
            0,
            0.1,
          );

          for (const label of vectorLabels) {
            const visibleCandidates: Array<{
              candidate: VectorLabelCandidate;
              projected: THREE.Vector3;
              cameraDepth: number;
            }> = [];
            for (const candidate of labelCandidates) {
              if (candidate.levelM !== label.levelM) continue;
              if (
                label.candidatePolylineKey
                  ? candidate.polylineKey !==
                    label.candidatePolylineKey
                  : featuredPolylineKeys.has(candidate.polylineKey)
              ) {
                continue;
              }
              const projected = candidate.point.clone().project(camera);
              if (
                projected.z < -1 ||
                projected.z > 1 ||
                Math.abs(projected.x) > 0.82 ||
                Math.abs(projected.y) > verticalLimitNdc
              ) {
                continue;
              }
              const cameraDepth = -candidate.point
                .clone()
                .applyMatrix4(camera.matrixWorldInverse).z;
              visibleCandidates.push({
                candidate,
                projected,
                cameraDepth,
              });
            }
            if (!visibleCandidates.length) {
              label.sprite.visible = false;
              continue;
            }
            const minimumCameraDepth = Math.min(
              ...visibleCandidates.map(({ cameraDepth }) => cameraDepth),
            );
            const maximumCameraDepth = Math.max(
              ...visibleCandidates.map(({ cameraDepth }) => cameraDepth),
            );
            const cameraDepthRange = Math.max(
              maximumCameraDepth - minimumCameraDepth,
              1e-6,
            );
            let best:
              | { candidate: VectorLabelCandidate; score: number }
              | undefined;
            let bestOverlapping:
              | { candidate: VectorLabelCandidate; score: number }
              | undefined;
            for (const {
              candidate,
              projected,
              cameraDepth,
            } of visibleCandidates) {
              const projectedTangent = candidate.point
                .clone()
                .addScaledVector(candidate.tangent, 5)
                .project(camera);
              const deltaX = projectedTangent.x - projected.x;
              const deltaY = projectedTangent.y - projected.y;
              const horizontal =
                Math.abs(deltaX) /
                (Math.abs(deltaX) + Math.abs(deltaY) + 1e-6);
              const bounds = {
                left: projected.x - halfWidthNdc,
                right: projected.x + halfWidthNdc,
                top: projected.y + halfHeightNdc,
                bottom: projected.y - halfHeightNdc,
              };
              const overlaps = occupied.some(
                (other) =>
                  bounds.left < other.right + collisionPaddingNdc &&
                  bounds.right > other.left - collisionPaddingNdc &&
                  bounds.bottom < other.top + collisionPaddingNdc &&
                  bounds.top > other.bottom - collisionPaddingNdc,
              );
              const edgeClearance = Math.min(
                0.82 - Math.abs(projected.x),
                verticalLimitNdc - Math.abs(projected.y),
              );
              const foregroundScreen =
                (verticalLimitNdc - projected.y) /
                (verticalLimitNdc * 2);
              const foregroundDepth =
                (maximumCameraDepth - cameraDepth) / cameraDepthRange;
              const gentleRelief =
                1 / (1 + Math.max(candidate.reliefSlope, 0));
              const horizontalFocus =
                isobathLabelFocusXNdc === undefined
                  ? 0
                  : Math.max(
                      0,
                      1 -
                        Math.abs(
                          projected.x - isobathLabelFocusXNdc,
                        ) /
                          0.9,
                    ) * 210;
              const score =
                horizontalFocus +
                horizontal * 55 +
                edgeClearance * 30 +
                foregroundScreen * 95 +
                foregroundDepth * 170 +
                gentleRelief * 120 +
                candidate.sourceScore * 0.02;
              if (overlaps) {
                if (
                  requiredLevels.has(label.levelM) &&
                  (!bestOverlapping ||
                    score > bestOverlapping.score)
                ) {
                  bestOverlapping = { candidate, score };
                }
                continue;
              }
              if (!best || score > best.score) {
                best = { candidate, score };
              }
            }
            best ??= bestOverlapping;
            if (!best) {
              label.sprite.visible = false;
              continue;
            }
            label.sprite.position.copy(best.candidate.point);
            label.sprite.visible = true;
            const projected = best.candidate.point.clone().project(camera);
            occupied.push({
              left: projected.x - halfWidthNdc,
              right: projected.x + halfWidthNdc,
              top: projected.y + halfHeightNdc,
              bottom: projected.y - halfHeightNdc,
            });
          }
        };
      }

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
      rendererCanvas = renderer.domElement;
      rendererCanvas.addEventListener(
        "webglcontextlost",
        handleContextLost,
      );
      rendererCanvas.addEventListener(
        "webglcontextrestored",
        handleContextRestored,
      );
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
      cameraCalibrationOriginRef.current = {
        horizontalOffset: camera.position.clone().sub(controls.target),
        panOriginTarget: controls.target.clone(),
      };
      if (initialOrbitAzimuthDeg !== 0) {
        camera.position
          .sub(controls.target)
          .applyAxisAngle(
            new THREE.Vector3(0, 1, 0),
            THREE.MathUtils.degToRad(initialOrbitAzimuthDeg),
          )
          .add(controls.target);
        camera.lookAt(controls.target);
        controls.update();
      }
      if (initialCameraElevationDeg !== undefined) {
        const offset = camera.position.clone().sub(controls.target);
        const horizontalDistance = Math.hypot(offset.x, offset.z);
        if (horizontalDistance > 1e-6) {
          offset.y =
            horizontalDistance *
            Math.tan(
              THREE.MathUtils.degToRad(initialCameraElevationDeg),
            );
          camera.position.copy(controls.target).add(offset);
          camera.lookAt(controls.target);
          controls.update();
        }
      }
      if (initialPanRightM !== 0 || initialPanUpM !== 0) {
        const screenTranslation = new THREE.Vector3()
          .addScaledVector(
            new THREE.Vector3(1, 0, 0).applyQuaternion(camera.quaternion),
            -initialPanRightM,
          )
          .addScaledVector(
            new THREE.Vector3(0, 1, 0).applyQuaternion(camera.quaternion),
            -initialPanUpM,
          );
        camera.position.add(screenTranslation);
        controls.target.add(screenTranslation);
        controls.cursor.copy(controls.target);
        camera.lookAt(controls.target);
        controls.update();
      }
      initialViewRef.current = {
        position: camera.position.clone(),
        target: controls.target.clone(),
        zoom: camera.zoom,
      };
      updateVectorLabels(true);

      const render = () => {
        if (scene && rendererRef.current && cameraRef.current) {
          updateVectorLabels(false);
          const currentHost = hostRef.current;
          if (currentHost) {
            updateTerrainScale(
              scaleBarRef.current,
              scaleLabelRef.current,
              cameraRef.current,
              currentHost,
            );
          }
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
      if (metadata.view.reselectVectorLabelsOnCameraEnd) {
        controls.addEventListener("end", () => {
          updateVectorLabels(true, true);
          render();
        });
      }

      const resize = () => {
        resizeFrame = 0;
        const currentHost = hostRef.current;
        const currentRenderer = rendererRef.current;
        const currentCamera = cameraRef.current;
        if (!currentHost || !currentRenderer || !currentCamera) return;
        const pixelRatio = Math.min(window.devicePixelRatio, 1.75);
        const pixelRatioChanged =
          currentRenderer.getPixelRatio() !== pixelRatio;
        if (pixelRatioChanged) {
          currentRenderer.setPixelRatio(pixelRatio);
          pixelRatioUniform.value = pixelRatio;
        }
        const widthPx = Math.max(currentHost.clientWidth, 1);
        const heightPx = Math.max(currentHost.clientHeight, 1);
        if (
          !pixelRatioChanged &&
          widthPx === lastWidth &&
          heightPx === lastHeight
        ) {
          return;
        }
        lastWidth = widthPx;
        lastHeight = heightPx;
        // Keep the canvas CSS box and its WebGL backing store synchronized.
        // WebKit standalone can otherwise composite the resized buffer beyond
        // the canvas bounds after an orientation change.
        currentRenderer.setSize(widthPx, heightPx, true);
        vectorLineMaterials.forEach((lineMaterial) => {
          lineMaterial.resolution.set(widthPx, heightPx);
        });
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
        updateVectorLabels(true);
        render();
      };
      resizeObserver = new ResizeObserver(() => {
        if (resizeFrame) cancelAnimationFrame(resizeFrame);
        resizeFrame = requestAnimationFrame(resize);
      });
      resizeObserver.observe(mount);
      resize();

      await setTexture(styleRef.current);
      render();
      if (!cancelled) {
        setStatus("ready");
        onReady?.();
      }
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
      if (!cancelled) {
        setStatus("error");
        onError?.();
      }
    });

    return () => {
      cancelled = true;
      resizeObserver?.disconnect();
      if (resizeFrame) cancelAnimationFrame(resizeFrame);
      rendererCanvas?.removeEventListener(
        "webglcontextlost",
        handleContextLost,
      );
      rendererCanvas?.removeEventListener(
        "webglcontextrestored",
        handleContextRestored,
      );
      controlsRef.current?.dispose();
      rendererRef.current?.dispose();
      geometry?.dispose();
      vectorLineGeometries.forEach((lineGeometry) =>
        lineGeometry.dispose(),
      );
      vectorLineMaterials.forEach((lineMaterial) =>
        lineMaterial.dispose(),
      );
      vectorLabels.forEach(({ sprite, texture }) => {
        sprite.material.dispose();
        texture.dispose();
      });
      materialRef.current?.dispose();
      Object.values(textureCacheRef.current).forEach((texture) =>
        texture?.dispose(),
      );
      textureCacheRef.current = {};
      rendererRef.current?.domElement.remove();
      rendererRef.current = null;
      sceneRef.current = null;
      vectorIsobathGroupRef.current = null;
      controlsRef.current = null;
      cameraRef.current = null;
      materialRef.current = null;
      metadataRef.current = null;
      cameraCalibrationOriginRef.current = null;
      mesh = null;
      scene = null;
    };
  }, [
    initialCameraElevationDeg,
    initialCenterOffsetEastM,
    initialCenterOffsetSouthM,
    initialOrbitAzimuthDeg,
    initialPanRightM,
    initialPanUpM,
    initialZoom,
    isobathLabelFocusXNdc,
    compactAttributions,
    onContextRestored,
    onError,
    onReady,
    slug,
    vectorIsobathsPath,
  ]);

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

    updateTexture().catch(() => {
      setStatus("error");
      onError?.();
    });
    return () => {
      cancelled = true;
    };
  }, [onError, slug, style]);

  function renderCurrentScene() {
    const renderer = rendererRef.current;
    const camera = cameraRef.current;
    const scene = sceneRef.current;
    if (renderer && camera && scene) renderer.render(scene, camera);
  }

  function toggleIsobaths() {
    const nextValue = !isobathsEnabled;
    isobathsEnabledRef.current = nextValue;
    isobathsEnabledUniformRef.current.value = nextValue ? 1 : 0;
    if (vectorIsobathGroupRef.current) {
      vectorIsobathGroupRef.current.visible = nextValue;
    }
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

  function currentCameraCalibration(): CameraCalibrationSnapshot | null {
    const camera = cameraRef.current;
    const controls = controlsRef.current;
    const origin = cameraCalibrationOriginRef.current;
    if (!camera || !controls || !origin) return null;

    const offset = camera.position.clone().sub(controls.target);
    const baseAzimuth = Math.atan2(
      origin.horizontalOffset.x,
      origin.horizontalOffset.z,
    );
    const currentAzimuth = Math.atan2(offset.x, offset.z);
    const orbitAzimuthDeg = normalisedAngleDeg(
      THREE.MathUtils.radToDeg(currentAzimuth - baseAzimuth),
    );
    const cameraElevationDeg = THREE.MathUtils.radToDeg(
      Math.atan2(offset.y, Math.hypot(offset.x, offset.z)),
    );

    const screenRight = new THREE.Vector3(1, 0, 0).applyQuaternion(
      camera.quaternion,
    );
    const screenUp = new THREE.Vector3(0, 1, 0).applyQuaternion(
      camera.quaternion,
    );
    const screenForward = new THREE.Vector3(0, 0, -1).applyQuaternion(
      camera.quaternion,
    );
    const targetDelta = controls.target
      .clone()
      .sub(origin.panOriginTarget);

    return {
      schema: "divetopo-camera-calibration-v1",
      slug,
      siteName,
      capturedAt: new Date().toISOString(),
      interactiveInitialView: {
        zoom: rounded(camera.zoom),
        orbitAzimuthDeg: rounded(orbitAzimuthDeg, 2),
        cameraElevationDeg: rounded(cameraElevationDeg, 2),
        panRightM: rounded(-targetDelta.dot(screenRight), 2),
        panUpM: rounded(-targetDelta.dot(screenUp), 2),
        centerOffsetEastM: initialCenterOffsetEastM,
        centerOffsetSouthM: initialCenterOffsetSouthM,
        ...(isobathLabelFocusXNdc === undefined
          ? {}
          : { isobathLabelFocusXNdc }),
      },
      diagnostic: {
        cameraPosition: {
          x: rounded(camera.position.x),
          y: rounded(camera.position.y),
          z: rounded(camera.position.z),
        },
        target: {
          x: rounded(controls.target.x),
          y: rounded(controls.target.y),
          z: rounded(controls.target.z),
        },
        panResidualForwardM: rounded(targetDelta.dot(screenForward), 3),
      },
    };
  }

  async function saveCameraCalibration() {
    const calibration = currentCameraCalibration();
    if (!calibration) return;
    const serialized = `${JSON.stringify(calibration, null, 2)}\n`;
    window.localStorage.setItem(
      `divetopo-camera-calibration:${slug}`,
      serialized,
    );

    const href = URL.createObjectURL(
      new Blob([serialized], { type: "application/json" }),
    );
    const anchor = document.createElement("a");
    anchor.href = href;
    anchor.download = `${slug}-camera-calibration.json`;
    anchor.click();
    URL.revokeObjectURL(href);

    try {
      await navigator.clipboard.writeText(serialized);
      setCameraCalibrationMessage("JSON téléchargé et copié.");
    } catch {
      setCameraCalibrationMessage("JSON téléchargé.");
    }
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

    const forceCssFullscreenForLocalQa =
      window.location.hostname === "localhost" &&
      new URLSearchParams(window.location.search).has(
        "force-css-fullscreen",
      );

    if (
      !forceCssFullscreenForLocalQa &&
      typeof host.requestFullscreen === "function"
    ) {
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
  const sourceAttribution = terrainAttribution?.sources[style];
  const copyright = terrainAttribution?.copyright;

  return (
    <div
      className={`terrain-host is-interactive${downloadHref ? " has-download" : ""}${isCssFullscreen ? " is-css-fullscreen" : ""}`}
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
      <div
        className={`terrain-scale${status === "ready" ? " is-visible" : ""}`}
        ref={scaleBarRef}
        aria-hidden="true"
      >
        <span className="terrain-scale-label" ref={scaleLabelRef}>
          50 m
        </span>
        <span className="terrain-scale-track">
          <span className="terrain-scale-line" />
        </span>
      </div>
      {status === "ready" &&
      isobathsEnabled &&
      isobathLevels.length > 0 &&
      !usesVectorIsobaths ? (
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
      {status === "ready" && sourceAttribution && copyright ? (
        <div
          className="terrain-attribution"
          aria-label={terrainAttribution.requiredDisplay}
        >
          <span className="terrain-attribution-source">
            {sourceAttribution}
          </span>
          <span className="terrain-attribution-copyright">
            {copyright}
          </span>
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
        {downloadHref && downloadLabel ? (
          <a
            className="terrain-icon-button terrain-download"
            href={downloadHref}
            download={downloadFilename}
            aria-label={downloadLabel}
            title={downloadLabel}
          >
            <span className="terrain-download-arrow" aria-hidden="true">
              ↓
            </span>
          </a>
        ) : null}
      </div>
      {cameraCalibrationEnabled ? (
        <aside
          className="terrain-camera-calibration"
          data-testid="terrain-camera-calibration"
          aria-label="Calibration temporaire de la caméra"
        >
          <strong>Calibration caméra · {siteName}</strong>
          <span>
            Déplacez la vue, puis enregistrez le cadrage retenu.
          </span>
          <button type="button" onClick={saveCameraCalibration}>
            Enregistrer ce cadrage
          </button>
          {cameraCalibrationMessage ? (
            <output>{cameraCalibrationMessage}</output>
          ) : null}
        </aside>
      ) : null}
    </div>
  );
}
