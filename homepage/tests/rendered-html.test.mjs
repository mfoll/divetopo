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
  assert.match(html, /Le relief sous-marin, région par région\./);
  assert.match(html, /La Réunion/);
  assert.match(html, /src="\/reunion-overview\.webp"/);
  assert.match(html, /href="https:\/\/reunion\.divetopo\.com"/);
  assert.match(html, /aria-label="Explorer les cartes de La Réunion"/);
  assert.match(html, /Une page prête à accueillir d’autres régions\./);
  assert.match(html, /data-testid="language-fr"[^>]*checked=""/);
  assert.match(html, /data-testid="theme-auto"[^>]*checked=""/);
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
  assert.match(html, /Underwater terrain, region by region\./);
  assert.match(html, /Réunion Island/);
  assert.match(html, /aria-label="Explore maps of Réunion Island"/);
  assert.match(html, /Ready for more regions\./);
  assert.match(html, /data-testid="language-en"[^>]*checked=""/);
  assert.doesNotMatch(html, /Le relief sous-marin, région par région\./);
});

test("respects Accept-Language quality weights and exclusions", async () => {
  const preferredFrench = await render({
    "accept-language": "de-DE,fr;q=0.9,en;q=0.8",
  });
  const excludedFrench = await render({
    "accept-language": "fr;q=0,en;q=1",
  });
  const [frenchHtml, englishHtml] = await Promise.all([
    preferredFrench.text(),
    excludedFrench.text(),
  ]);

  assert.match(frenchHtml, /<html lang="fr" data-theme="auto">/);
  assert.match(frenchHtml, /Le relief sous-marin, région par région\./);
  assert.match(englishHtml, /<html lang="en" data-theme="auto">/);
  assert.match(englishHtml, /Underwater terrain, region by region\./);
});

test("saved cookies override system language and theme", async () => {
  const response = await render({
    "accept-language": "en-US,en;q=0.9",
    cookie: "divetopo-language=fr; divetopo-theme=dark",
  });
  const html = await response.text();

  assert.match(html, /<html lang="fr" data-theme="dark">/);
  assert.match(html, /Le relief sous-marin, région par région\./);
  assert.match(html, /data-testid="theme-dark"[^>]*checked=""/);
  assert.doesNotMatch(html, /Underwater terrain, region by region\./);
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
  assert.match(regionsSource, /en:\s*"Réunion Island"/);
  assert.match(stylesheet, /:root\[data-theme="dark"\]/);
  assert.match(
    stylesheet,
    /@media \(prefers-color-scheme: dark\)[\s\S]*:root\[data-theme="auto"\]/,
  );
  assert.match(stylesheet, /\.hero h1\s*\{[^}]*grid-column:\s*1;/s);
  assert.match(stylesheet, /\.hero-lead\s*\{[^}]*grid-column:\s*2;/s);
  assert.match(stylesheet, /\.region-card\s*\{[^}]*max-width:\s*30rem;/s);
  assert.match(controlsSource, /document\.cookie/);
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
