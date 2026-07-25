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

function extractFooter(html) {
  const footer = html.match(/<footer\b[\s\S]*?<\/footer>/i)?.[0];
  assert.ok(footer, "expected the rendered page to contain a footer");
  return footer;
}

async function readPngDimensions(path) {
  const png = await readFile(path);
  assert.deepEqual(
    [...png.subarray(0, 8)],
    [137, 80, 78, 71, 13, 10, 26, 10],
    `${path.pathname} must have a valid PNG signature`,
  );
  assert.equal(
    png.toString("ascii", 12, 16),
    "IHDR",
    `${path.pathname} must begin with an IHDR chunk`,
  );

  return {
    width: png.readUInt32BE(16),
    height: png.readUInt32BE(20),
  };
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
  assert.doesNotMatch(html, /Choisissez une région/);
  assert.match(html, /La Réunion/);
  assert.doesNotMatch(html, /Sélection de cartes/);
  assert.match(html, /sélection non exhaustive de sept sites/);
  assert.match(html, /src="\/reunion-overview\.webp"/);
  assert.match(html, /href="https:\/\/reunion\.divetopo\.com"/);
  assert.match(html, /aria-label="Explorer La Réunion"/);
  assert.match(html, /<section[^>]*aria-label="Régions"[^>]*>/);
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
  const footer = extractFooter(html);
  assert.match(footer, /Accès gratuit/);
  assert.match(footer, /sans publicité/);
  assert.match(footer, /code sous licence/);
  assert.match(
    footer,
    /href="https:\/\/opensource\.org\/license\/mit"[^>]*>MIT<\/a>/,
  );
  assert.match(footer, /cartes sous licence/);
  assert.match(
    footer,
    /href="https:\/\/creativecommons\.org\/licenses\/by-nc-sa\/4\.0\/deed\.fr"[^>]*>CC BY-NC-SA 4\.0<\/a>/,
  );
  assert.match(footer, /IGN RGE ALTI/);
  assert.match(footer, /GEBCO Compilation Group \(2024\)/);
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
  assert.doesNotMatch(html, /Choose a region/);
  assert.match(html, /Réunion Island/);
  assert.doesNotMatch(html, /Map selection/);
  assert.match(html, /non-exhaustive selection of seven sites/);
  assert.match(html, /aria-label="Explore Réunion Island"/);
  assert.match(html, /<section[^>]*aria-label="Regions"[^>]*>/);
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
  const footer = extractFooter(html);
  assert.match(footer, /Free access/);
  assert.match(footer, /ad-free/);
  assert.match(footer, /code under the/);
  assert.match(
    footer,
    /href="https:\/\/opensource\.org\/license\/mit"[^>]*>MIT License<\/a>/,
  );
  assert.match(footer, /maps under/);
  assert.match(
    footer,
    /href="https:\/\/creativecommons\.org\/licenses\/by-nc-sa\/4\.0\/deed\.en"[^>]*>CC BY-NC-SA 4\.0<\/a>/,
  );
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
  assert.doesNotMatch(stylesheet, /\.section-heading\s*\{/);
  assert.doesNotMatch(stylesheet, /\.region-status\s*\{/);
  assert.doesNotMatch(
    stylesheet,
    /\.contact-inner p\s*\{[^}]*max-width:/s,
  );
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

test("advertises the standalone DiveTopo app identity in server-rendered metadata", async () => {
  const response = await render();
  const html = await response.text();

  assert.match(
    html,
    /<link rel="manifest" href="\/manifest\.webmanifest"\/>/,
  );
  assert.match(
    html,
    /<meta name="application-name" content="DiveTopo"\/>/,
  );
  assert.match(
    html,
    /<meta name="mobile-web-app-capable" content="yes"\/>/,
  );
  assert.match(
    html,
    /<meta name="apple-mobile-web-app-capable" content="yes"\/>/,
  );
  assert.match(
    html,
    /<meta name="apple-mobile-web-app-title" content="DiveTopo"\/>/,
  );
  assert.match(
    html,
    /<link rel="apple-touch-icon" href="\/apple-touch-icon\.png" sizes="180x180" type="image\/png"\/>/,
  );
  assert.match(
    html,
    /<link rel="icon" href="\/favicon\.svg" type="image\/svg\+xml"\/>/,
  );
  assert.match(html, /<link rel="shortcut icon" href="\/favicon\.svg"\/>/);
});

test("ships a scoped standalone manifest and correctly sized PNG icons", async () => {
  const manifestPath = new URL(
    "../public/manifest.webmanifest",
    import.meta.url,
  );
  const manifest = JSON.parse(await readFile(manifestPath, "utf8"));

  assert.equal(manifest.name, "DiveTopo");
  assert.equal(manifest.short_name, "DiveTopo");
  assert.equal(manifest.id, "/");
  assert.equal(manifest.start_url, "/");
  assert.equal(manifest.scope, "/");
  assert.equal(manifest.display, "standalone");
  assert.deepEqual(manifest.icons, [
    {
      src: "/app-icon-192.png",
      sizes: "192x192",
      type: "image/png",
      purpose: "any maskable",
    },
    {
      src: "/app-icon-512.png",
      sizes: "512x512",
      type: "image/png",
      purpose: "any maskable",
    },
  ]);

  const iconSizes = await Promise.all([
    readPngDimensions(
      new URL("../public/apple-touch-icon.png", import.meta.url),
    ),
    readPngDimensions(new URL("../public/app-icon-192.png", import.meta.url)),
    readPngDimensions(new URL("../public/app-icon-512.png", import.meta.url)),
  ]);
  assert.deepEqual(iconSizes, [
    { width: 180, height: 180 },
    { width: 192, height: 192 },
    { width: 512, height: 512 },
  ]);
});

test("keeps install suggestions delayed, dismissible, and standalone-aware", async () => {
  const source = await readFile(
    new URL("../app/InstallPrompt.tsx", import.meta.url),
    "utf8",
  );

  assert.match(source, /beforeinstallprompt/);
  assert.match(source, /appinstalled/);
  assert.match(source, /\(display-mode: standalone\)/);
  assert.match(source, /navigatorWithStandalone\.standalone/);
  assert.match(source, /DISPLAY_DELAY_MS\s*=\s*3_000/);
  assert.match(
    source,
    /DISMISSAL_DURATION_MS\s*=\s*30\s*\*\s*24\s*\*\s*60\s*\*\s*60\s*\*\s*1000/,
  );
  assert.match(
    source,
    /window\.localStorage\.getItem\(DISMISSAL_STORAGE_KEY\)/,
  );
  assert.match(
    source,
    /window\.localStorage\.setItem\(DISMISSAL_STORAGE_KEY/,
  );
  assert.match(source, /event\.preventDefault\(\)/);
  assert.match(source, /await promptEvent\.prompt\(\)/);
  assert.match(source, /await promptEvent\.userChoice/);
});
