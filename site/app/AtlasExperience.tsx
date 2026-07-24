"use client";

/* eslint-disable @next/next/no-img-element -- responsive map derivatives are generated locally and swapped in place */

import {
  lazy,
  Suspense,
  useRef,
  useState,
  type KeyboardEvent,
} from "react";
import mapManifestJson from "../public/maps/manifest.json";

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
};

type PlancheAsset = {
  style: SurfaceStyle;
  preview: AssetVariant;
  download: AssetVariant & { filename: string };
};

type AtlasAssetSite = {
  slug: string;
  displayName: string;
  plateTitle: string;
  maxDepthM: number;
  verticalExaggeration: number;
  orthophotoCaptureDate: string;
  plateAuthor: string;
  copyrightYear: number;
  mapLicense: string;
  locator: AssetVariant;
  maps: MapAsset[];
  planches: PlancheAsset[];
};

type MapManifest = {
  sites: AtlasAssetSite[];
};

const TerrainViewer = lazy(() => import("./TerrainViewer"));
const mapManifest = mapManifestJson as MapManifest;
const initialSite = mapManifest.sites[0];

if (!initialSite) {
  throw new Error("The dive atlas requires at least one site");
}

const SOURCE_LINKS = [
  {
    label: "HYSCORES 2015",
    href: "https://doi.org/10.12770/ee059de2-2c81-46ce-88de-0fb5517046af",
  },
  { label: "Ifremer", href: "https://www.ifremer.fr/fr" },
  {
    label: "Université de Bretagne Occidentale",
    href: "https://www.univ-brest.fr/fr",
  },
  {
    label: "Office de l’eau Réunion",
    href: "https://donnees.eaureunion.fr/",
  },
  {
    label: "IGN RGE ALTI",
    href: "https://cartes.gouv.fr/rechercher-une-donnee/dataset/IGNF_RGE-ALTI",
  },
  {
    label: "IGN BD ORTHO",
    href: "https://cartes.gouv.fr/rechercher-une-donnee/dataset/IGNF_BD-ORTHO",
  },
  {
    label: "GEBCO 2024 Grid",
    href: "https://www.gebco.net/data-products-gridded-bathymetry-data/gebco2024-grid",
  },
] as const;

function assetSrcSet(variants: AssetVariant[]) {
  return variants.map((variant) => `${variant.src} ${variant.width}w`).join(", ");
}

function selectedMap(
  site: AtlasAssetSite,
  view: MapView,
  style: SurfaceStyle,
) {
  const asset = site.maps.find(
    (candidate) => candidate.view === view && candidate.style === style,
  );
  if (!asset) throw new Error(`Missing ${view}/${style} map for ${site.slug}`);
  return asset;
}

function selectedPlanche(site: AtlasAssetSite, style: SurfaceStyle) {
  const asset = site.planches.find(
    (candidate) => candidate.style === style,
  );
  if (!asset) throw new Error(`Missing ${style} planche for ${site.slug}`);
  return asset;
}

function surfaceLabel(style: SurfaceStyle) {
  return style === "orthophoto" ? "Orthophoto" : "Topographie";
}

function viewLabel(view: ViewMode) {
  if (view === "2d") return "Plan 2D";
  if (view === "3d") return "Vue 3D";
  return "3D interactive";
}

function SurfaceToggle({
  value,
  onChange,
}: {
  value: SurfaceStyle;
  onChange: (style: SurfaceStyle) => void;
}) {
  return (
    <fieldset className="segmented-control surface-control">
      <legend>Fond de carte</legend>
      <button
        type="button"
        aria-pressed={value === "orthophoto"}
        onClick={() => onChange("orthophoto")}
      >
        Orthophoto
      </button>
      <button
        type="button"
        aria-pressed={value === "topographic"}
        onClick={() => onChange("topographic")}
      >
        Topographie
      </button>
    </fieldset>
  );
}

function ViewToggle({
  value,
  onChange,
}: {
  value: ViewMode;
  onChange: (view: ViewMode) => void;
}) {
  return (
    <fieldset className="segmented-control view-control">
      <legend>Type de vue</legend>
      <button
        type="button"
        aria-pressed={value === "2d"}
        onClick={() => onChange("2d")}
      >
        Plan 2D
      </button>
      <button
        type="button"
        aria-pressed={value === "3d"}
        onClick={() => onChange("3d")}
      >
        Vue 3D
      </button>
      <button
        type="button"
        aria-pressed={value === "interactive"}
        onClick={() => onChange("interactive")}
      >
        3D interactive
      </button>
    </fieldset>
  );
}

