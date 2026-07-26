/* eslint-disable @next/next/no-img-element -- the regional relief is a fixed, locally generated map */

import { homepageCopy } from "../content/homepage-copy";
import type { Language, Theme } from "../content/preferences";
import { regions } from "../content/regions";
import InstallPrompt from "./InstallPrompt";
import PreferenceControls from "./PreferenceControls";

export default function HomepageExperience({
  language,
  theme,
}: {
  language: Language;
  theme: Theme;
}) {
  const text = homepageCopy[language];

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
              <a href="#contact">{text.contactNavigation}</a>
            </nav>
            <PreferenceControls
              language={language}
              theme={theme}
            />
          </div>
        </div>
      </header>

      <InstallPrompt copy={text.installPrompt} />

      <main className="homepage-main" id="top">
        <section className="hero" aria-labelledby="hero-title">
          <div className="hero-inner">
            <h1 id="hero-title">{text.heroTitle}</h1>
          </div>
        </section>

        <section
          className="regions-section"
          id="regions"
          aria-label={text.regionsNavigation}
        >
          <div className="regions-inner">
            <div className="region-grid">
              {regions.map((region) => (
                <a
                  aria-label={`${text.exploreRegion} ${region.name[language]}`}
                  className="region-card"
                  data-testid={`region-${region.slug}`}
                  href={`${region.href}/${language}`}
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
                  </div>
                  <div className="region-copy">
                    <div className="region-title-row">
                      <div>
                        <p>{region.location[language]}</p>
                        <h3>{region.name[language]}</h3>
                      </div>
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
          <span>DiveTopo</span>
        </a>
        <div className="site-footer-meta">
          <span className="site-footer-access">
            {text.footer.freeAccess} · {text.footer.adFree} ·{" "}
            {text.footer.codeLicense}{" "}
            <a
              href="https://opensource.org/license/mit"
              rel="noreferrer"
              target="_blank"
            >
              {text.footer.mitLicense}
            </a>{" "}
            · {text.footer.mapsLicense}{" "}
            <a
              href={`https://creativecommons.org/licenses/by-nc-sa/4.0/deed.${language}`}
              rel="noreferrer"
              target="_blank"
            >
              CC BY-NC-SA 4.0
            </a>
          </span>
          <span>{text.footer.aiGenerated}</span>
          <span>{text.footer.credit}</span>
        </div>
        <a href="#top">{text.footer.backToTop}</a>
      </footer>
    </>
  );
}
