import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Tests locaux PACA | DiveTopo",
  robots: {
    index: false,
    follow: false,
  },
};

const sites = [
  ["La Gabinière, Port-Cros", "/test/paca/gabiniere"],
  ["Pointe de Portissol", "/test/paca/portissol"],
  ["Les Deux Frères, Cap Sicié", "/test/paca/deux-freres"],
  ["Les Pyramides, Cap Dramont", "/test/paca/pyramides"],
  ["Cap des Mèdes, Porquerolles", "/test/paca/cap-des-medes"],
] as const;

export default function PacaTestIndexPage() {
  return (
    <main
      style={{
        margin: "0 auto",
        maxWidth: 760,
        padding: "3rem 1.25rem",
      }}
    >
      <p>Prototype local · PACA</p>
      <h1>Cinq sites validés</h1>
      <p>
        Index de validation local v1.1. Les routes ci-dessous restent
        non publiées.
      </p>
      <nav aria-label="Sites PACA">
        <ul>
          {sites.map(([name, href]) => (
            <li key={href}>
              <a href={href}>{name}</a>
            </li>
          ))}
        </ul>
      </nav>
    </main>
  );
}
