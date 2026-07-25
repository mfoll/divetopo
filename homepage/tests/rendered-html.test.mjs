import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import test from "node:test";

async function render(requestHeaders = {}) {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}-${Math.random()}`);
  const { default: worker } = await import(workerUrl.href);

  return worker.fetch(
    new Request("http://localhost/", {
      headers: {
        accept: "text/html",
        ...requestHeaders,
      },
    }),
    {
      ASSETS: {
        fetch: async () => new Response("Not found", { status: 404 }),
      },
    },
    {
      waitUntil() {},
      passThroughOnException() {},
    },
  );
}

test("server-renders the French homepage with Auto theme by default", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(html, /<html lang="fr" data-theme="auto">/);
  assert.match(
    html,
    /<title>DiveTopo · Cartes de sites de plongée<\/title>/i,
  );
  assert.match(
    html,
    /<meta name="viewport" content="width=device-width, initial-scale=1"/,
  );
  assert.match(html, /Cartographies de sites de plongée/);
  assert.doesNotMatch(html, /Le relief sous-marin, région par région\./);
  assert.doesNotMatch(html, /DiveTopo réunit des cartes/);
  assert.doesNotMatch(html, />Explorer</);
  assert.doesNotMatch(
    html,
    /Chaque région rassemble les cartes disponibles/,
  );
  assert.match(html, /La Réunion/);
  assert.match(html, /Sélection de cartes/);
  assert.match(html, /sélection non exhaustive de sept sites/);
  assert.match(html, /src="\/reunion-overview\.webp"/);
  assert.match(html, /href="https:\/\/reunion\.divetopo\.com"/);
  assert.match(html, /aria-label="Explorer La Réunion"/);
  assert.match(html, /Une page prête à accueillir d’autres régions\./);
  assert.match(html, /href="#contact">Contact<\/a>/);
  assert.match(html, /id="contact"/);
  assert.match(
    html,
    /Une question, une remarque ou un site de plongée que vous aimeriez voir cartographié(?:\u00a0|&nbsp;|&#xA0;|&#160;)\?<br\/>Écrivez-moi à/,
  );
  assert.match(html, /href="mailto:contact@divetopo\.com"/);
  assert.match(html, />contact@divetopo\.com<\/a>/);
  assert.ok(html.indexOf('id="contact"') < html.indexOf("<footer"));
  assert.doesNotMatch(html, /<form\b/i);
  assert.match(html, /href="#top">Haut de page<\/a>/);
  assert.match(
    html,
    /<button(?=[^>]*data-testid="language-fr")(?=[^>]*aria-pressed="true")[^>]*>/,
  );
  assert.match(html, /data-testid="theme-auto"[^>]*checked=""/);
  assert.match(
    html,
    /data-testid="theme-light"[\s\S]*data-testid="theme-auto"[\s\S]*data-testid="theme-dark"/,
  );
  assert.match(html, /title="Utiliser le thème du système"/);
  assert.match(html, /class="theme-choice-icon"/);
  const forbiddenProjectTerm = ["at", "las"].join("");
  assert.doesNotMatch(
    html,
    new RegExp(`${forbiddenProjectTerm}|Le projet|project-section`, "i"),
  );
  assert.match(html, /IGN RGE ALTI/);
  assert.match(html, /GEBCO Compilation Group \(2024\)/);
  assert.doesNotMatch(html, /codex-preview|Your site is taking shape/i);
});

test("uses the browser language for the English version", async () => {
  const response = await render({ "accept-language": "en-GB,en;q=0.9,fr;q=0.7" });
  const html = await response.text();

  assert.match(html, /<html lang="en" data-theme="auto">/);
  assert.match(html, /<title>DiveTopo · Dive site maps<\/title>/i);
  assert.match(
    html,
    /name="twitter:image:alt" content="DiveTopo, dive site maps"/,
  );
  assert.match(html, /Dive site maps/);
  assert.doesNotMatch(
    html,
    /Each region brings together the available maps/,
  );
  assert.match(html, /Réunion Island/);
  assert.match(html, /Map selection/);
  assert.match(html, /non-exhaustive selection of seven sites/);
  assert.match(html, /aria-label="Explore Réunion Island"/);
  assert.match(html, /Ready for more regions\./);
  assert.match(
    html,
    /Have a question, feedback, or a dive site you would like to see mapped\?<br\/>Email me at/,
  );
  assert.match(html, /href="mailto:contact@divetopo\.com"/);
  assert.match(html, /href="#top">Back to top<\/a>/);
  assert.match(
    html,
    /<button(?=[^>]*data-testid="language-en")(?=[^>]*aria-pressed="true")[^>]*>/,
  );
  assert.match(html, /title="Use system theme"/);
  assert.doesNotMatch(html, /Cartographies de sites de plongée/);
});

test("respects Accept-Language quality weights and exclusions", async () => {
  const frenchHtml = await (
    await render({
      "accept-language": "de-DE,fr;q=0.9,en;q=0.8",
    })
  ).text();
  const englishHtml = await (
    await render({
      "accept-language": "fr;q=0,en;q=1",
    })
  ).text();
  const fallbackEnglishHtml = await (
    await render({
      "accept-language": "es-ES,es;q=0.9",
    })
  ).text();

  assert.match(frenchHtml, /<html lang="fr" data-theme="auto">/);
  assert.match(frenchHtml, /Cartographies de sites de plongée/);
  assert.match(englishHtml, /<html lang="en" data-theme="auto">/);
  assert.match(englishHtml, /Dive site maps/);
  assert.match(fallbackEnglishHtml, /<html lang="en" data-theme="auto">/);
});

test("saved cookies override system language and theme", async () => {
  const response = await render({
    "accept-language": "en-US,en;q=0.9",
    cookie: "divetopo-language=fr; divetopo-theme=dark",
  });
  const html = await response.text();

  assert.match(html, /<html lang="fr" data-theme="dark">/);
  assert.match(html, /Cartographies de sites de plongée/);
  assert.match(html, /data-testid="theme-dark"[^>]*checked=""/);
  assert.doesNotMatch(html, /Dive site maps/);
});

test("keeps regions data-driven and bundles the exact island relief", async () => {
  const [
    regionsSource,
    packageJson,
    stylesheet,
    controlsSource,
    preferencesSource,
  ] = await Promise.all([
    readFile(new URL("../content/regions.ts", import.meta.url), "utf8"),
    readFile(new URL("../package.json", import.meta.url), "utf8"),
    readFile(new URL("../app/globals.css", import.meta.url), "utf8"),
    readFile(new URL("../app/PreferenceControls.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/preferences.ts", import.meta.url), "utf8"),
  ]);

  assert.match(regionsSource, /export const regions/);
  assert.match(regionsSource, /https:\/\/reunion\.divetopo\.com/);
  assert.match(regionsSource, /reunion-overview\.webp/);
  assert.match(regionsSource, /fr:\s*"La Réunion"/);
  assert.match(regionsSource, /en:\s*"Réunion Island"/);
  assert.match(stylesheet, /:root\[data-theme="dark"\]/);
  assert.match(
    stylesheet,
    /@media \(prefers-color-scheme: dark\)[\s\S]*:root\[data-theme="auto"\]/,
  );
  assert.match(
    stylesheet,
    /\.hero\s*\{[^}]*padding:\s*clamp\(2\.75rem,\s*5vw,\s*5\.25rem\)/s,
  );
  assert.match(
    stylesheet,
    /main\s*\{[^}]*radial-gradient\(circle at 82% 4rem,\s*var\(--hero-glow\),\s*transparent 30rem\)/s,
  );
  assert.doesNotMatch(stylesheet, /\.hero\s*\{[^}]*background:/s);
  assert.match(
    stylesheet,
    /\.brand\s*\{[^}]*font-size:\s*clamp\(0\.88rem,\s*1\.15vw,\s*1\.04rem\);[^}]*font-weight:\s*700;/s,
  );
  assert.match(
    stylesheet,
    /\.site-footer\s*\{[^}]*min-height:\s*7rem;[^}]*padding:\s*1\.5rem var\(--page-gutter\);/s,
  );
  assert.doesNotMatch(stylesheet, /\.hero-lead\s*\{/);
  assert.doesNotMatch(stylesheet, /\.section-heading\s*\{[^}]*border-top:/s);
  assert.match(stylesheet, /\.region-card\s*\{[^}]*max-width:\s*30rem;/s);
  assert.match(controlsSource, /document\.cookie/);
  assert.match(controlsSource, /Domain=\.divetopo\.com/);
  assert.match(controlsSource, /onLanguageChange\(nextLanguage\)/);
  assert.match(controlsSource, /className="language-choice"/);
  assert.match(controlsSource, /flushSync/);
  assert.match(controlsSource, /window\.history\.replaceState/);
  assert.match(
    controlsSource,
    /window\.scrollTo\(scrollPosition\.left, scrollPosition\.top\)/,
  );
  assert.doesNotMatch(controlsSource, /window\.location\.reload/);
  assert.match(
    controlsSource,
    /document\.documentElement\.setAttribute\("data-theme"/,
  );
  assert.doesNotMatch(controlsSource, /localStorage/);
  assert.match(preferencesSource, /accept-language/);
  assert.match(preferencesSource, /cookies\(\)/);
  assert.doesNotMatch(packageJson, /react-loading-skeleton|drizzle/);
  await access(new URL("../public/reunion-overview.webp", import.meta.url));
  await access(new URL("../public/og.png", import.meta.url));
});
