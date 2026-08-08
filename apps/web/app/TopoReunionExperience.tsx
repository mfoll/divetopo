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
  type MouseEvent,
} from "react";
import { pacaCopy, topoReunionCopy } from "../content/copy";
import type { Language, Theme } from "../content/preferences";
import { regionCopy } from "../content/region-catalog";
import {
  languagePath,
  localizedSitePath,
  parseTopoRoute,
  releaseAssetUrl,
  regionalSeoText,
} from "../content/routing";
import {
  PACA_COMPACT_ATTRIBUTIONS,
  REUNION_COMPACT_ATTRIBUTIONS,
  pacaMapManifest,
  regionalMapManifests,
  reunionMapManifest,
  type AssetVariant,
  type MapAsset,
  type MapView,
  type RegionalAssetSite,
  type RegionalMapManifest,
  type RegionSlug,
  type SiteLocation,
  type SurfaceStyle,
} from "../content/regional";
import InstallPrompt from "./InstallPrompt";
import PreferenceControls from "./PreferenceControls";

type ViewMode = MapView | "interactive";
type Unified3DRendererState = "loading" | "ready" | "error";

const TerrainViewer = lazy(() => import("./TerrainViewer"));
type RegionalCopy = typeof topoReunionCopy;

export type RegionExperienceConfig = {
  region: RegionSlug;
  manifest: RegionalMapManifest;
  copy: RegionalCopy;
  compactAttributions: Record<SurfaceStyle, string>;
  sectionId: string;
  titleId: string;
  viewerTestId: string;
  pickerScaleLabel: string;
  pickerScaleWidthPercent: number;
};

export const REUNION_EXPERIENCE_CONFIG: RegionExperienceConfig = {
  region: "reunion",
  manifest: reunionMapManifest,
  copy: topoReunionCopy,
  compactAttributions: REUNION_COMPACT_ATTRIBUTIONS,
  sectionId: "topo-reunion",
  titleId: "topo-reunion-title",
  viewerTestId: "topo-reunion-viewer",
  pickerScaleLabel: "5 km",
  pickerScaleWidthPercent: 29.4118,
};

export const PACA_EXPERIENCE_CONFIG: RegionExperienceConfig = {
  region: "paca",
  manifest: pacaMapManifest,
  copy: pacaCopy,
  compactAttributions: PACA_COMPACT_ATTRIBUTIONS,
  sectionId: "topo-paca",
  titleId: "topo-paca-title",
  viewerTestId: "topo-paca-viewer",
  pickerScaleLabel: "20 km",
  pickerScaleWidthPercent: 18.2769,
};

export function regionalExperienceConfig(
  region: RegionSlug,
): RegionExperienceConfig {
  if (region === "reunion") return REUNION_EXPERIENCE_CONFIG;
  if (region === "paca") return PACA_EXPERIENCE_CONFIG;
  return {
    region,
    manifest: regionalMapManifests[region],
    copy: regionCopy(region) as RegionalCopy,
    compactAttributions: PACA_COMPACT_ATTRIBUTIONS,
    sectionId: `topo-${region}`,
    titleId: `topo-${region}-title`,
    viewerTestId: `topo-${region}-viewer`,
    pickerScaleLabel: "10 km",
    pickerScaleWidthPercent: 24,
  };
}

function dynamicCaptureAsset(
  site: RegionalAssetSite,
  style: SurfaceStyle,
): MapAsset {
  const base = site.assetBasePath
    ? `${site.assetBasePath}/maps`
    : `/maps/${site.slug}`;
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
      filename: `${site.slug}-3d-dynamique-${style}.jpg`,
    },
  };
}

function dynamicMobileCapture(
  site: RegionalAssetSite,
  style: SurfaceStyle,
): AssetVariant {
  const base = site.assetBasePath
    ? `${site.assetBasePath}/maps`
    : `/maps/${site.slug}`;
  return {
    src: `${base}/3d-dynamic-${style}-mobile-960.webp`,
    width: 960,
    height: 662,
  };
}

function assetSrcSet(variants: AssetVariant[]) {
  return variants.map((variant) => `${variant.src} ${variant.width}w`).join(", ");
}

