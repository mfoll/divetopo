"use client";

/* eslint-disable @next/next/no-img-element -- responsive map derivatives are generated locally and swapped in place */

import {
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useRef,
  useState,
  type CSSProperties,
} from "react";
import { topoReunionCopy } from "../content/copy";
import type { Language, Theme } from "../content/preferences";
import {
  languagePath,
  localizedSitePath,
  parseTopoRoute,
  regionalSeoText,
} from "../content/routing";
import mapManifestJson from "../content/map-manifest.json";
import InstallPrompt from "./InstallPrompt";
import PreferenceControls from "./PreferenceControls";

type SurfaceStyle = "topographic" | "orthophoto";
type MapView = "2d" | "3d";
type ViewMode = MapView | "interactive";
type Unified3DRendererState = "loading" | "ready" | "error";

type AssetVariant = {
  src: string;
  width: number;
  height: number;
};

type MapAsset = {
  view: MapView;
  style: SurfaceStyle;
  sourceDimensions: { width: number; height: number };
  variants: AssetVariant[];
  download: AssetVariant & { filename: string };
};

type PlancheAsset = {
  style: SurfaceStyle;
  preview: AssetVariant;
  download: AssetVariant & { filename: string };
};

type SiteLocation = {
  city: string;
  latitude: number;
  longitude: number;
};

type WestCoastLocatorPosition = {
  xPercent: number;
  yPercent: number;
};

type InteractiveInitialView = {
  zoom: number;
  centerOffsetEastM: number;
  centerOffsetSouthM: number;
};

type TopoReunionAssetSite = {
  slug: string;
  displayName: string;
  plateTitle: string;
  location: SiteLocation;
  westCoastLocatorPosition: WestCoastLocatorPosition;
  maxDepthM: number;
  planMaxDepthM: number;
  verticalExaggeration: number;
  orthophotoCaptureDate: string;
  plateAuthor: string;
  copyrightYear: number;
  mapLicense: string;
  compactAttributions?: Record<SurfaceStyle, string>;
  interactiveInitialView?: InteractiveInitialView;
  maps: MapAsset[];
  planches: PlancheAsset[];
};

type MapManifest = {
  reunionOverview: AssetVariant;
  westCoastLocator: AssetVariant;
  sites: TopoReunionAssetSite[];
};

const TerrainViewer = lazy(() => import("./TerrainViewer"));
const REUNION_COMPACT_ATTRIBUTIONS: Record<SurfaceStyle, string> = {
  orthophoto:
    "Bathymétrie : HYSCORES / Litto3D · Topographie : IGN RGE ALTI · Orthophoto : IGN BD ORTHO",
  topographic:
    "Bathymétrie : HYSCORES / Litto3D · Topographie : IGN RGE ALTI",
};
function dynamicCaptureAsset(
  slug: string,
  style: SurfaceStyle,
): MapAsset {
  const base = `/maps/${slug}`;
  return {
    view: "3d",
    style,
    sourceDimensions: { width: 2474, height: 1712 },
    variants: [
      { src: `${base}/3d-dynamic-${style}-960.webp`, width: 960, height: 664 },
      { src: `${base}/3d-dynamic-${style}-1600.webp`, width: 1600, height: 1107 },
      { src: `${base}/3d-dynamic-${style}-2474.webp`, width: 2474, height: 1712 },
    ],
    download: {
      src: `${base}/downloads/3d-dynamic-${style}-full.jpg`,
      width: 2474,
      height: 1712,
      filename: `${slug}-3d-dynamique-${style}.jpg`,
    },
  };
}

function dynamicMobileCapture(
  slug: string,
  style: SurfaceStyle,
): AssetVariant {
  return {
    src: `/maps/${slug}/3d-dynamic-${style}-mobile-960.webp`,
    width: 960,
    height: 662,
  };
}
const mapManifest = mapManifestJson as MapManifest;
const initialSite = mapManifest.sites[0];

if (!initialSite) {
  throw new Error("Topo Réunion requires at least one site");
}