function SiteNavigator({
  activeSlug,
  onSelect,
}: {
  activeSlug: string;
  onSelect: (slug: string) => void;
}) {
  const buttonRefs = useRef<Record<string, HTMLButtonElement | null>>({});

  function selectAndFocus(index: number) {
    const site = mapManifest.sites[index];
    if (!site) return;
    onSelect(site.slug);
    requestAnimationFrame(() => {
      const button = buttonRefs.current[site.slug];
      button?.focus();
      button?.scrollIntoView({ block: "nearest", inline: "nearest" });
    });
  }

  function handleKey(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    let nextIndex: number | null = null;
    if (event.key === "ArrowDown" || event.key === "ArrowRight") {
      nextIndex = (index + 1) % mapManifest.sites.length;
    } else if (event.key === "ArrowUp" || event.key === "ArrowLeft") {
      nextIndex =
        (index - 1 + mapManifest.sites.length) % mapManifest.sites.length;
    } else if (event.key === "Home") {
      nextIndex = 0;
    } else if (event.key === "End") {
      nextIndex = mapManifest.sites.length - 1;
    }
    if (nextIndex === null) return;
    event.preventDefault();
    selectAndFocus(nextIndex);
  }

  return (
    <aside className="site-navigator" aria-labelledby="site-navigator-title">
      <h2 id="site-navigator-title">Sites de plongée</h2>
      <label className="site-select-label">
        <span>Choisir un site</span>
        <select
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
      <div
        className="site-list"
        role="tablist"
        aria-label="Choisir un site de plongée"
        aria-orientation="vertical"
      >
        {mapManifest.sites.map((site, index) => {
          const selected = activeSlug === site.slug;
          return (
            <button
              key={site.slug}
              id={`site-tab-${site.slug}`}
              ref={(node) => {
                buttonRefs.current[site.slug] = node;
              }}
              type="button"
              role="tab"
              aria-controls="atlas-panel"
              aria-selected={selected}
              tabIndex={selected ? 0 : -1}
              onClick={() => onSelect(site.slug)}
              onKeyDown={(event) => handleKey(event, index)}
            >
              {site.displayName}
            </button>
          );
        })}
      </div>
    </aside>
  );
}