function selectedMap(
  site: RegionalAssetSite,
  view: MapView,
  style: SurfaceStyle,
) {
  const asset = site.maps.find(
    (candidate) => candidate.view === view && candidate.style === style,
  );
  if (!asset) throw new Error(`Missing ${view}/${style} map for ${site.slug}`);
  return asset;
}

function selectedPlanche(site: RegionalAssetSite, style: SurfaceStyle) {
  const asset = site.planches?.find(
    (candidate) => candidate.style === style,
  );
  return asset
    ? {
        ...asset,
        download: {
          ...asset.download,
          src: releaseAssetUrl(asset.download.filename),
        },
      }
    : undefined;
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
  copy,
}: {
  value: SurfaceStyle;
  onChange: (style: SurfaceStyle) => void;
  language: Language;
  copy: RegionalCopy;
}) {
  const text = copy[language];

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
  copy,
  unified3D = false,
}: {
  value: ViewMode;
  onChange: (view: ViewMode) => void;
  language: Language;
  copy: RegionalCopy;
  unified3D?: boolean;
}) {
  const text = copy[language].views;

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

function SitePicker({
  config,
  activeSlug,
  hasSiteRoute,
  onSelect,
  language,
}: {
  config: RegionExperienceConfig;
  activeSlug: string;
  hasSiteRoute: boolean;
  onSelect: (slug: string) => void;
  language: Language;
}) {
  const {
    manifest,
    copy,
    region,
    pickerScaleLabel,
    pickerScaleWidthPercent,
  } = config;
  const text = copy[language].picker;

  return (
    <aside
      className={
        region !== "reunion" ? "site-picker is-paca" : "site-picker"
      }
      aria-label={text.chooseDiveSite}
    >
      <label className="site-picker-select">
        <span>{text.sites}</span>
        <select
          aria-label={text.chooseSite}
          value={activeSlug}
          onChange={(event) => onSelect(event.target.value)}
        >
          {manifest.sites.map((site) => (
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

        <div className={`site-picker-map${region !== "reunion" ? " is-paca" : ""}`}>
          <img
            src={manifest.westCoastLocator.src}
            width={manifest.westCoastLocator.width}
            height={manifest.westCoastLocator.height}
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

          {manifest.sites.map((site) => {
            const selected = activeSlug === site.slug;
            const layout = site.siteLabelLayout;
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
                href={localizedSitePath(language, site.slug, region)}
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
            aria-label={text.mapScale}
            style={{
              "--site-picker-scale-width": `${pickerScaleWidthPercent}%`,
            } as CSSProperties}
          >
            <span aria-hidden="true" />
            <strong>{pickerScaleLabel}</strong>
          </div>
        </div>

        <div
          className={`reunion-overview${region !== "reunion" ? " is-paca" : ""}`}
          role="img"
          aria-label={text.overviewAlt}
        >
          <div className="reunion-overview-map">
            <img
              src={manifest.reunionOverview.src}
              width={manifest.reunionOverview.width}
              height={manifest.reunionOverview.height}
              alt=""
            />
            {region === "reunion" && (
              <span className="reunion-overview-extent" aria-hidden="true" />
            )}
          </div>
        </div>
      </div>
    </aside>
  );
}

export type RegionalExperienceProps = {
  language: Language;
  theme: Theme;
  initialSlug?: string;
  config: RegionExperienceConfig;
};

export function TopoRegionExperience({
  language: initialLanguage,
  theme,
  initialSlug,
  config,
}: RegionalExperienceProps) {
  const { manifest, copy, region } = config;
  const initialSite = manifest.sites[0];
  if (!initialSite) {
    throw new Error(`${region} requires at least one published site`);
  }

  const resolvedInitialSite =
    manifest.sites.find((site) => site.slug === initialSlug) ?? initialSite;
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
  const text = copy[language];
  const dialogRef = useRef<HTMLDialogElement>(null);

  const activeSite =
    manifest.sites.find((site) => site.slug === activeSlug) ?? initialSite;
  const usesUnified3D = true;
  const pageSeoText = regionalSeoText(language, region);
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
      const route = parseTopoRoute(window.location.pathname, region);
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

      if (manifest.sites.some((site) => site.slug === route.slug)) {
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
  }, [initialSite.slug, manifest.sites, region]);

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
    if (!manifest.sites.some((site) => site.slug === slug)) {
      return;
    }

    const pathname = localizedSitePath(language, slug, region);
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
      ? localizedSitePath(nextLanguage, activeSlug, region)
      : languagePath(nextLanguage, region);
    const nextUrl = `${pathname}${window.location.search}`;

    window.history.replaceState(window.history.state, "", nextUrl);
    setLanguage(nextLanguage);
  }

  const staticView: MapView = viewMode === "2d" ? "2d" : "3d";
  const mapAsset =
    usesUnified3D && staticView === "3d"
      ? dynamicCaptureAsset(activeSite, surfaceStyle)
      : selectedMap(activeSite, staticView, surfaceStyle);
  const mapLargest = mapAsset.variants.at(-1) ?? mapAsset.variants[0];
  const planche = selectedPlanche(activeSite, surfaceStyle);
  const surfaceText = text.surfaces[surfaceStyle];

  function openMapDialog() {
    if (viewMode !== "interactive") dialogRef.current?.showModal();
  }

  function closeOnBackdrop(event: MouseEvent<HTMLDialogElement>) {
    if (event.target === dialogRef.current) dialogRef.current.close();
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
              <a href={`#${config.sectionId}`}>{text.header.explore}</a>
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
          id={config.sectionId}
          aria-labelledby={config.titleId}
        >
          <div className="topo-reunion-intro">
            <h1 id={config.titleId}>{text.topoReunionTitle}</h1>
          </div>

          <div className="topo-reunion-workspace">
            <SitePicker
              config={config}
              activeSlug={activeSlug}
              hasSiteRoute={hasSiteRoute}
              onSelect={selectSite}
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
                      <span>{activeSite.location.city}</span>
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
                    copy={copy}
                    unified3D={usesUnified3D}
                  />
                  <SurfaceToggle
                    value={surfaceStyle}
                    onChange={setSurfaceStyle}
                    language={language}
                    copy={copy}
                  />
                </div>
              </div>

              <div
                className={`viewer-frame${showsRegularInteractive || showsUnifiedTerrain ? " is-interactive" : ""}${mountsUnifiedTerrain ? " has-unified-3d" : ""}`}
                data-testid={config.viewerTestId}
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
                        config.compactAttributions
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
                                activeSite,
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
                        initialOrbitAzimuthDeg={
                          activeSite.interactiveInitialView?.orbitAzimuthDeg
                        }
                        initialCameraElevationDeg={
                          activeSite.interactiveInitialView
                            ?.cameraElevationDeg
                        }
                        initialPanRightM={
                          activeSite.interactiveInitialView?.panRightM
                        }
                        initialPanUpM={
                          activeSite.interactiveInitialView?.panUpM
                        }
                        initialCenterOffsetEastM={
                          activeSite.interactiveInitialView
                            ?.centerOffsetEastM ??
                          (activeSite.slug === "cap-la-houssaye" ? -12 : 0)
                        }
                        initialCenterOffsetSouthM={
                          activeSite.interactiveInitialView
                            ?.centerOffsetSouthM ??
                          (region === "reunion" && activeSite.slug === "cap-la-houssaye"
                            ? 12
                            : 0)
                        }
                        isobathLabelFocusXNdc={
                          activeSite.interactiveInitialView
                            ?.isobathLabelFocusXNdc
                        }
                        onReady={markUnifiedRendererReady}
                        onError={markUnifiedRendererError}
                        onContextRestored={restoreUnifiedRenderer}
                        compactAttributions={
                          activeSite.compactAttributions ??
                          config.compactAttributions
                        }
                        downloadHref={mapAsset.download.src}
                        downloadFilename={mapAsset.download.filename}
                        downloadLabel={mapDownloadLabel}
                      />
                    </Suspense>
                  </div>
                ) : null}
              </div>

              <div
                className={`viewer-meta${showsInteractionHelp ? "" : " is-placeholder"}`}
                aria-hidden={!showsInteractionHelp}
              >
                <span>{text.map.interactionHelp}</span>
              </div>

              {planche ? (
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
              ) : null}
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

    </>
  );
}

export function TopoReunionExperience({
  language,
  theme,
  initialSlug,
}: Omit<RegionalExperienceProps, "config">) {
  return (
    <TopoRegionExperience
      config={REUNION_EXPERIENCE_CONFIG}
      language={language}
      theme={theme}
      initialSlug={initialSlug}
    />
  );
}
