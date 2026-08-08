/* eslint-disable @next/next/no-img-element -- regional relief is generated locally */

import type { CSSProperties } from "react";
import type { Language, Theme } from "../content/preferences";
import { regionCatalog } from "../content/region-catalog";
import {
  regionalMapManifests,
  type RegionSlug,
} from "../content/regional";
import PreferenceControls from "./PreferenceControls";

export default function EmptyRegionExperience({
  region,
  language,
  theme,
}: {
  region: RegionSlug;
  language: Language;
  theme: Theme;
}) {
  const catalog = regionCatalog[region];
  const manifest = regionalMapManifests[region];
  const plannedSites = manifest.plannedSites ?? [];
  const title =
    language === "fr"
      ? `Sites de plongée de ${catalog.names.fr}`
      : `Dive sites in ${catalog.names.en}`;
  const message =
    language === "fr"
      ? "Les cinq premières cartographies sont en cours de validation. Cette page sera ouverte site par site, sans publier les rendus qui n’ont pas encore passé la QA."
      : "The first five maps are being validated. This page will open site by site, without publishing renders that have not passed QA yet.";

  return (
    <>
      <header className="masthead" id="top">
        <div className="masthead-inner">
          <a className="brand" href={`/${language}`}>
            <span className="brand-home-cue" aria-hidden="true">←</span>
            <span className="brand-mark" aria-hidden="true" />
            <span className="brand-wordmark">DiveTopo</span>
          </a>
          <PreferenceControls language={language} theme={theme} />
        </div>
      </header>
      <main className="homepage-main">
        <section className="hero" aria-labelledby={`topo-${region}-title`}>
          <div className="hero-inner">
            <p>{catalog.location[language]}</p>
            <h1 id={`topo-${region}-title`}>{title}</h1>
            <p>{message}</p>
          </div>
        </section>
        <section className="regions-section regional-preview-section">
          <div className="regions-inner regional-preview-grid">
            <div className="site-picker-map is-paca regional-preview-map">
              <img
                src={manifest.westCoastLocator.src}
                width={manifest.westCoastLocator.width}
                height={manifest.westCoastLocator.height}
                alt={
                  language === "fr"
                    ? `Relief régional de ${catalog.names.fr}.`
                    : `Regional relief of ${catalog.names.en}.`
                }
              />
              {plannedSites.map((site) => {
                const layout = site.siteLabelLayout;
                return (
                  <span
                    key={site.slug}
                    className={`site-map-marker site-map-marker-preparing label-${layout.side}`}
                    style={{
                      "--site-x": `${site.westCoastLocatorPosition.xPercent}%`,
                      "--site-y": `${site.westCoastLocatorPosition.yPercent}%`,
                      "--label-shift-y": `${layout.shiftYRem}rem`,
                      "--label-width": layout.widthRem
                        ? `${layout.widthRem}rem`
                        : undefined,
                      "--label-offset": `${layout.labelOffsetRem ?? 2.3}rem`,
                      "--connector-angle": `${layout.connectorAngleDeg}deg`,
                      "--connector-width": `${layout.connectorWidthRem ?? 1}rem`,
                    } as CSSProperties}
                    aria-label={`${site.displayName}, ${language === "fr" ? "en préparation" : "in preparation"}`}
                  >
                    <span className="site-map-marker-dot" aria-hidden="true" />
                  </span>
                );
              })}
            </div>
            <div className="regional-preview-sites">
              <h2>{language === "fr" ? "Les cinq sites retenus" : "Five selected sites"}</h2>
              <ul>
                {plannedSites.map((site) => (
                  <li key={site.slug}>
                    <span>
                      <strong>{site.displayName}</strong>
                      <small>{site.location.city}</small>
                    </span>
                    <em>{language === "fr" ? "En préparation" : "In preparation"}</em>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>
      </main>
    </>
  );
}
