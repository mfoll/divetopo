/* eslint-disable @next/next/no-img-element -- the regional relief is a fixed, locally generated map */

import { regions } from "../content/regions";

const CAPABILITIES = [
  {
    number: "01",
    title: "Plans 2D",
    description:
      "Des vues lisibles du littoral et des profondeurs pour situer les formes du relief.",
  },
  {
    number: "02",
    title: "Perspectives 3D",
    description:
      "Des reliefs obliques qui rendent visibles les pentes, tombants et continuités terre-mer.",
  },
  {
    number: "03",
    title: "Reliefs interactifs",
    description:
      "Une exploration libre des modèles disponibles, directement dans le navigateur.",
  },
] as const;

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
            <a href="#projet">Le projet</a>
          </nav>
        </div>
      </header>

      <main id="top">
        <section className="hero" aria-labelledby="hero-title">
          <div className="hero-inner">
            <p className="eyebrow">Atlas topo-bathymétriques</p>
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
                Chaque atlas rassemble les cartes disponibles pour un même
                territoire.
              </p>
            </div>

            <div className="region-grid">
              {regions.map((region) => (
                <a
                  className="region-card"
                  data-testid={`region-${region.slug}`}
                  href={region.href}
                  key={region.slug}
                  aria-label={`Explorer l’atlas de ${region.name}`}
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
                    <ul className="region-features" aria-label="Contenu de l’atlas">
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
                <strong>Un atlas pensé pour grandir.</strong> De nouvelles
                régions viendront rejoindre cette page au fil des prochaines
                cartographies.
              </p>
            </aside>
          </div>
        </section>

        <section
          className="project-section"
          id="projet"
          aria-labelledby="project-title"
        >
          <div className="project-inner">
            <div className="project-heading">
              <p className="eyebrow">Une lecture du terrain</p>
              <h2 id="project-title">
                Comprendre les formes qui continuent sous l’eau.
              </h2>
              <p>
                Chaque région conserve sa géographie, ses sources et ses
                échelles. DiveTopo leur donne un langage visuel commun.
              </p>
            </div>

            <ol className="capability-grid">
              {CAPABILITIES.map((capability) => (
                <li key={capability.number}>
                  <span>{capability.number}</span>
                  <h3>{capability.title}</h3>
                  <p>{capability.description}</p>
                </li>
              ))}
            </ol>

            <p className="orientation-note">
              Ces cartes sont des aides à la lecture du relief et à
              l’orientation générale. Elles ne remplacent ni les informations
              locales, ni l’évaluation des conditions et de la sécurité.
            </p>
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