export function AtlasExperience() {
  const [activeSlug, setActiveSlug] = useState(() => initialSite.slug);
  const [surfaceStyle, setSurfaceStyle] =
    useState<SurfaceStyle>("orthophoto");
  const [viewMode, setViewMode] = useState<ViewMode>("3d");
  const dialogRef = useRef<HTMLDialogElement>(null);

  const activeSite =
    mapManifest.sites.find((site) => site.slug === activeSlug) ?? initialSite;
  const staticView: MapView = viewMode === "2d" ? "2d" : "3d";
  const mapAsset = selectedMap(activeSite, staticView, surfaceStyle);
  const mapLargest = mapAsset.variants.at(-1) ?? mapAsset.variants[0];
  const planche = selectedPlanche(activeSite, surfaceStyle);

  function openMapDialog() {
    if (viewMode !== "interactive") dialogRef.current?.showModal();
  }

  function closeOnBackdrop(event: React.MouseEvent<HTMLDialogElement>) {
    if (event.target === dialogRef.current) dialogRef.current.close();
  }

  const mapAlt =
    staticView === "2d"
      ? `Plan topo-bathymétrique 2D de ${activeSite.displayName}, nord en haut, fond ${surfaceLabel(surfaceStyle).toLowerCase()}, profondeurs affichées jusqu’à −${activeSite.maxDepthM} m.`
      : `Perspective 3D oblique de ${activeSite.displayName}, fond ${surfaceLabel(surfaceStyle).toLowerCase()}, relief vertical exagéré environ quatre fois.`;

  return (
    <main>
      <header className="masthead" id="top">
        <a className="brand" href="#atlas">
          Plongée à La Réunion
        </a>
        <nav aria-label="Navigation principale">
          <a href="#atlas">Les cartes</a>
          <a href="#sources">Méthode et crédits</a>
          <a
            href="https://github.com/mfoll/reunion-topobathy"
            target="_blank"
            rel="noreferrer"
          >
            GitHub
          </a>
        </nav>
      </header>

      <section className="atlas-section" id="atlas" aria-labelledby="atlas-title">
        <div className="atlas-intro">
          <h1 id="atlas-title">Cartes de plongée à La Réunion</h1>
          <p>Plans 2D, vues 3D et reliefs interactifs.</p>
        </div>

        <div className="atlas-workspace">
          <SiteNavigator activeSlug={activeSlug} onSelect={setActiveSlug} />

          <article
            className="atlas-main"
            id="atlas-panel"
            role="tabpanel"
            aria-labelledby={`site-tab-${activeSite.slug}`}
          >
            <div className="viewer-heading">
              <h2>{activeSite.displayName}</h2>
              <div className="viewer-toolbar">
                <ViewToggle value={viewMode} onChange={setViewMode} />
                <SurfaceToggle
                  value={surfaceStyle}
                  onChange={setSurfaceStyle}
                />
              </div>
            </div>

            <div
              className={`viewer-frame${viewMode === "interactive" ? " is-interactive" : ""}`}
              data-testid="atlas-viewer"
            >
              {viewMode === "interactive" ? (
                <Suspense
                  fallback={
                    <div className="terrain-loading" role="status">
                      Préparation du relief…
                    </div>
                  }
                >
                  <TerrainViewer
                    key={activeSite.slug}
                    slug={activeSite.slug}
                    siteName={activeSite.displayName}
                    style={surfaceStyle}
                  />
                </Suspense>
              ) : (
                <button
                  type="button"
                  className="map-open"
                  onClick={openMapDialog}
                  aria-label={`Ouvrir la carte de ${activeSite.displayName} en grand`}
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
                  <span>Ouvrir en grand</span>
                </button>
              )}
            </div>

            <div className="viewer-meta" aria-live="polite">
              <span>
                {viewLabel(viewMode)} · {surfaceLabel(surfaceStyle)}
              </span>
              {viewMode === "interactive" ? (
                <span>
                  Glisser pour tourner · Molette ou pincement pour zoomer · Clic
                  droit ou Ctrl + glisser pour déplacer
                </span>
              ) : null}
            </div>

            <div className="planche-download">
              <img
                key={`${activeSite.slug}-planche-${surfaceStyle}`}
                src={planche.preview.src}
                width={planche.preview.width}
                height={planche.preview.height}
                loading="lazy"
                alt={`Aperçu de la planche imprimable de ${activeSite.displayName}, fond ${surfaceLabel(surfaceStyle).toLowerCase()}.`}
              />
              <div>
                <strong>Planche imprimable</strong>
                <span>
                  {activeSite.displayName} · {surfaceLabel(surfaceStyle)}
                </span>
              </div>
              <a
                href={planche.download.src}
                download={planche.download.filename}
              >
                Télécharger la planche HD
              </a>
            </div>
          </article>

          <aside className="locator-panel" aria-labelledby="locator-title">
            <h2 id="locator-title">La Réunion</h2>
            <img
              key={`${activeSite.slug}-locator`}
              src={activeSite.locator.src}
              width={activeSite.locator.width}
              height={activeSite.locator.height}
              alt={`Localisation de ${activeSite.displayName} sur l’île de La Réunion.`}
            />
          </aside>
        </div>
      </section>

      <section
        className="sources-section"
        id="sources"
        aria-labelledby="sources-title"
      >
        <img
          className="sources-map"
          src="/maps/passe-hermitage/2d-orthophoto-1600.webp"
          width={1600}
          height={1107}
          loading="lazy"
          alt=""
          aria-hidden="true"
        />
        <div className="sources-inner">
          <h2 id="sources-title">Méthode, sources et licences</h2>

          <div className="method-grid">
            <article>
              <h3>Bathymétrie</h3>
              <p>HYSCORES 2015</p>
            </article>
            <article>
              <h3>Topographie</h3>
              <p>IGN RGE ALTI</p>
            </article>
            <article>
              <h3>Orthophoto</h3>
              <p>IGN BD ORTHO</p>
            </article>
            <article>
              <h3>Cartes et reliefs</h3>
              <p>Isobathes tous les 5 m · relief vertical ≈ ×4</p>
            </article>
          </div>

          <div className="information-grid">
            <article>
              <h3>Sources</h3>
              <ul className="source-links">
                {SOURCE_LINKS.map((source) => (
                  <li key={source.href}>
                    <a
                      href={source.href}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {source.label}
                    </a>
                  </li>
                ))}
              </ul>
            </article>
            <article>
              <h3>Licence</h3>
              <p>
                Cartes © {initialSite.copyrightYear} {initialSite.plateAuthor}
              </p>
              <p>
                <a
                  href="https://creativecommons.org/licenses/by-nc-sa/4.0/deed.fr"
                  target="_blank"
                  rel="noreferrer"
                >
                  {initialSite.mapLicense}
                </a>
              </p>
              <p>
                <a
                  href="https://github.com/mfoll/reunion-topobathy"
                  target="_blank"
                  rel="noreferrer"
                >
                  Code source sur GitHub
                </a>
              </p>
            </article>
            <article>
              <h3>Sécurité</h3>
              <p>
                Ces cartes ne remplacent pas les informations locales, les
                conditions de mer, les consignes des autorités ou l’avis d’un
                professionnel.
              </p>
            </article>
          </div>
        </div>
      </section>

      <footer className="site-footer">
        <a className="brand" href="#top">
          Plongée à La Réunion
        </a>
        <span>
          Cartes © {initialSite.copyrightYear} {initialSite.plateAuthor} ·{" "}
          {initialSite.mapLicense}
        </span>
        <a href="#top">Haut de page</a>
      </footer>

      <dialog
        className="map-dialog"
        ref={dialogRef}
        onClick={closeOnBackdrop}
        aria-label={`Carte de ${activeSite.displayName} en grand`}
      >
        <button
          type="button"
          className="dialog-close"
          onClick={() => dialogRef.current?.close()}
        >
          Fermer
        </button>
        <img
          src={mapLargest.src}
          width={mapLargest.width}
          height={mapLargest.height}
          alt={mapAlt}
        />
      </dialog>
    </main>
  );
}
