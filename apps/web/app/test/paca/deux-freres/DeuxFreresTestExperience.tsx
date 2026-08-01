"use client";

import { lazy, Suspense, useCallback, useState } from "react";
import styles from "./deux-freres.module.css";

type SurfaceStyle = "topographic" | "orthophoto";

const TerrainViewer = lazy(() => import("../../../TerrainViewer"));

const MAP_BASE = "/test-assets/paca/deux-freres/maps";
const TERRAIN_SLUG = "deux-freres-cap-sicie";
const TERRAIN_BASE = `/terrain/${TERRAIN_SLUG}`;

const compactAttributions: Record<SurfaceStyle, string> = {
  topographic: "Bathymétrie/topographie : Litto3D PACA 2015 · IGN69",
  orthophoto:
    "Litto3D PACA 2015 · Orthophoto : IGN BD ORTHO 13-07-2023 · IGN69",
};

function dynamicPoster(surface: SurfaceStyle) {
  return `${MAP_BASE}/3d-dynamic-${surface}-2474.webp`;
}

function dynamicMobilePoster(surface: SurfaceStyle) {
  return `${MAP_BASE}/3d-dynamic-${surface}-mobile-960.webp`;
}

function dynamicDownload(surface: SurfaceStyle) {
  return `${MAP_BASE}/downloads/3d-dynamic-${surface}-full.jpg`;
}

export default function DeuxFreresTestExperience() {
  const [surface, setSurface] = useState<SurfaceStyle>("orthophoto");
  const [terrainReady, setTerrainReady] = useState(false);
  const markReady = useCallback(() => setTerrainReady(true), []);

  function changeSurface(nextSurface: SurfaceStyle) {
    if (nextSurface !== surface) setTerrainReady(false);
    setSurface(nextSurface);
  }

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <div>
          <p className={styles.eyebrow}>Prototype local · PACA</p>
          <h1>Les Deux Frères, Cap Sicié</h1>
          <p className={styles.lead}>
            Vue 3D directement interactive, issue du paquet terrain v1.1.
          </p>
        </div>
        <span className={styles.badge}>Non publié</span>
      </header>

      <section
        className="topo-reunion-section"
        aria-labelledby="deux-freres-title"
      >
        <div className="topo-reunion-intro">
          <h2 id="deux-freres-title">Les Deux Frères</h2>
          <p>
            Relief réel Shom–IGN Litto3D PACA 2015 et orthophoto IGN BD ORTHO.
          </p>
        </div>

        <article
          className="topo-reunion-main"
          aria-label="Les Deux Frères, Cap Sicié"
        >
          <div className="viewer-head">
            <header className="active-site-heading">
              <div>
                <h2>Vue 3D</h2>
                <p>Les Deux Frères · La Seyne-sur-Mer · Cap Sicié</p>
              </div>
              <span>Lambert-93 · EPSG:2154</span>
            </header>

            <div className="viewer-toolbar is-unified-3d">
              <fieldset className="segmented-control surface-control">
                <legend>Fond de carte</legend>
                <button
                  type="button"
                  aria-pressed={surface === "orthophoto"}
                  onClick={() => changeSurface("orthophoto")}
                >
                  Vue aérienne
                </button>
                <button
                  type="button"
                  aria-pressed={surface === "topographic"}
                  onClick={() => changeSurface("topographic")}
                >
                  Topographie
                </button>
              </fieldset>
            </div>
          </div>

          <div
            className="viewer-frame is-interactive has-unified-3d"
            data-testid="deux-freres-test-viewer"
          >
            <picture
              className={`${styles.poster} ${terrainReady ? styles.posterHidden : ""}`}
            >
              <source
                media="(max-width: 560px)"
                srcSet={dynamicMobilePoster(surface)}
              />
              <img
                src={dynamicPoster(surface)}
                width={2474}
                height={1712}
                alt=""
                aria-hidden="true"
                fetchPriority="high"
              />
            </picture>

            <div
              className={`unified-3d-layer${terrainReady ? " is-rendered" : ""}`}
              data-testid="deux-freres-interactive-layer"
            >
              <Suspense
                fallback={
                  <div className="terrain-loading" role="status">
                    Préparation du relief…
                  </div>
                }
              >
                <TerrainViewer
                  key={surface}
                  slug={TERRAIN_SLUG}
                  siteName="Les Deux Frères"
                  style={surface}
                  language="fr"
                  vectorIsobathsPath={`${TERRAIN_BASE}/isobaths-vector.json`}
                  initialZoom={0.9}
                  initialCenterOffsetEastM={310}
                  initialCenterOffsetSouthM={100}
                  compactAttributions={compactAttributions}
                  onReady={markReady}
                  downloadHref={dynamicDownload(surface)}
                  downloadFilename={`deux-freres-cap-sicie-3d-${surface}.jpg`}
                  downloadLabel="Télécharger la vue 3D en haute définition"
                />
              </Suspense>
            </div>
          </div>

          <div className="viewer-meta">
            <span>
              Glisser pour tourner · Molette ou pincement pour zoomer ·
              contrôles isobathes, recentrage, plein écran et téléchargement
            </span>
          </div>

          <div className={styles.planGrid}>
            <figure className={styles.plan}>
              <img
                src={`${MAP_BASE}/2d-topographic.jpg`}
                width={2474}
                height={1712}
                alt="Plan 2D topobathymétrique topographique des Deux Frères"
                loading="lazy"
              />
              <figcaption>
                <strong>Plan 2D topographique</strong>
                <a
                  href={`${MAP_BASE}/2d-topographic.jpg`}
                  download="deux-freres-cap-sicie-topobathy-2d.jpg"
                >
                  Télécharger le plan HD
                </a>
              </figcaption>
            </figure>
            <figure className={styles.plan}>
              <img
                src={`${MAP_BASE}/2d-orthophoto.jpg`}
                width={2474}
                height={1712}
                alt="Plan 2D topobathymétrique avec orthophoto des Deux Frères"
                loading="lazy"
              />
              <figcaption>
                <strong>Plan 2D orthophoto</strong>
                <a
                  href={`${MAP_BASE}/2d-orthophoto.jpg`}
                  download="deux-freres-cap-sicie-topobathy-2d-ortho.jpg"
                >
                  Télécharger le plan HD
                </a>
              </figcaption>
            </figure>
          </div>

          <p className={styles.credits}>
            Bathymétrie et topographie : Shom–IGN Litto3D PACA 2015, MNT brut à
            1 m · Orthophoto : IGN BD ORTHO, prise de vue du 13 juillet 2023 ·
            Référentiel vertical IGN69 · © 2026 Matthieu Foll · CC BY-NC-SA
            4.0
          </p>
        </article>
      </section>
    </main>
  );
}
