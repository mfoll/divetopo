"use client";

/* eslint-disable @next/next/no-img-element -- responsive derivatives are prebuilt and one native image is intentionally swapped in place */

import {
  lazy,
  Suspense,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
} from "react";
import mapManifestJson from "../public/maps/manifest.json";

type SurfaceStyle = "topographic" | "orthophoto";
type MapView = "2d" | "3d";

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
  plateTitle: string;
  verticalExaggeration: number;
  locator: AssetVariant;
  maps: MapAsset[];
  planches: PlancheAsset[];
};

type MapManifest = {
  sites: AtlasAssetSite[];
};

type SiteCopy = {
  name: string;
  shortName: string;
  description: string;
  coordinates: [string, string];
  extent: string;
  depth: number;
  orthophotoDate: string;
};

const TerrainViewer = lazy(() => import("./TerrainViewer"));
const mapManifest = mapManifestJson as MapManifest;

const SITE_COPY: Record<string, SiteCopy> = {
  "cap-la-houssaye": {
    name: "Cap La Houssaye",
    shortName: "Cap La Houssaye",
    description:
      "Une lecture resserrée des deux pointes du Cap et du relief côtier jusqu’à −20 m. La côte reste au cœur du cadre, là où les formes sont les plus lisibles.",
    coordinates: ["21° 01′ 02.5″ S", "55° 14′ 14.8″ E"],
    extent: "≈ 495 × 342 m",
    depth: 20,
    orthophotoDate: "22 juillet 2025",
  },
  "boucan-canot": {
    name: "Boucan Canot",
    shortName: "Boucan Canot",
    description:
      "Autour de la piscine naturelle, une emprise de 800 × 554 m et une perspective orientée vers le sud-est, jusqu’à −30 m.",
    coordinates: ["21° 01′ 36.7″ S", "55° 13′ 32.9″ E"],
    extent: "800 × 554 m",
    depth: 30,
    orthophotoDate: "22 juillet 2025",
  },
  "passe-hermitage": {
    name: "Passe de l’Hermitage",
    shortName: "Passe de l’Hermitage",
    description:
      "Une emprise d’un kilomètre centrée sur la passe et le grand lagon, prolongée jusqu’à −30 m. La perspective regarde vers le nord-est.",
    coordinates: ["21° 05′ 06.7″ S", "55° 13′ 26.6″ E"],
    extent: "1 000 × 692 m",
    depth: 30,
    orthophotoDate: "2 août 2025",
  },
};

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

function SurfaceToggle({
  value,
  onChange,
  dark = false,
}: {
  value: SurfaceStyle;
  onChange: (style: SurfaceStyle) => void;
  dark?: boolean;
}) {
  return (
    <fieldset
      className={`segmented-control surface-control${dark ? " is-dark" : ""}`}
    >
      <legend>Fond de carte</legend>
      <button
        type="button"
        aria-pressed={value === "topographic"}
        onClick={() => onChange("topographic")}
      >
        Topographie
      </button>
      <button
        type="button"
        aria-pressed={value === "orthophoto"}
        onClick={() => onChange("orthophoto")}
      >
        Orthophoto
      </button>
    </fieldset>
  );
}

function ViewToggle({
  value,
  onChange,
  onExplore,
}: {
  value: MapView;
  onChange: (view: MapView) => void;
  onExplore: () => void;
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
        Perspective 3D
      </button>
      <button type="button" className="explore-control" onClick={onExplore}>
        Explorer en 3D
      </button>
    </fieldset>
  );
}

function SiteRail({
  activeSlug,
  onSelect,
  compact = false,
}: {
  activeSlug: string;
  onSelect: (slug: string) => void;
  compact?: boolean;
}) {
  return (
    <div
      className={`site-rail${compact ? " is-compact" : ""}`}
      role="tablist"
      aria-label="Choisir un site"
    >
      {mapManifest.sites.map((site, index) => {
        const copy = SITE_COPY[site.slug];
        return (
          <button
            key={site.slug}
            type="button"
            role="tab"
            aria-selected={activeSlug === site.slug}
            onClick={() => onSelect(site.slug)}
          >
            <span aria-hidden="true">{String(index + 1).padStart(2, "0")}</span>
            {copy.shortName}
          </button>
        );
      })}
    </div>
  );
}