function assetSrcSet(variants: AssetVariant[]) {
  return variants.map((variant) => `${variant.src} ${variant.width}w`).join(", ");
}

function selectedMap(
  site: TopoReunionAssetSite,
  view: MapView,
  style: SurfaceStyle,
) {
  const asset = site.maps.find(
    (candidate) => candidate.view === view && candidate.style === style,
  );
  if (!asset) throw new Error(`Missing ${view}/${style} map for ${site.slug}`);
  return asset;
}

function selectedPlanche(site: TopoReunionAssetSite, style: SurfaceStyle) {
  const asset = site.planches.find(
    (candidate) => candidate.style === style,
  );
  if (!asset) throw new Error(`Missing ${style} planche for ${site.slug}`);
  return asset;
}

function formatDms(value: number, positive: string, negative: string) {
  const totalTenths = Math.round(Math.abs(value) * 36_000);
  const degrees = Math.floor(totalTenths / 36_000);
  const remainingTenths = totalTenths % 36_000;
  const minutes = Math.floor(remainingTenths / 600);
  const seconds = (remainingTenths % 600) / 10;
  const direction = value < 0 ? negative : positive;
  return `${degrees}° ${String(minutes).padStart(2, "0")}′ ${seconds
    .toFixed(1)
    .padStart(4, "0")}″ ${direction}`;
}

function gpsLabel(location: SiteLocation, language: Language) {
  return `${formatDms(location.latitude, "N", "S")} · ${formatDms(
    location.longitude,
    "E",
    language === "fr" ? "O" : "W",
  )}`;
}

