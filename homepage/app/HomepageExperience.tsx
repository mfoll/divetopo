"use client";

/* eslint-disable @next/next/no-img-element -- the regional relief is a fixed, locally generated map */

import { useEffect, useState } from "react";
import { homepageCopy } from "../content/copy";
import type { Language, Theme } from "../content/preferences";
import { regions } from "../content/regions";
import PreferenceControls from "./PreferenceControls";

export default function HomepageExperience({
  language: initialLanguage,
  theme,
}: {
  language: Language;
  theme: Theme;
}) {
  const [language, setLanguage] = useState(initialLanguage);
  const text = homepageCopy[language];

  useEffect(() => {
    document.documentElement.lang = language;
    document.title = text.documentTitle;
    document
      .querySelector('meta[name="description"]')
      ?.setAttribute("content", text.metadataDescription);
  }, [language, text.documentTitle, text.metadataDescription]);

  return (
    <>
      <header className="masthead">
        <div className="masthead-inner">
          <a className="brand" href="#top" aria-label={text.homeLabel}>
            <span className="brand-mark" aria-hidden="true" />
            <span>DiveTopo</span>
          </a>
          <div className="masthead-actions">
            <nav className="primary-nav" aria-label={text.navigationLabel}>
              <a href="#regions">{text.regionsNavigation}</a>
            </nav>
            <PreferenceControls
              language={language}
              theme={theme}
              onLanguageChange={setLanguage}
            />
          </div>
        </div>
      </header>

      <main id="top">
        <section className="hero" aria-labelledby="hero-title">
          <div className="hero-inner">
            <p className="eyebrow">{text.heroEyebrow}</p>
            <h1 id="hero-title">{text.heroTitle}</h1>
            <p className="hero-lead">{text.heroLead}</p>
          </div>
        </section>

        <section
          className="regions-section"
          id="regions"
          aria-labelledby="regions-title"
        >
          <div className="regions-inner">
            <div className="section-heading">
              <div>
                <p className="eyebrow">{text.exploreEyebrow}</p>
                <h2 id="regions-title">{text.regionsTitle}</h2>
              </div>
              <p>{text.regionsLead}</p>
            </div>

            <div className="region-grid">
              {regions.map((region) => (
                <a
                  aria-label={`${text.exploreRegion} ${region.name[language]}`}
                  className="region-card"
                  data-testid={`region-${region.slug}`}
                  href={region.href}
                  key={region.slug}
                >
                  <div className="region-visual">
                    <img
                      src={region.image.src}
                      width={region.image.width}
                      height={region.image.height}
                      alt={region.image.alt[language]}
                      fetchPriority="high"
                    />
                    <span className="region-status">
                      <span aria-hidden="true" />
                      {region.status[language]}
                    </span>
                  </div>
                  <div className="region-copy">
                    <div className="region-title-row">
                      <div>
                        <p>{region.location[language]}</p>
                        <h3>{region.name[language]}</h3>
                      </div>
                      <span className="region-arrow" aria-hidden="true">
                        ↗
                      </span>
                    </div>
                    <p className="region-description">
                      {region.description[language]}
                    </p>
                    <ul
                      className="region-features"
                      aria-label={text.availableContent}
                    >
                      {region.features.map((feature) => (
                        <li key={feature.fr}>{feature[language]}</li>
                      ))}
                    </ul>
                  </div>
                </a>
              ))}
            </div>

            <aside className="future-note" aria-label={text.futureLabel}>
              <span className="future-icon" aria-hidden="true">
                +
              </span>
              <p>
                <strong>{text.futureStrong}</strong> {text.futureText}
              </p>
            </aside>
          </div>
        </section>
      </main>

      <footer className="site-footer">
        <div className="footer-inner">
          <a className="brand footer-brand" href="#top">
            <span className="brand-mark" aria-hidden="true" />
            <span>DiveTopo</span>
          </a>
          <p>{text.footer}</p>
        </div>
      </footer>
    </>
  );
}
