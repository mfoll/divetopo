"use client";

/* eslint-disable @next/next/no-img-element -- responsive map derivatives are generated locally and swapped in place */

import {
  lazy,
  Suspense,
  useEffect,
  useRef,
  useState,
  type CSSProperties,
} from "react";
import { topoReunionCopy } from "../content/copy";
import type { Language, Theme } from "../content/preferences";
import mapManifestJson from "../public/maps/manifest.json";
import PreferenceControls from "./PreferenceControls";

type SurfaceStyle = "topographic" | "orthophoto";
type MapView = "2d" | "3d";
type ViewMode = MapView | "interactive";

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
  maps: MapAsset[];
  planches: PlancheAsset[];
};

type MapManifest = {
  reunionOverview: AssetVariant;
  westCoastLocator: AssetVariant;
  sites: TopoReunionAssetSite[];
};

const TerrainViewer = lazy(() => import("./TerrainViewer"));
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
}: {
  value: ViewMode;
  onChange: (view: ViewMode) => void;
  language: Language;
}) {
  const text = topoReunionCopy[language].views;

  return (
    <fieldset className="segmented-control view-control">
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
      <button
        type="button"
        aria-pressed={value === "interactive"}
        onClick={() => onChange("interactive")}
      >
        {text.interactive}
      </button>
    </fieldset>
  );
}

const SITE_LABEL_LAYOUT = {
  "cap-la-houssaye": "right-up",
  "boucan-canot": "left-up",
  "cap-homard": "right-down",
  "passe-hermitage": "right",
  "pont-rouge-la-tortue": "left",
  "plage-cimetiere-saint-leu": "left-up",
  "pointe-au-sel-sec-jaune": "left",
} as const;

function SitePicker({
  activeSlug,
  onSelect,
  onOpenOverview,
  language,
}: {
  activeSlug: string;
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

          {mapManifest.sites.map((site, index) => {
            const selected = activeSlug === site.slug;
            const knownLayout =
              SITE_LABEL_LAYOUT[
                site.slug as keyof typeof SITE_LABEL_LAYOUT
              ];
            const layout = knownLayout ?? (index % 2 === 0 ? "right" : "left");
            const style = {
              "--site-x": `${site.westCoastLocatorPosition.xPercent}%`,
              "--site-y": `${site.westCoastLocatorPosition.yPercent}%`,
            } as CSSProperties;

            return (
              <button
                key={site.slug}
                type="button"
                className={`site-map-marker label-${layout}`}
                style={style}
                aria-pressed={selected}
                aria-label={`${text.showSite} ${site.displayName}`}
                onClick={() => onSelect(site.slug)}
              >
                <span className="site-map-marker-dot" aria-hidden="true" />
                <span className="site-map-marker-line" aria-hidden="true" />
                <span className="site-map-marker-label">
                  {site.displayName}
                </span>
              </button>
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
}: {
  language: Language;
  theme: Theme;
}) {
  const [language, setLanguage] = useState(initialLanguage);
  const [activeSlug, setActiveSlug] = useState(() => initialSite.slug);
  const [surfaceStyle, setSurfaceStyle] =
    useState<SurfaceStyle>("orthophoto");
  const [viewMode, setViewMode] = useState<ViewMode>("3d");
  const text = topoReunionCopy[language];
  const dialogRef = useRef<HTMLDialogElement>(null);
  const overviewDialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    document.documentElement.lang = language;
    document.title = text.topoReunionTitle;
    document
      .querySelector('meta[name="description"]')
      ?.setAttribute("content", text.metadataDescription);
  }, [language, text.topoReunionTitle, text.metadataDescription]);

  const activeSite =
    mapManifest.sites.find((site) => site.slug === activeSlug) ?? initialSite;
  const staticView: MapView = viewMode === "2d" ? "2d" : "3d";
  const mapAsset = selectedMap(activeSite, staticView, surfaceStyle);
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

  return (
    <>
      <header className="masthead" id="top">
        <div className="masthead-inner">
          <a
            className="brand"
            href="https://divetopo.com/"
            aria-label={text.header.homeLabel}
          >
            <span className="brand-mark" aria-hidden="true" />
            <span>{text.header.brand}</span>
          </a>
          <div className="masthead-actions">
            <nav aria-label={text.header.navigationLabel}>
              <a href="#topo-reunion">{text.header.explore}</a>
              <a href="#sources">{text.header.methodSources}</a>
              <a href="#contact">{text.header.contact}</a>
              <a
                className="external-link"
                href="https://github.com/mfoll/reunion-topobathy"
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
              onLanguageChange={setLanguage}
            />
          </div>
        </div>
      </header>

      <main>
        <section
          className="topo-reunion-section"
          id="topo-reunion"
          aria-labelledby="topo-reunion-title"
        >
          <div className="topo-reunion-intro">
            <h1 id="topo-reunion-title">{text.topoReunionTitle}</h1>
            <p>{text.topoReunionLead}</p>
          </div>

        <div className="topo-reunion-workspace">
          <SitePicker
            activeSlug={activeSlug}
            onSelect={setActiveSlug}
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

              <div className="viewer-toolbar">
                <ViewToggle
                  value={viewMode}
                  onChange={setViewMode}
                  language={language}
                />
                <SurfaceToggle
                  value={surfaceStyle}
                  onChange={setSurfaceStyle}
                  language={language}
                />
              </div>
            </div>

            <div
              className={`viewer-frame${viewMode === "interactive" ? " is-interactive" : ""}`}
              data-testid="topo-reunion-viewer"
            >
              {viewMode === "interactive" ? (
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
                  />
                </Suspense>
              ) : (
                <>
                  <button
                    type="button"
                    className="map-open"
                    onClick={openMapDialog}
                    aria-label={`${text.map.openMap} ${activeSite.displayName}`}
                  >
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
                    <span>{text.map.openLarge}</span>
                  </button>
                  <a
                    className="map-download"
                    data-testid="map-download"
                    href={mapAsset.download.src}
                    download={mapAsset.download.filename}
                    aria-label={mapDownloadLabel}
                  >
                    <span aria-hidden="true">↓</span>
                    {text.map.download}
                  </a>
                </>
              )}
            </div>

            {viewMode === "interactive" ? (
              <div className="viewer-meta">
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
                href="https://github.com/mfoll/reunion-topobathy"
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
              {text.contact.prompt}{" "}
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
          <span>{text.header.brand}</span>
        </a>
        <span>
          {text.footer.maps} © {initialSite.copyrightYear}{" "}
          {initialSite.plateAuthor} ·{" "}
          {initialSite.mapLicense}
        </span>
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
            alt={text.dialogs.islandOverviewAlt}
          />
          <span className="reunion-overview-extent" aria-hidden="true" />
        </div>
      </dialog>
    </>
  );
}
