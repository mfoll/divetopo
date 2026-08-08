import reunionMapManifestJson from "./map-manifest.json";
import pacaMapManifestJson from "./paca-map-manifest.json";
import alpesMaritimesMapManifestJson from "./alpes-maritimes-map-manifest.json";
import bouchesDuRhoneMapManifestJson from "./bouches-du-rhone-map-manifest.json";
import varCentreMapManifestJson from "./var-centre-map-manifest.json";
import varEstMapManifestJson from "./var-est-map-manifest.json";
import varOuestMapManifestJson from "./var-ouest-map-manifest.json";

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

export type SiteLabelLayout = {
  side: "left" | "right";
  shiftYRem: number;
  connectorAngleDeg: number;
  connectorWidthRem?: number;
  labelOffsetRem?: number;
  lines?: readonly string[];
  widthRem?: number;
};

export type RegionalAssetSite = {
  slug: string;
  displayName: string;
  plateTitle: string;
  config: string;
  assetBasePath?: string;
  location: SiteLocation;
  westCoastLocatorPosition: {
    xPercent: number;
    yPercent: number;
  };
  siteLabelLayout: SiteLabelLayout;
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

export type RegionSlug =
  | "reunion"
  | "paca"
  | "bouches-du-rhone"
  | "var-ouest"
  | "var-centre"
  | "var-est"
  | "alpes-maritimes";

export type AutonomousMediterraneanRegionSlug = Exclude<
  RegionSlug,
  "reunion" | "paca"
>;

export const reunionMapManifest = reunionMapManifestJson as RegionalMapManifest;
export const pacaMapManifest = pacaMapManifestJson as RegionalMapManifest;
export const bouchesDuRhoneMapManifest =
  bouchesDuRhoneMapManifestJson as RegionalMapManifest;
export const varOuestMapManifest =
  varOuestMapManifestJson as RegionalMapManifest;
export const varCentreMapManifest =
  varCentreMapManifestJson as RegionalMapManifest;
export const varEstMapManifest =
  varEstMapManifestJson as RegionalMapManifest;
export const alpesMaritimesMapManifest =
  alpesMaritimesMapManifestJson as RegionalMapManifest;

export const regionalMapManifests: Record<
  RegionSlug,
  RegionalMapManifest
> = {
  reunion: reunionMapManifest,
  paca: pacaMapManifest,
  "bouches-du-rhone": bouchesDuRhoneMapManifest,
  "var-ouest": varOuestMapManifest,
  "var-centre": varCentreMapManifest,
  "var-est": varEstMapManifest,
  "alpes-maritimes": alpesMaritimesMapManifest,
};

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