function googleMapsUrl(location: SiteLocation) {
  const query = `${location.latitude.toFixed(8)},${location.longitude.toFixed(8)}`;
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`;
}

function SurfaceToggle({
  value,
  onChange,
  language,
}: {
  value: SurfaceStyle;
  onChange: (style: SurfaceStyle) => void;
  language: Language;
}) {
  const text = topoReunionCopy[language];

  return (
    <fieldset className="segmented-control surface-control">
      <legend>{text.surfaceGroup}</legend>
      <button
        type="button"
        aria-pressed={value === "orthophoto"}
        onClick={() => onChange("orthophoto")}
      >
        {text.surfaces.orthophoto.label}
      </button>
      <button
        type="button"
        aria-pressed={value === "topographic"}
        onClick={() => onChange("topographic")}
      >
        {text.surfaces.topographic.label}
      </button>
    </fieldset>
  );
}

function ViewToggle({
  value,
  onChange,
  language,
  unified3D = false,
}: {
  value: ViewMode;
  onChange: (view: ViewMode) => void;
  language: Language;
  unified3D?: boolean;
}) {
  const text = topoReunionCopy[language].views;

  return (
    <fieldset
      className={`segmented-control view-control${unified3D ? " is-unified-3d" : ""}`}
    >
      <legend>{text.group}</legend>
      <button
        type="button"
        aria-pressed={value === "2d"}
        onClick={() => onChange("2d")}
      >
        {text.twoD}
      </button>
      <button
        type="button"
        aria-pressed={value === "3d"}
        onClick={() => onChange("3d")}
      >
        {text.threeD}
      </button>
      {!unified3D ? (
        <button
          type="button"
          aria-pressed={value === "interactive"}
          onClick={() => onChange("interactive")}
        >
          {text.interactive}
        </button>
      ) : null}
    </fieldset>
  );
}

type SiteLabelLayout = {
  side: "left" | "right";
  shiftYRem: number;
  connectorAngleDeg: number;
  connectorWidthRem?: number;
  labelOffsetRem?: number;
  lines?: readonly string[];
  widthRem?: number;
};

const SITE_LABEL_LAYOUT: Record<string, SiteLabelLayout> = {
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
} as const;

function SitePicker({
  activeSlug,
  hasSiteRoute,
  onSelect,
  onOpenOverview,
  language,
}: {
  activeSlug: string;
  hasSiteRoute: boolean;
  onSelect: (slug: string) => void;
  onOpenOverview: () => void;
  language: Language;
}) {
  const text = topoReunionCopy[language].picker;

  return (
    <aside className="site-picker" aria-label={text.chooseDiveSite}>
      <label className="site-picker-select">
        <span>{text.sites}</span>
        <select
          aria-label={text.chooseSite}
          value={activeSlug}
          onChange={(event) => onSelect(event.target.value)}
        >
          {mapManifest.sites.map((site) => (
            <option key={site.slug} value={site.slug}>
              {site.displayName}
            </option>
          ))}
        </select>
      </label>

      <div className="site-picker-maps">
        <header className="site-picker-heading">
          <h2>{text.sites}</h2>
          <p>{text.instruction}</p>
        </header>

        <div className="site-picker-map">
          <img
            src={mapManifest.westCoastLocator.src}
            width={mapManifest.westCoastLocator.width}
            height={mapManifest.westCoastLocator.height}
            alt={text.westCoastAlt}
          />
          <div
            className="site-picker-north"
            role="img"
            aria-label={text.north}
          >
            <span aria-hidden="true">↑</span>
            <strong>N</strong>
          </div>

          {mapManifest.sites.map((site) => {
            const selected = activeSlug === site.slug;
            const layout = SITE_LABEL_LAYOUT[site.slug] ?? {
              side: "right",
              shiftYRem: 0,
              connectorAngleDeg: 0,
            };
            const style = {
              "--site-x": `${site.westCoastLocatorPosition.xPercent}%`,
              "--site-y": `${site.westCoastLocatorPosition.yPercent}%`,
              "--label-shift-y": `${layout.shiftYRem}rem`,
              "--label-width": layout.widthRem
                ? `${layout.widthRem}rem`
                : undefined,
              "--label-offset": `${layout.labelOffsetRem ?? 2.3}rem`,
              "--connector-angle": `${layout.connectorAngleDeg}deg`,
              "--connector-width": `${layout.connectorWidthRem ?? 1}rem`,
            } as CSSProperties;

            return (
              <a
                key={site.slug}
                className={`site-map-marker label-${layout.side}`}
                style={style}
                aria-current={hasSiteRoute && selected ? "page" : undefined}
                data-selected={selected}
                aria-label={`${text.showSite} ${site.displayName}`}
                href={localizedSitePath(language, site.slug)}
                onClick={(event) => {
                  if (
                    event.button !== 0 ||
                    event.metaKey ||
                    event.ctrlKey ||
                    event.shiftKey ||
                    event.altKey
                  ) {
                    return;
                  }
                  event.preventDefault();
                  onSelect(site.slug);
                }}
              >
                <span className="site-map-marker-dot" aria-hidden="true" />
                <span className="site-map-marker-line" aria-hidden="true" />
                <span
                  className={`site-map-marker-label${layout.lines ? " is-multiline" : ""}`}
                >
                  {layout.lines
                    ? layout.lines.map((line) => (
                        <span key={line}>{line}</span>
                      ))
                    : site.displayName}
                </span>
              </a>
            );
          })}

          <div
            className="site-picker-scale"
            role="img"
            aria-label={text.fiveKilometreScale}
          >
            <span aria-hidden="true" />
            <strong>5 km</strong>
          </div>
        </div>

        <button
          type="button"
          className="reunion-overview"
          aria-label={text.openIslandMap}
          onClick={onOpenOverview}
        >
          <div className="reunion-overview-map">
            <img
              src={mapManifest.reunionOverview.src}
              width={mapManifest.reunionOverview.width}
              height={mapManifest.reunionOverview.height}
              alt={text.islandOverviewAlt}
            />
            <span className="reunion-overview-extent" aria-hidden="true" />
          </div>
        </button>
      </div>
    </aside>
  );
}

export function TopoReunionExperience({
  language: initialLanguage,
  theme,
  initialSlug,
}: {
  language: Language;
  theme: Theme;
  initialSlug?: string;
}) {
  const resolvedInitialSite =
    mapManifest.sites.find((site) => site.slug === initialSlug) ?? initialSite;
  const [language, setLanguage] = useState(initialLanguage);
  const [activeSlug, setActiveSlug] = useState(
    () => resolvedInitialSite.slug,
  );
  const [hasSiteRoute, setHasSiteRoute] = useState(
    () => initialSlug !== undefined,
  );
  const [surfaceStyle, setSurfaceStyle] =
    useState<SurfaceStyle>("orthophoto");
  const [viewMode, setViewMode] = useState<ViewMode>("3d");
  const [unified3DRendererState, setUnified3DRendererState] =
    useState<Unified3DRendererState>("loading");
  const [unified3DAttempt, setUnified3DAttempt] = useState(0);
  const text = topoReunionCopy[language];
  const dialogRef = useRef<HTMLDialogElement>(null);
  const overviewDialogRef = useRef<HTMLDialogElement>(null);

  const activeSite =
    mapManifest.sites.find((site) => site.slug === activeSlug) ?? initialSite;
  const usesUnified3D = true;
  const pageSeoText = regionalSeoText(language);
  const pageTitle = pageSeoText.title;
  const pageDescription = pageSeoText.description;

  useEffect(() => {
    document.documentElement.setAttribute("lang", language);
    document.querySelector("title")?.replaceChildren(pageTitle);
    document
      .querySelector('meta[name="description"]')
      ?.setAttribute("content", pageDescription);
  }, [language, pageDescription, pageTitle]);

  useEffect(() => {
    function restoreRouteFromHistory() {
      const route = parseTopoRoute(window.location.pathname);
      if (!route) {
        return;
      }

      setLanguage(route.language);
      if (route.kind === "overview") {
        setActiveSlug(initialSite.slug);
        setHasSiteRoute(false);
        setUnified3DRendererState("loading");
        setUnified3DAttempt(0);
        return;
      }

      if (mapManifest.sites.some((site) => site.slug === route.slug)) {
        setActiveSlug(route.slug);
        setHasSiteRoute(true);
        setUnified3DRendererState("loading");
        setUnified3DAttempt((current) => current + 1);
        setViewMode((current) =>
          current === "interactive" ? "3d" : current,
        );
      }
    }

    window.addEventListener("popstate", restoreRouteFromHistory);
    return () =>
      window.removeEventListener("popstate", restoreRouteFromHistory);
  }, []);

  const markUnifiedRendererReady = useCallback(() => {
    setUnified3DRendererState("ready");
  }, []);

  const markUnifiedRendererError = useCallback(() => {
    setUnified3DRendererState("error");
  }, []);

  const restoreUnifiedRenderer = useCallback(() => {
    setUnified3DRendererState("loading");
    setUnified3DAttempt((current) => current + 1);
  }, []);

  function selectSite(slug: string) {
    if (!mapManifest.sites.some((site) => site.slug === slug)) {
      return;
    }

    const pathname = localizedSitePath(language, slug);
    const nextUrl =
      `${pathname}${window.location.search}${window.location.hash}`;
    const currentUrl =
      `${window.location.pathname}${window.location.search}` +
      `${window.location.hash}`;

    if (nextUrl !== currentUrl) {
      window.history.pushState(window.history.state, "", nextUrl);
    }
    if (slug !== activeSlug) {
      setUnified3DRendererState("loading");
      setUnified3DAttempt(0);
    }
    setActiveSlug(slug);
    setHasSiteRoute(true);
    setViewMode((current) =>
      current === "interactive" ? "3d" : current,
    );
  }

  function changeViewMode(nextView: ViewMode) {
    const resolvedView =
      usesUnified3D && nextView === "interactive"
        ? "3d"
        : nextView;
    setViewMode(resolvedView);
    if (resolvedView !== "3d") {
      setUnified3DRendererState("loading");
      setUnified3DAttempt(0);
    }
  }

  function changeLanguage(nextLanguage: Language) {
    const pathname = hasSiteRoute
      ? localizedSitePath(nextLanguage, activeSlug)
      : languagePath(nextLanguage);
    const nextUrl = `${pathname}${window.location.search}`;

    window.history.replaceState(window.history.state, "", nextUrl);
    setLanguage(nextLanguage);
  }

  const staticView: MapView = viewMode === "2d" ? "2d" : "3d";
  const mapAsset =
    usesUnified3D && staticView === "3d"
      ? dynamicCaptureAsset(activeSite.slug, surfaceStyle)
      : selectedMap(activeSite, staticView, surfaceStyle);
  const mapLargest = mapAsset.variants.at(-1) ?? mapAsset.variants[0];
  const planche = selectedPlanche(activeSite, surfaceStyle);
  const surfaceText = text.surfaces[surfaceStyle];

  function openMapDialog() {
    if (viewMode !== "interactive") dialogRef.current?.showModal();
  }

  function closeOnBackdrop(event: React.MouseEvent<HTMLDialogElement>) {
    if (event.target === dialogRef.current) dialogRef.current.close();
  }

  function closeOverviewOnBackdrop(
    event: React.MouseEvent<HTMLDialogElement>,
  ) {
    if (event.target === overviewDialogRef.current) {
      overviewDialogRef.current.close();
    }
  }

  const mapAlt =
    staticView === "2d"
      ? `${text.map.twoDAltStart} ${activeSite.displayName}, ${text.map.twoDAltMiddle} ${surfaceText.description}, ${text.map.depthsShownTo} −${activeSite.planMaxDepthM} m.`
      : `${text.map.threeDAltStart} ${activeSite.displayName}, ${text.map.threeDAltMiddle} ${surfaceText.description}${text.map.threeDAltEnd}`;
  const mapDownloadLabel =
    language === "fr"
      ? `${staticView === "2d" ? text.map.downloadTwoD : text.map.downloadThreeD} de ${activeSite.displayName}, avec ${surfaceText.description}`
      : `${staticView === "2d" ? text.map.downloadTwoD : text.map.downloadThreeD} of ${activeSite.displayName}, with ${surfaceText.description}`;
  const platePreviewAlt =
    language === "fr"
      ? `${text.plate.previewAlt} ${activeSite.displayName}, avec ${surfaceText.description}.`
      : `${text.plate.previewAlt} ${activeSite.displayName}, with ${surfaceText.description}.`;
  const showsRegularInteractive =
    viewMode === "interactive" && !usesUnified3D;
  const mountsUnifiedTerrain = usesUnified3D && viewMode === "3d";
  const showsUnifiedTerrain =
    mountsUnifiedTerrain && unified3DRendererState === "ready";
  const reservesInteractionHelp =
    showsRegularInteractive || (usesUnified3D && viewMode === "3d");
  const showsInteractionHelp =
    showsRegularInteractive || showsUnifiedTerrain;
  const mapDownload = (
    <a
      className={`map-download${mountsUnifiedTerrain ? " is-icon-only" : ""}`}
      data-testid="map-download"
      href={mapAsset.download.src}
      download={mapAsset.download.filename}
      aria-label={mapDownloadLabel}
      title={mountsUnifiedTerrain ? mapDownloadLabel : undefined}
    >
      <span className="map-download-arrow" aria-hidden="true">
        ↓
      </span>
      <span className="map-download-label">{text.map.download}</span>
    </a>
  );

  return (
    <>
      <header className="masthead" id="top">
        <div className="masthead-inner">
          <a
            className="brand"
            href={`/${language}`}
            aria-label={text.header.homeLabel}
          >
            <span className="brand-home-cue" aria-hidden="true">
              ←
            </span>
            <span className="brand-mark" aria-hidden="true" />
            <span className="brand-wordmark">{text.header.brand}</span>
          </a>
          <div className="masthead-actions">
            <nav aria-label={text.header.navigationLabel}>
              <a href="#topo-reunion">{text.header.explore}</a>
              <a href="#sources">{text.header.methodSources}</a>
              <a href="#contact">{text.header.contact}</a>
              <a
                className="external-link"
                href="https://github.com/mfoll/divetopo"
                target="_blank"
                rel="noreferrer"
                aria-label={text.header.githubNewWindow}
              >
                <span>GitHub</span>
                <span className="external-link-icon" aria-hidden="true" />
              </a>
            </nav>
            <PreferenceControls
              language={language}
              theme={theme}
              onLanguageChange={changeLanguage}
            />
          </div>
        </div>
      </header>

      <InstallPrompt copy={text.install} />

      <main>
        <section
          className="topo-reunion-section"
          id="topo-reunion"
          aria-labelledby="topo-reunion-title"
        >
          <div className="topo-reunion-intro">
            <h1 id="topo-reunion-title">{text.topoReunionTitle}</h1>
          </div>

          <div className="topo-reunion-workspace">
            <SitePicker
              activeSlug={activeSlug}
              hasSiteRoute={hasSiteRoute}
              onSelect={selectSite}
              onOpenOverview={() => overviewDialogRef.current?.showModal()}
              language={language}
            />

            <article
              className="topo-reunion-main"
              id="topo-reunion-panel"
              aria-labelledby={`active-site-title-${activeSite.slug}`}
            >
              <div className="viewer-head">
                <header className="active-site-heading">
                  <div>
                    <h2 id={`active-site-title-${activeSite.slug}`}>
                      {activeSite.displayName}
                    </h2>
                    <p>
                      <span>
                        {activeSite.location.city}, {text.islandName}
                      </span>
                      <span aria-hidden="true">·</span>
                      <span>{gpsLabel(activeSite.location, language)}</span>
                    </p>
                  </div>
                  <a
                    href={googleMapsUrl(activeSite.location)}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {text.activeSite.googleMaps}
                  </a>
                </header>

                <div
                  className={`viewer-toolbar${usesUnified3D ? " is-unified-3d" : ""}`}
                >
                  <ViewToggle
                    value={viewMode}
                    onChange={changeViewMode}
                    language={language}
                    unified3D={usesUnified3D}
                  />
                  <SurfaceToggle
                    value={surfaceStyle}
                    onChange={setSurfaceStyle}
                    language={language}
                  />
                </div>
              </div>

              <div
                className={`viewer-frame${showsRegularInteractive || showsUnifiedTerrain ? " is-interactive" : ""}${mountsUnifiedTerrain ? " has-unified-3d" : ""}`}
                data-testid="topo-reunion-viewer"
              >
                {showsRegularInteractive ? (
                  <Suspense
                    fallback={
                      <div className="terrain-loading" role="status">
                        {text.map.preparingTerrain}
                      </div>
                    }
                  >
                    <TerrainViewer
                      key={activeSite.slug}
                      slug={activeSite.slug}
                      siteName={activeSite.displayName}
                      style={surfaceStyle}
                      language={language}
                      compactAttributions={
                        activeSite.compactAttributions ??
                        REUNION_COMPACT_ATTRIBUTIONS
                      }
                    />
                  </Suspense>
                ) : (
                  <>
                    <button
                      type="button"
                      className={`map-open${usesUnified3D && viewMode === "3d" ? " unified-3d-poster" : ""}`}
                      onClick={openMapDialog}
                      aria-label={`${text.map.openMap} ${activeSite.displayName}`}
                    >
                      {usesUnified3D && staticView === "3d" ? (
                        <picture
                          key={`${activeSite.slug}-${viewMode}-${surfaceStyle}`}
                        >
                          <source
                            media="(max-width: 560px)"
                            srcSet={
                              dynamicMobileCapture(
                                activeSite.slug,
                                surfaceStyle,
                              ).src
                            }
                          />
                          <img
                            src={mapLargest.src}
                            srcSet={assetSrcSet(mapAsset.variants)}
                            sizes="(max-width: 980px) 100vw, 68vw"
                            width={mapLargest.width}
                            height={mapLargest.height}
                            alt={mapAlt}
                            fetchPriority="high"
                          />
                        </picture>
                      ) : (
                        <img
                          key={`${activeSite.slug}-${viewMode}-${surfaceStyle}`}
                          src={mapLargest.src}
                          srcSet={assetSrcSet(mapAsset.variants)}
                          sizes="(max-width: 980px) 100vw, 68vw"
                          width={mapLargest.width}
                          height={mapLargest.height}
                          alt={mapAlt}
                          fetchPriority="high"
                        />
                      )}
                    </button>
                    {!showsUnifiedTerrain ? mapDownload : null}
                  </>
                )}
                {mountsUnifiedTerrain ? (
                  <div
                    className={`unified-3d-layer${showsUnifiedTerrain ? " is-rendered" : ""}`}
                    data-testid="unified-3d-layer"
                  >
                    <Suspense fallback={null}>
                      <TerrainViewer
                        key={`${activeSite.slug}-unified-${unified3DAttempt}`}
                        slug={activeSite.slug}
                        siteName={activeSite.displayName}
                        style={surfaceStyle}
                        language={language}
                        vectorIsobathsPath={`/terrain/${activeSite.slug}/isobaths-vector.json`}
                        initialZoom={
                          activeSite.interactiveInitialView?.zoom ??
                          (activeSite.slug === "cap-la-houssaye" ? 1.12 : 1)
                        }
                        initialCenterOffsetEastM={
                          activeSite.interactiveInitialView
                            ?.centerOffsetEastM ??
                          (activeSite.slug === "cap-la-houssaye" ? -12 : 0)
                        }
                        initialCenterOffsetSouthM={
                          activeSite.interactiveInitialView
                            ?.centerOffsetSouthM ??
                          (activeSite.slug === "cap-la-houssaye" ? 12 : 0)
                        }
                        onReady={markUnifiedRendererReady}
                        onError={markUnifiedRendererError}
                        onContextRestored={restoreUnifiedRenderer}
                        compactAttributions={
                          activeSite.compactAttributions ??
                          REUNION_COMPACT_ATTRIBUTIONS
                        }
                        downloadHref={mapAsset.download.src}
                        downloadFilename={mapAsset.download.filename}
                        downloadLabel={mapDownloadLabel}
                      />
                    </Suspense>
                  </div>
                ) : null}
              </div>

              {reservesInteractionHelp ? (
                <div
                  className={`viewer-meta${showsInteractionHelp ? "" : " is-placeholder"}`}
                  aria-hidden={!showsInteractionHelp}
                >
                  <span>{text.map.interactionHelp}</span>
                </div>
              ) : null}

              <div className="planche-download">
                <img
                  key={`${activeSite.slug}-planche-${surfaceStyle}`}
                  src={planche.preview.src}
                  width={planche.preview.width}
                  height={planche.preview.height}
                  loading="lazy"
                  alt={platePreviewAlt}
                />
                <div>
                  <strong>{text.plate.printable}</strong>
                  <span>
                    {activeSite.displayName} · {surfaceText.label}
                  </span>
                </div>
                <a
                  href={planche.download.src}
                  download={planche.download.filename}
                >
                  {text.plate.download}
                </a>
              </div>
            </article>
          </div>
        </section>

        <section
          className="sources-section"
          id="sources"
          aria-labelledby="sources-title"
        >
          <div className="sources-inner">
          <div className="sources-heading">
            <h2 id="sources-title">{text.sources.title}</h2>
            <p>{text.sources.lead}</p>
          </div>

          <div className="source-cards">
            {text.sources.cards.map((source, index) => (
              <article key={source.title}>
                <span className="source-number">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <h3>{source.title}</h3>
                <p>{source.description}</p>
                <div className="source-links">
                  {source.links.map((link) => (
                    <a
                      key={link.href}
                      href={link.href}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {link.label}
                    </a>
                  ))}
                </div>
              </article>
            ))}
          </div>

          <div className="method-panel">
            <div>
              <span className="method-label">{text.sources.methodLabel}</span>
              <h3>{text.sources.methodTitle}</h3>
              <p className="method-ai-disclosure">
                {text.sources.aiDisclosure}
              </p>
            </div>
            <ul>
              {text.sources.methodSteps.map((step) => (
                <li key={step.title}>
                  <strong>{step.title}</strong>
                  <span>{step.description}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="project-notes">
            <article>
              <h3>{text.sources.creditsTitle}</h3>
              <p>
                {text.sources.mapsAndVisualisations} ©{" "}
                {initialSite.copyrightYear}{" "}
                {initialSite.plateAuthor}.
              </p>
              <a
                href={`https://creativecommons.org/licenses/by-nc-sa/4.0/deed.${language}`}
                target="_blank"
                rel="noreferrer"
              >
                {initialSite.mapLicense}
              </a>
            </article>
            <article>
              <h3>{text.sources.sourceCodeTitle}</h3>
              <p>{text.sources.sourceCodeText}</p>
              <a
                href="https://github.com/mfoll/divetopo"
                target="_blank"
                rel="noreferrer"
              >
                {text.sources.viewRepository}
              </a>
            </article>
            <article>
              <h3>{text.sources.safetyTitle}</h3>
              <p>{text.sources.safetyText}</p>
            </article>
          </div>
          </div>
        </section>

        <section
          className="contact-section"
          id="contact"
          aria-labelledby="contact-title"
        >
          <div className="contact-inner">
            <h2 id="contact-title">{text.contact.title}</h2>
            <p>
              {text.contact.question}
              <br />
              {text.contact.action}{" "}
              <a href="mailto:contact@divetopo.com">
                contact@divetopo.com
              </a>
              .
            </p>
          </div>
        </section>
      </main>

      <footer className="site-footer">
        <a className="brand" href="#top">
          <span className="brand-mark" aria-hidden="true" />
          <span className="brand-wordmark">{text.header.brand}</span>
        </a>
        <div className="site-footer-meta">
          <span className="site-footer-access">
            {text.footer.freeAndAdFree} · {text.footer.codeLicense}{" "}
            <a
              href="https://opensource.org/license/mit"
              target="_blank"
              rel="noreferrer"
            >
              {text.footer.mit}
            </a>{" "}
            · {text.footer.mapsLicense}{" "}
            <a
              href={`https://creativecommons.org/licenses/by-nc-sa/4.0/deed.${language}`}
              target="_blank"
              rel="noreferrer"
            >
              CC BY-NC-SA 4.0
            </a>
          </span>
          <span>
            {text.footer.maps} © {initialSite.copyrightYear}{" "}
            {initialSite.plateAuthor} · {initialSite.mapLicense}
          </span>
          <span>{text.footer.analytics}</span>
        </div>
        <a href="#top">{text.footer.backToTop}</a>
      </footer>

      <dialog
        className="map-dialog"
        ref={dialogRef}
        onClick={closeOnBackdrop}
        aria-label={`${text.dialogs.largeMap} ${activeSite.displayName}`}
      >
        <button
          type="button"
          className="dialog-close"
          onClick={() => dialogRef.current?.close()}
        >
          {text.dialogs.close}
        </button>
        <img
          src={mapLargest.src}
          width={mapLargest.width}
          height={mapLargest.height}
          loading="lazy"
          alt={mapAlt}
        />
      </dialog>

      <dialog
        className="map-dialog overview-dialog"
        ref={overviewDialogRef}
        onClick={closeOverviewOnBackdrop}
        aria-label={text.dialogs.largeIslandMap}
      >
        <button
          type="button"
          className="dialog-close"
          onClick={() => overviewDialogRef.current?.close()}
        >
          {text.dialogs.close}
        </button>
        <div className="overview-dialog-map">
          <img
            src={mapManifest.reunionOverview.src}
            width={mapManifest.reunionOverview.width}
            height={mapManifest.reunionOverview.height}
            loading="lazy"
            alt={text.dialogs.islandOverviewAlt}
          />
          <span className="reunion-overview-extent" aria-hidden="true" />
        </div>
      </dialog>
    </>
  );
}
