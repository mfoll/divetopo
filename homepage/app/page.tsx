/* eslint-disable @next/next/no-img-element -- the regional relief is a fixed, locally generated map */

import { regions } from "../content/regions";

export default function Home() {
  return (
    <>
      <header className="masthead">
        <div className="masthead-inner">
          <a className="brand" href="#top" aria-label="DiveTopo, accueil">
            <span className="brand-mark" aria-hidden="true" />
            <span>DiveTopo</span>
          </a>
          <nav aria-label="Navigation principale">
            <a href="#regions">Régions</a>
          </nav>
        </div>
      </header>

      <main id="top">
        <section className="hero" aria-labelledby="hero-title">
          <div className="hero-inner">
            <p className="eyebrow">Cartographies de sites de plongée</p>
            <h1 id="hero-title">Le relief sous-marin, région par région.</h1>
            <p className="hero-lead">
              DiveTopo réunit des cartes de sites de plongée qui prolongent le
              paysage sous la surface, du plan 2D au relief interactif.
            </p>
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
                <p className="eyebrow">Explorer</p>
                <h2 id="regions-title">Choisissez une région</h2>
              </div>
              <p>
                Chaque région rassemble les cartes disponibles pour certains
                sites de son territoire.
              </p>
            </div>

            <div className="region-grid">
              {regions.map((region) => (
                <a
                  className="region-card"
                  data-testid={`region-${region.slug}`}
                  href={region.href}
                  key={region.slug}
                  aria-label={`Explorer les cartes de ${region.name}`}
                >
                  <div className="region-visual">
                    <img
                      src={region.image.src}
                      width={region.image.width}
                      height={region.image.height}
                      alt={region.image.alt}
                      fetchPriority="high"
                    />
                    <span className="region-status">
                      <span aria-hidden="true" />
                      {region.status}
                    </span>
                  </div>
                  <div className="region-copy">
                    <div className="region-title-row">
                      <div>
                        <p>{region.location}</p>
                        <h3>{region.name}</h3>
                      </div>
                      <span className="region-arrow" aria-hidden="true">
                        ↗
                      </span>
                    </div>
                    <p className="region-description">{region.description}</p>
                    <ul
                      className="region-features"
                      aria-label="Contenu disponible"
                    >
                      {region.features.map((feature) => (
                        <li key={feature}>{feature}</li>
                      ))}
                    </ul>
                  </div>
                </a>
              ))}
            </div>

            <aside className="future-note" aria-label="Évolution de DiveTopo">
              <span className="future-icon" aria-hidden="true">
                +
              </span>
              <p>
                <strong>Une page prête à accueillir d’autres régions.</strong>{" "}
                Elles apparaîtront ici au fil des sites effectivement
                cartographiés.
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
          <p>
            Relief insulaire : IGN RGE ALTI · GEBCO Compilation Group (2024)
            GEBCO 2024 Grid.
          </p>
        </div>
      </footer>
    </>
  );
}