export function AtlasExperience() {
  const [activeSlug, setActiveSlug] = useState("cap-la-houssaye");
  const [surfaceStyle, setSurfaceStyle] =
    useState<SurfaceStyle>("topographic");
  const [mapView, setMapView] = useState<MapView>("2d");
  const [explorerActive, setExplorerActive] = useState(false);
  const dialogRef = useRef<HTMLDialogElement>(null);

  const activeSite = useMemo(
    () =>
      mapManifest.sites.find((site) => site.slug === activeSlug) ??
      mapManifest.sites[0],
    [activeSlug],
  );
  const copy = SITE_COPY[activeSite.slug];
  const mapAsset = selectedMap(activeSite, mapView, surfaceStyle);
  const mapLargest = mapAsset.variants.at(-1) ?? mapAsset.variants[0];
  const planche = selectedPlanche(activeSite, surfaceStyle);

  function selectSite(slug: string) {
    setActiveSlug(slug);
  }

  function openExplorer() {
    setExplorerActive(true);
    const reducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    document
      .getElementById("explorer")
      ?.scrollIntoView({ behavior: reducedMotion ? "auto" : "smooth" });
  }

  function openMapDialog() {
    dialogRef.current?.showModal();
  }

  function closeOnBackdrop(event: React.MouseEvent<HTMLDialogElement>) {
    if (event.target === dialogRef.current) dialogRef.current.close();
  }

  function handleSiteKeys(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    const currentIndex = mapManifest.sites.findIndex(
      (site) => site.slug === activeSlug,
    );
    const direction = event.key === "ArrowRight" ? 1 : -1;
    const nextIndex =
      (currentIndex + direction + mapManifest.sites.length) %
      mapManifest.sites.length;
    selectSite(mapManifest.sites[nextIndex].slug);
  }

  return (
    <main>
      <header className="masthead" id="top">
        <a className="brand" href="#atlas" aria-label="Reliefs de l’Ouest">
          Reliefs de l’Ouest
        </a>
        <nav aria-label="Navigation principale">
          <a href="#sites">Les sites</a>
          <a href="#method">La méthode</a>
          <a href="#credits">À propos</a>
        </nav>
      </header>

      <section className="atlas-hero" id="atlas" aria-labelledby="hero-title">
        <div className="hero-topline">
          <div className="hero-copy">
            <h1 id="hero-title">
              <span>Lire la côte</span>
              <span>sous la surface</span>
            </h1>
            <p>
              Trois sites de plongée, cartographiés du rivage jusqu’aux fonds
              marins.
            </p>
          </div>
          <div onKeyDown={handleSiteKeys}>
            <SiteRail activeSlug={activeSlug} onSelect={selectSite} compact />
          </div>
        </div>

        <div className="map-toolbar">
          <ViewToggle
            value={mapView}
            onChange={setMapView}
            onExplore={openExplorer}
          />
          <SurfaceToggle
            value={surfaceStyle}
            onChange={setSurfaceStyle}
          />
        </div>

        <figure className="map-stage">
          <button
            type="button"
            className="map-open"
            onClick={openMapDialog}
            aria-label={`Ouvrir la carte de ${copy.name} en grand`}
          >
            <img
              key={`${activeSite.slug}-${mapView}-${surfaceStyle}`}
              src={mapLargest.src}
              srcSet={assetSrcSet(mapAsset.variants)}
              sizes="(max-width: 760px) 100vw, 92vw"
              width={mapLargest.width}
              height={mapLargest.height}
              alt={
                mapView === "2d"
                  ? `Plan topo-bathymétrique 2D de ${copy.name}, nord en haut, fond ${surfaceStyle === "topographic" ? "topographique" : "orthophoto"}, profondeurs affichées jusqu’à −${copy.depth} m.`
                  : `Perspective 3D oblique de ${copy.name}, fond ${surfaceStyle === "topographic" ? "topographique" : "orthophoto"}, relief vertical exagéré environ quatre fois.`
              }
              fetchPriority="high"
            />
            <span>Ouvrir en grand</span>
          </button>
          <figcaption>
            <strong>{copy.name}</strong>
            <span>
              {mapView === "2d" ? "Plan métrique" : "Lecture du relief"}
              {" · "}
              {surfaceStyle === "topographic"
                ? "Relief topographique"
                : "Orthophoto"}
            </span>
          </figcaption>
        </figure>

        <a className="scroll-cue" href="#sites">
          Découvrir les cartes
        </a>
      </section>

      <section className="site-section" id="sites" aria-labelledby="sites-title">
        <div className="section-index" aria-hidden="true">
          02 / Les sites
        </div>
        <div className="site-layout">
          <aside className="site-index">
            <SiteRail activeSlug={activeSlug} onSelect={selectSite} />
          </aside>
          <article className="site-story">
            <h2 id="sites-title">Trois reliefs, trois lectures de la côte</h2>
            <div className="story-grid">
              <div className="story-copy">
                <h3>{copy.name}</h3>
                <p>{copy.description}</p>
                <dl>
                  <div>
                    <dt>Coordonnées</dt>
                    <dd>
                      {copy.coordinates[0]}
                      <br />
                      {copy.coordinates[1]}
                    </dd>
                  </div>
                  <div>
                    <dt>Emprise du plan 2D</dt>
                    <dd>{copy.extent}</dd>
                  </div>
                  <div>
                    <dt>Lecture</dt>
                    <dd>
                      Isobathes · 5 m
                      <br />
                      Relief 3D · ≈ ×4
                    </dd>
                  </div>
                </dl>
                <a
                  className="download-link"
                  href={planche.download.src}
                  download={planche.download.filename}
                >
                  Télécharger la planche HD
                </a>
              </div>
              <figure className="planche-frame">
                <img
                  key={`${activeSite.slug}-planche-${surfaceStyle}`}
                  src={planche.preview.src}
                  width={planche.preview.width}
                  height={planche.preview.height}
                  loading="lazy"
                  alt={`Planche complète de ${copy.name} réunissant localisation, plan 2D et perspective 3D, fond ${surfaceStyle === "topographic" ? "topographique" : "orthophoto"}.`}
                />
                <figcaption>
                  Planche imprimable · 5 400 × 3 250 px
                </figcaption>
              </figure>
            </div>
          </article>
        </div>
      </section>

      <section
        className="explorer-section"
        id="explorer"
        aria-labelledby="explorer-title"
      >
        <div className="explorer-canvas">
          {explorerActive ? (
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
                siteName={copy.name}
                style={surfaceStyle}
              />
            </Suspense>
          ) : (
            <button
              type="button"
              className="terrain-poster"
              onClick={() => setExplorerActive(true)}
            >
              <img
                src={selectedMap(activeSite, "3d", surfaceStyle).variants[1].src}
                width={1600}
                height={1107}
                loading="lazy"
                alt=""
              />
              <span>Activer le relief interactif</span>
            </button>
          )}
        </div>
        <div className="explorer-copy">
          <h2 id="explorer-title">Explorer le relief</h2>
          <p>
            Faites pivoter la carte, zoomez et suivez la côte du regard.
          </p>
          <div className="explorer-site">
            <span>Site sélectionné</span>
            <strong>{copy.name}</strong>
          </div>
          <SurfaceToggle
            value={surfaceStyle}
            onChange={setSurfaceStyle}
            dark
          />
          <div className="gesture-help">
            <p>
              Glisser pour tourner · Molette ou pincement pour zoomer · clic
              droit ou Ctrl + glisser pour déplacer
            </p>
            <p>
              Relief vertical ≈ ×4 · Le plan 2D reste la référence métrique
            </p>
          </div>
          <SiteRail activeSlug={activeSlug} onSelect={selectSite} compact />
        </div>
      </section>

      <section className="method-section" id="method" aria-labelledby="method-title">
        <div className="method-intro">
          <div>
            <h2 id="method-title">Du relevé au relief</h2>
            <p>
              Bathymétrie, topographie et orthophoto sont réunies dans un même
              référentiel pour produire une lecture continue de la côte.
            </p>
          </div>
          <img
            src="/maps/passe-hermitage/2d-orthophoto-1600.webp"
            width={1600}
            height={1107}
            loading="lazy"
            alt="Détail du raccord entre bathymétrie, trait de côte et orthophoto à la Passe de l’Hermitage."
          />
        </div>
        <ol className="method-steps">
          <li>
            <span>01</span>
            <h3>Bathymétrie</h3>
            <p>
              HYSCORES 2015 · Ifremer, UBO, Office de l’Eau Réunion
            </p>
          </li>
          <li>
            <span>02</span>
            <h3>Raccord terre–mer</h3>
            <p>RGE ALTI et continuité calculée au trait de côte</p>
          </li>
          <li>
            <span>03</span>
            <h3>Relief et textures</h3>
            <p>Isobathes tous les 5 m · relief vertical ≈ ×4</p>
          </li>
          <li>
            <span>04</span>
            <h3>Composition</h3>
            <p>Plan 2D, perspective 3D, orthophoto et planche imprimable</p>
          </li>
        </ol>
      </section>

      <aside className="safety-notice" aria-labelledby="safety-title">
        <h2 id="safety-title">Une carte pour comprendre, pas pour naviguer</h2>
        <p>
          Ces cartes sont des aides à la lecture du relief et à l’orientation
          générale. Elles ne remplacent ni les informations locales, ni l’état
          de mer, ni les consignes des autorités, ni l’évaluation d’un
          professionnel.
        </p>
      </aside>

      <section className="credits-section" id="credits" aria-labelledby="credits-title">
        <h2 id="credits-title">Crédits et licences</h2>
        <div className="credits-grid">
          <p>
            Cartes © 2026 Matthieu Foll · CC BY-NC-SA 4.0. Le partage et
            l’adaptation sont permis pour un usage non commercial, avec
            attribution, indication des modifications et partage sous la même
            licence.
          </p>
          <p>
            Bathymétrie : Projet HYSCORES, Ifremer, UBO et Office de l’Eau
            Réunion, 2015, incluant Litto3D. Topographie : IGN RGE ALTI.
            Orthophoto : IGN BD ORTHO, prise de vue du {copy.orthophotoDate}.
          </p>
          <p>
            Localisation insulaire : GEBCO Compilation Group (2024), GEBCO
            2024 Grid. Les données tierces conservent leurs propres conditions
            d’utilisation.
          </p>
        </div>
      </section>

      <footer className="site-footer">
        <a className="brand" href="#top">
          Reliefs de l’Ouest
        </a>
        <span>Cartes © 2026 Matthieu Foll · CC BY-NC-SA 4.0</span>
        <a href="#top">Haut de page</a>
      </footer>

      <dialog
        className="map-dialog"
        ref={dialogRef}
        onClick={closeOnBackdrop}
        aria-label={`Carte de ${copy.name} en grand`}
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
          alt=""
        />
      </dialog>
    </main>
  );
}
