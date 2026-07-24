"use client";

/* eslint-disable @next/next/no-img-element -- responsive map derivatives are generated locally and swapped in place */

import {
  lazy,
  Suspense,
  useRef,
  useState,
  type CSSProperties,
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

type SiteLocation = {
  city: string;
  latitude: number;
  longitude: number;
};

type WestCoastLocatorPosition = {
  xPercent: number;
  yPercent: number;
};

type AtlasAssetSite = {
  slug: string;
  displayName: string;
  plateTitle: string;
  location: SiteLocation;
  westCoastLocatorPosition: WestCoastLocatorPosition;
  maxDepthM: number;
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
  sites: AtlasAssetSite[];
};

const TerrainViewer = lazy(() => import("./TerrainViewer"));
const mapManifest = mapManifestJson as MapManifest;
const initialSite = mapManifest.sites[0];

if (!initialSite) {
  throw new Error("The dive atlas requires at least one site");
}

const DATA_SOURCES = [
  {
    title: "Bathymétrie",
    description:
      "Relief sous-marin issu du levé HYSCORES 2015, incluant les données Litto3D.",
    links: [
      {
        label: "HYSCORES 2015",
        href: "https://doi.org/10.12770/ee059de2-2c81-46ce-88de-0fb5517046af",
      },
      { label: "Ifremer", href: "https://www.ifremer.fr/fr" },
      {
        label: "UBO",
        href: "https://www.univ-brest.fr/fr",
      },
      {
        label: "Office de l’eau Réunion",
        href: "https://donnees.eaureunion.fr/",
      },
    ],
  },
  {
    title: "Topographie",
    description:
      "Modèle numérique de terrain RGE ALTI pour le relief de la partie terrestre.",
    links: [
      {
        label: "IGN RGE ALTI",
        href: "https://cartes.gouv.fr/rechercher-une-donnee/dataset/IGNF_RGE-ALTI",
      },
    ],
  },
  {
    title: "Orthophoto",
    description:
      "Orthophotographies géoréférencées BD ORTHO pour le fond aérien haute résolution.",
    links: [
      {
        label: "IGN BD ORTHO",
        href: "https://cartes.gouv.fr/rechercher-une-donnee/dataset/IGNF_BD-ORTHO",
      },
    ],
  },
  {
    title: "Relief régional",
    description:
      "Grille bathymétrique GEBCO 2024 pour la carte de sélection de la côte ouest.",
    links: [
      {
        label: "GEBCO 2024",
        href: "https://www.gebco.net/data-products-gridded-bathymetry-data/gebco2024-grid",
      },
    ],
  },
] as const;

const METHOD_STEPS = [
  "Toutes les données sont reprojetées dans le même système de coordonnées : UTM 40S, EPSG:32740.",
  "Le relief terrestre et les fonds marins sont assemblés en une surface continue le long du littoral.",
  "Les isobathes sont générées tous les 5 m ; les vues 3D utilisent une exagération verticale d’environ ×4.",
  "Plans 2D, vues 3D, reliefs interactifs et planches HD sont produits à partir des mêmes paramètres de site.",
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

function gpsLabel(location: SiteLocation) {
  return `${formatDms(location.latitude, "N", "S")} · ${formatDms(
    location.longitude,
    "E",
    "O",
  )}`;
}

function googleMapsUrl(location: SiteLocation) {
  const query = `${location.latitude.toFixed(8)},${location.longitude.toFixed(8)}`;
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`;
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

const SITE_LABEL_LAYOUT = {
  "cap-la-houssaye": "right-up",
  "boucan-canot": "left-down",
  "passe-hermitage": "right",
} as const;

function SitePicker({
  activeSlug,
  onSelect,
  onOpenOverview,
}: {
  activeSlug: string;
  onSelect: (slug: string) => void;
  onOpenOverview: () => void;
}) {
  return (
    <aside className="site-picker" aria-label="Choisir un site de plongée">
      <label className="site-picker-select">
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

      <div className="site-picker-maps">
        <button
          type="button"
          className="reunion-overview"
          aria-label="Ouvrir la carte de La Réunion en grand"
          onClick={onOpenOverview}
        >
          <div className="reunion-overview-map">
            <img
              src={mapManifest.reunionOverview.src}
              width={mapManifest.reunionOverview.width}
              height={mapManifest.reunionOverview.height}
              alt="Relief terrestre et sous-marin de La Réunion. Un rectangle situe la zone ouest détaillée ci-dessous."
            />
            <span className="reunion-overview-extent" aria-hidden="true" />
          </div>
        </button>

        <div className="site-picker-map">
          <img
            src={mapManifest.westCoastLocator.src}
            width={mapManifest.westCoastLocator.width}
            height={mapManifest.westCoastLocator.height}
            alt="Relief terrestre et sous-marin de la côte ouest de La Réunion, du Cap La Houssaye à Saint-Leu."
          />
          <div className="site-picker-range" aria-hidden="true">
            <strong>Côte ouest</strong>
          </div>
          <div className="site-picker-north" aria-label="Nord">
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
                aria-label={`Afficher ${site.displayName}`}
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
            aria-label="Échelle de cinq kilomètres"
          >
            <span aria-hidden="true" />
            <strong>5 km</strong>
          </div>
        </div>
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
  const overviewDialogRef = useRef<HTMLDialogElement>(null);

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

  function closeOverviewOnBackdrop(
    event: React.MouseEvent<HTMLDialogElement>,
  ) {
    if (event.target === overviewDialogRef.current) {
      overviewDialogRef.current.close();
    }
  }

  const mapAlt =
    staticView === "2d"
      ? `Plan topo-bathymétrique 2D de ${activeSite.displayName}, nord en haut, fond ${surfaceLabel(surfaceStyle).toLowerCase()}, profondeurs affichées jusqu’à −${activeSite.maxDepthM} m.`
      : `Perspective 3D oblique de ${activeSite.displayName}, fond ${surfaceLabel(surfaceStyle).toLowerCase()}, relief vertical exagéré environ quatre fois.`;

  return (
    <main>
      <header className="masthead" id="top">
        <div className="masthead-inner">
          <a className="brand" href="#atlas">
            <span className="brand-mark" aria-hidden="true" />
            <span>Plan des sites de plongée · La Réunion</span>
          </a>
          <nav aria-label="Navigation principale">
            <a href="#atlas">Explorer</a>
            <a href="#sources">Méthode et sources</a>
            <a
              href="https://github.com/mfoll/reunion-topobathy"
              target="_blank"
              rel="noreferrer"
            >
              GitHub
            </a>
          </nav>
        </div>
      </header>

      <section className="atlas-section" id="atlas" aria-labelledby="atlas-title">
        <div className="atlas-intro">
          <h1 id="atlas-title">Plans des sites de plongée à La Réunion</h1>
        </div>

        <div className="atlas-workspace">
          <SitePicker
            activeSlug={activeSlug}
            onSelect={setActiveSlug}
            onOpenOverview={() => overviewDialogRef.current?.showModal()}
          />

          <article
            className="atlas-main"
            id="atlas-panel"
            aria-labelledby={`active-site-title-${activeSite.slug}`}
          >
            <div className="viewer-head">
              <header className="active-site-heading">
                <div>
                  <h2 id={`active-site-title-${activeSite.slug}`}>
                    {activeSite.displayName}
                  </h2>
                  <p>
                    <span>{activeSite.location.city}, La Réunion</span>
                    <span aria-hidden="true">·</span>
                    <span>{gpsLabel(activeSite.location)}</span>
                  </p>
                </div>
                <a
                  href={googleMapsUrl(activeSite.location)}
                  target="_blank"
                  rel="noreferrer"
                >
                  Voir le site sur Google Maps
                </a>
              </header>

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
                <strong>Planche HD à imprimer</strong>
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

        </div>
      </section>

      <section
        className="sources-section"
        id="sources"
        aria-labelledby="sources-title"
      >
        <div className="sources-inner">
          <div className="sources-heading">
            <h2 id="sources-title">Données, méthode et licences</h2>
            <p>
              Ce projet est rendu possible par des données bathymétriques,
              topographiques et aériennes librement accessibles, mises à
              disposition par des organismes publics et scientifiques.
            </p>
          </div>

          <div className="source-cards">
            {DATA_SOURCES.map((source, index) => (
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
              <span className="method-label">Traitement cartographique</span>
              <h3>Méthode de production</h3>
            </div>
            <ul>
              {METHOD_STEPS.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ul>
          </div>

          <div className="project-notes">
            <article>
              <h3>Crédits et licence</h3>
              <p>
                Plans et visualisations © {initialSite.copyrightYear}{" "}
                {initialSite.plateAuthor}.
              </p>
              <a
                href="https://creativecommons.org/licenses/by-nc-sa/4.0/deed.fr"
                target="_blank"
                rel="noreferrer"
              >
                {initialSite.mapLicense}
              </a>
            </article>
            <article>
              <h3>Code source</h3>
              <p>
                La chaîne de production et le code du site sont disponibles sur
                GitHub.
              </p>
              <a
                href="https://github.com/mfoll/reunion-topobathy"
                target="_blank"
                rel="noreferrer"
              >
                Voir le dépôt GitHub
              </a>
            </article>
            <article>
              <h3>Sécurité</h3>
              <p>
                Ces plans ne sont pas destinés à la navigation et ne remplacent
                pas les informations locales, les conditions de mer, les
                consignes des autorités ou l’avis d’un professionnel.
              </p>
            </article>
          </div>
        </div>
      </section>

      <footer className="site-footer">
        <a className="brand" href="#top">
          <span className="brand-mark" aria-hidden="true" />
          <span>Plan des sites de plongée · La Réunion</span>
        </a>
        <span>
          Plans © {initialSite.copyrightYear} {initialSite.plateAuthor} ·{" "}
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

      <dialog
        className="map-dialog overview-dialog"
        ref={overviewDialogRef}
        onClick={closeOverviewOnBackdrop}
        aria-label="Carte de La Réunion en grand"
      >
        <button
          type="button"
          className="dialog-close"
          onClick={() => overviewDialogRef.current?.close()}
        >
          Fermer
        </button>
        <div className="overview-dialog-map">
          <img
            src={mapManifest.reunionOverview.src}
            width={mapManifest.reunionOverview.width}
            height={mapManifest.reunionOverview.height}
            alt="Relief terrestre et sous-marin de La Réunion. Un rectangle situe la zone ouest couverte par la carte de sélection des sites."
          />
          <span className="reunion-overview-extent" aria-hidden="true" />
        </div>
      </dialog>

    </main>
  );
}
