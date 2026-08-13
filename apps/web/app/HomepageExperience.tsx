/* eslint-disable @next/next/no-img-element -- the regional relief is a fixed, locally generated map */

import { homepageCopy } from "../content/homepage-copy";
import type { Language, Theme } from "../content/preferences";
import { regions } from "../content/regions";
import InstallPrompt from "./InstallPrompt";
import PreferenceControls from "./PreferenceControls";

type HomepageSitePosition = {
  slug: string;
  position: { xPercent: number; yPercent: number };
};

function spreadNearbyPoints(sites: HomepageSitePosition[]) {
  const visited = new Set<number>();
  const offsets = sites.map(() => ({ x: 0, y: 0 }));

  sites.forEach((_, index) => {
    if (visited.has(index)) return;
    const group: number[] = [];
    const pending = [index];
    visited.add(index);
    while (pending.length) {
      const currentIndex = pending.pop()!;
      group.push(currentIndex);
      sites.forEach((candidate, candidateIndex) => {
        if (visited.has(candidateIndex)) return;
        const current = sites[currentIndex];
        if (
          Math.hypot(
            candidate.position.xPercent - current.position.xPercent,
            candidate.position.yPercent - current.position.yPercent,
          ) < 1.5
        ) {
          visited.add(candidateIndex);
          pending.push(candidateIndex);
        }
      });
    }
    if (group.length < 2) return;

    const radius = group.length > 2 ? 2.75 : 2.25;
    group.forEach((candidateIndex, groupIndex) => {
      const angle = (Math.PI * 2 * groupIndex) / group.length - Math.PI / 2;
      offsets[candidateIndex] = {
        x: Math.cos(angle) * radius,
        y: Math.sin(angle) * radius,
      };
    });
  });

  return sites.map((site, index) => ({ ...site, offset: offsets[index] }));
}

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
            <span className="brand-wordmark">DiveTopo</span>
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
                  <div
                    className="region-visual"
                    style={{
                      aspectRatio: `${region.image.width} / ${region.image.height}`,
                    }}
                  >
                    <img
                      src={region.image.src}
                      width={region.image.width}
                      height={region.image.height}
                      style={{
                        aspectRatio: `${region.image.width} / ${region.image.height}`,
                      }}
                      alt={region.image.alt[language]}
                      fetchPriority="high"
                    />
                    <span className="region-site-points" aria-hidden="true">
                      {spreadNearbyPoints(region.sitePositions).map((site) => (
                        <span
                          className="region-site-point"
                          data-source-x={site.position.xPercent}
                          data-source-y={site.position.yPercent}
                          data-site-slug={site.slug}
                          key={site.slug}
                          style={{
                            left: `${site.position.xPercent}%`,
                            top: `${site.position.yPercent}%`,
                            translate: `${site.offset.x}px ${site.offset.y}px`,
                          }}
                        />
                      ))}
                    </span>
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
          <span className="brand-wordmark">DiveTopo</span>
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
          <span>{text.footer.analytics}</span>
        </div>
        <a href="#top">{text.footer.backToTop}</a>
      </footer>
    </>
  );
}
