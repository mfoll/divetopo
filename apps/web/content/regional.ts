import reunionMapManifestJson from "./map-manifest.json";
import pacaMapManifestJson from "./paca-map-manifest.json";

export type SurfaceStyle = "topographic" | "orthophoto";
export type MapView = "2d" | "3d";

export type AssetVariant = {
  src: string;
  width: number;
  height: number;
};

export type MapAsset = {
  view: MapView;
  style: SurfaceStyle;
  sourceDimensions: { width: number; height: number };
  variants: AssetVariant[];
  download: AssetVariant & { filename: string };
};

export type PlancheAsset = {
  style: SurfaceStyle;
  preview: AssetVariant;
  download: AssetVariant & { filename: string };
};

export type SiteLocation = {
  city: string;
  latitude: number;
  longitude: number;
};

export type RegionalAssetSite = {
  slug: string;
  displayName: string;
  plateTitle: string;
  assetBasePath?: string;
  location: SiteLocation;
  westCoastLocatorPosition: {
    xPercent: number;
    yPercent: number;
  };
  maxDepthM: number;
  planMaxDepthM: number;
  verticalExaggeration: number;
  orthophotoCaptureDate: string;
  plateAuthor: string;
  copyrightYear: number;
  mapLicense: string;
  compactAttributions?: Record<SurfaceStyle, string>;
  interactiveInitialView?: {
    zoom?: number;
    orbitAzimuthDeg?: number;
    cameraElevationDeg?: number;
    panRightM?: number;
    panUpM?: number;
    centerOffsetEastM?: number;
    centerOffsetSouthM?: number;
    isobathLabelFocusXNdc?: number;
  };
  maps: MapAsset[];
  planches?: PlancheAsset[];
};

export type RegionalMapManifest = {
  reunionOverview: AssetVariant;
  westCoastLocator: AssetVariant;
  sites: RegionalAssetSite[];
};

export type RegionSlug = "reunion" | "paca";

export const reunionMapManifest = reunionMapManifestJson as RegionalMapManifest;
export const pacaMapManifest = pacaMapManifestJson as RegionalMapManifest;

export const REUNION_COMPACT_ATTRIBUTIONS: Record<SurfaceStyle, string> = {
  orthophoto:
    "Bathymétrie : HYSCORES / Litto3D · Topographie : IGN RGE ALTI · Orthophoto : IGN BD ORTHO",
  topographic:
    "Bathymétrie : HYSCORES / Litto3D · Topographie : IGN RGE ALTI",
};

export const PACA_COMPACT_ATTRIBUTIONS: Record<SurfaceStyle, string> = {
  orthophoto:
    "Bathymétrie : Shom–IGN Litto3D PACA 2015 · Topographie : Shom–IGN Litto3D PACA 2015 · Orthophoto : IGN BD ORTHO · Référentiel vertical IGN69",
  topographic:
    "Bathymétrie : Shom–IGN Litto3D PACA 2015 · Topographie : Shom–IGN Litto3D PACA 2015 · Référentiel vertical IGN69",
};

export type SiteLabelLayout = {
  side: "left" | "right";
  shiftYRem: number;
  connectorAngleDeg: number;
  connectorWidthRem?: number;
  labelOffsetRem?: number;
  lines?: readonly string[];
  widthRem?: number;
};

export const REUNION_SITE_LABEL_LAYOUT: Record<string, SiteLabelLayout> = {
  "cap-la-houssaye": {
    side: "right",
    shiftYRem: -1.45,
    connectorAngleDeg: -42,
    connectorWidthRem: 1.35,
  },
  "boucan-canot": {
    side: "left",
    shiftYRem: -1.7,
    connectorAngleDeg: 48,
    connectorWidthRem: 1.45,
  },
  "cap-homard": {
    side: "right",
    shiftYRem: -0.15,
    connectorAngleDeg: -10,
    connectorWidthRem: 1.3,
    labelOffsetRem: 2.6,
  },
  "pointe-des-aigrettes": {
    side: "right",
    shiftYRem: 2.15,
    connectorAngleDeg: 58,
    connectorWidthRem: 2.45,
    labelOffsetRem: 2.65,
  },
  "roches-noires": {
    side: "left",
    shiftYRem: 0.9,
    connectorAngleDeg: -58,
    connectorWidthRem: 1,
    labelOffsetRem: 1.9,
    lines: ["Roches Noires"],
  },
  "passe-hermitage": {
    side: "right",
    shiftYRem: 0,
    connectorAngleDeg: 0,
  },
  "trois-bassins": {
    side: "left",
    shiftYRem: -0.45,
    connectorAngleDeg: 20,
  },
  "souris-chaude": {
    side: "right",
    shiftYRem: 0.15,
    connectorAngleDeg: 8,
  },
  "pont-rouge": {
    side: "left",
    shiftYRem: -0.5,
    connectorAngleDeg: 22,
  },
  "plage-cimetiere-saint-leu": {
    side: "left",
    shiftYRem: -0.5,
    connectorAngleDeg: 22,
  },
  "pointe-au-sel-sec-jaune": {
    side: "left",
    shiftYRem: 0.45,
    connectorAngleDeg: -18,
  },
};

export const PACA_SITE_LABEL_LAYOUT: Record<string, SiteLabelLayout> = {
  "pointe-portissol": {
    side: "right",
    shiftYRem: -3.5,
    connectorAngleDeg: -76.2,
    connectorWidthRem: 3.68,
    labelOffsetRem: 2.25,
    widthRem: 6.92,
  },
  "deux-freres-cap-sicie": {
    side: "right",
    shiftYRem: -2,
    connectorAngleDeg: -73.2,
    connectorWidthRem: 2.17,
    labelOffsetRem: 2,
    widthRem: 6.02,
  },
  "cap-des-medes": {
    side: "right",
    shiftYRem: -1,
    connectorAngleDeg: -26.8,
    connectorWidthRem: 2.38,
    labelOffsetRem: 3.5,
    widthRem: 5.86,
  },
  "la-gabiniere-port-cros": {
    side: "right",
    shiftYRem: 1.5,
    connectorAngleDeg: 58.5,
    connectorWidthRem: 1.67,
    labelOffsetRem: 2.25,
    widthRem: 5.11,
  },
  "les-pyramides-cap-dramont": {
    side: "left",
    shiftYRem: -1.0,
    connectorAngleDeg: 50.8,
    connectorWidthRem: 1.39,
    labelOffsetRem: 2.25,
    widthRem: 5.63,
  },
};
