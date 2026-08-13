import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import test from "node:test";

async function render(pathname = "/fr", requestHeaders = {}) {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}-${Math.random()}`);
  const { default: worker } = await import(workerUrl.href);

  return worker.fetch(
    new Request(`http://localhost${pathname}`, {
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

test("redirects the root URL using cookie then browser language", async () => {
  const defaultResponse = await render("/");
  const englishResponse = await render("/", {
    "accept-language": "en-GB,en;q=0.9,fr;q=0.7",
  });
  const cookieResponse = await render("/", {
    "accept-language": "en-US,en;q=0.9",
    cookie: "divetopo-language=fr",
  });

  assert.equal(defaultResponse.status, 307);
  assert.equal(defaultResponse.headers.get("location"), "http://localhost/fr");
  assert.equal(englishResponse.status, 307);
  assert.equal(englishResponse.headers.get("location"), "http://localhost/en");
  assert.equal(cookieResponse.status, 307);
  assert.equal(cookieResponse.headers.get("location"), "http://localhost/fr");
});

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
    /<link rel="canonical" href="https:\/\/divetopo\.com\/fr"/,
  );
  assert.match(
    html,
    /<link rel="alternate" hrefLang="fr" href="https:\/\/divetopo\.com\/fr"/i,
  );
  assert.match(
    html,
    /<link rel="alternate" hrefLang="en" href="https:\/\/divetopo\.com\/en"/i,
  );
  assert.match(
    html,
    /<link rel="alternate" hrefLang="x-default" href="https:\/\/divetopo\.com\/"/i,
  );
  assert.match(html, /type="application\/ld\+json"/);
  assert.match(html, /"@type":"WebPage"/);
  assert.match(html, /"@type":"ImageObject"/);
  assert.match(html, /"primaryImageOfPage"/);
  assert.match(html, /"encodingFormat":"image\/png"/);
  assert.match(html, /"creditText":"DiveTopo"/);
  assert.match(
    html,
    /"acquireLicensePage":"https:\/\/github\.com\/mfoll\/divetopo\/blob\/main\/LICENSE-MAPS\.md"/,
  );
  assert.match(html, /"inLanguage":"fr"/);
  assert.match(
    html,
    /<meta name="viewport" content="[^"]*width=device-width[^"]*initial-scale=1/,
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
  assert.match(html, /sélection non exhaustive de onze sites/);
  assert.match(html, /<li>11 sites<\/li>/);
  assert.match(html, /src="\/reunion-overview\.webp"/);
  assert.match(html, /href="\/reunion\/fr"/);
  assert.match(html, /aria-label="Explorer La Réunion"/);
  assert.doesNotMatch(html, /region-arrow|↗/);
  assert.doesNotMatch(html, /brand-home-cue/);
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
  assert.match(footer, /Site et code entièrement générés avec l’IA/);
  assert.match(
    footer,
    /Mesure d’audience agrégée, sans cookies, avec Cloudflare Web Analytics/,
  );
  assert.equal(
    [
      ...html.matchAll(
        /<script[^>]*src="https:\/\/static\.cloudflareinsights\.com\/beacon\.min\.js"[^>]*>/g,
      ),
    ].length,
    1,
  );
  assert.match(
    html,
    /<script[^>]*data-cf-beacon="\{&quot;token&quot;:&quot;32f973b9bb49455089575acc50377b05&quot;\}"[^>]*src="https:\/\/static\.cloudflareinsights\.com\/beacon\.min\.js"[^>]*type="module"/,
  );
  assert.doesNotMatch(html, /codex-preview|Your site is taking shape/i);
});

test("uses the browser language for the English version", async () => {
  const response = await render("/en", {
    "accept-language": "fr-FR,fr;q=0.9",
    cookie: "divetopo-language=fr",
  });
  const html = await response.text();

  assert.match(html, /<html lang="en" data-theme="auto">/);
  assert.match(html, /<title>DiveTopo · Dive site maps<\/title>/i);
  assert.match(
    html,
    /<link rel="canonical" href="https:\/\/divetopo\.com\/en"/,
  );
  assert.match(html, /"inLanguage":"en"/);
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
  assert.match(html, /href="\/reunion\/en"/);
  assert.doesNotMatch(html, /Map selection/);
  assert.match(html, /non-exhaustive selection of eleven sites/);
  assert.match(html, /<li>11 sites<\/li>/);
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
  assert.match(footer, /Site and code generated entirely with AI/);
  assert.match(
    footer,
    /Aggregated, cookie-free audience measurement with Cloudflare Web Analytics/,
  );
});

test("respects Accept-Language quality weights and exclusions", async () => {
  const frenchResponse = await render("/", {
    "accept-language": "de-DE,fr;q=0.9,en;q=0.8",
  });
  const englishResponse = await render("/", {
    "accept-language": "fr;q=0,en;q=1",
  });
  const fallbackEnglishResponse = await render("/", {
    "accept-language": "es-ES,es;q=0.9",
  });

  assert.equal(frenchResponse.headers.get("location"), "http://localhost/fr");
  assert.equal(englishResponse.headers.get("location"), "http://localhost/en");
  assert.equal(
    fallbackEnglishResponse.headers.get("location"),
    "http://localhost/en",
  );
});

test("saved cookies override system language and theme", async () => {
  const response = await render("/fr", {
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
    homepageSource,
    packageJson,
    stylesheet,
    controlsSource,
    preferencesSource,
    regionalManifestSource,
  ] = await Promise.all([
    readFile(new URL("../content/regions.ts", import.meta.url), "utf8"),
    readFile(new URL("../app/HomepageExperience.tsx", import.meta.url), "utf8"),
    readFile(new URL("../package.json", import.meta.url), "utf8"),
    readFile(new URL("../app/globals.css", import.meta.url), "utf8"),
    readFile(new URL("../app/PreferenceControls.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/preferences.ts", import.meta.url), "utf8"),
    readFile(
      new URL("../content/bouches-du-rhone-map-manifest.json", import.meta.url),
      "utf8",
    ),
  ]);

  assert.match(regionsSource, /export const regions/);
  assert.match(regionsSource, /href:\s*"\/reunion"/);
  assert.match(regionsSource, /reunion-overview\.webp/);
  assert.match(regionsSource, /regionalMapManifests\[region\]/);
  assert.match(regionsSource, /manifest\.westCoastLocator\.src/);
  assert.match(regionsSource, /manifest\.westCoastLocator\.width/);
  assert.match(regionsSource, /manifest\.westCoastLocator\.height/);
  assert.match(regionsSource, /sitePositions:\s*manifest\.sites\.map/);
  assert.match(regionsSource, /site\.reunionOverviewPosition/);
  assert.match(homepageSource, /className="region-site-points"/);
  assert.match(homepageSource, /spreadNearbyPoints\(region\.sitePositions\)/);
  assert.match(regionalManifestSource, /"detailBathymetryLayer":\s*"LITTO3D PACA 2015 MNT5m"/);
  assert.match(regionalManifestSource, /"detailBathymetryCrs":\s*"EPSG:2154"/);
  assert.match(regionalManifestSource, /"detailBathymetryResolutionM":\s*5/);
  assert.match(
    regionalManifestSource,
    /"coastlineLayer":\s*"LIMTM_2154_WFS:limite_terre_mer_france_metropolitaine_polygones"/,
  );
  assert.match(
    regionalManifestSource,
    /"coastlineSource":\s*"Shom–IGN Limite terre-mer official land polygons/,
  );
  assert.match(regionalManifestSource, /"marineLayer":\s*"emodnet:mean"/);
  assert.match(
    regionalManifestSource,
    /"marineResolution":\s*"1\/16 arc minute native DTM grid \(~115 m\)"/,
  );
  assert.match(regionsSource, /name:\s*catalog\.names/);
  assert.match(stylesheet, /:root\[data-theme="dark"\]/);
  assert.match(
    stylesheet,
    /@media \(prefers-color-scheme: dark\)[\s\S]*:root\[data-theme="auto"\]/,
  );
  assert.match(
    stylesheet,
    /\.homepage-main \.hero\s*\{[^}]*padding:\s*clamp\(2\.75rem,\s*5vw,\s*5\.25rem\)/s,
  );
  assert.match(
    stylesheet,
    /\.homepage-main\s*\{[^}]*radial-gradient\(circle at 82% 4rem,\s*var\(--topo-glow\),\s*transparent 30rem\)/s,
  );
  assert.doesNotMatch(stylesheet, /\.homepage-main \.hero\s*\{[^}]*background:/s);
  assert.match(
    stylesheet,
    /\.brand\s*\{[^}]*font-size:\s*clamp\(0\.88rem,\s*1\.15vw,\s*1\.04rem\);[^}]*font-weight:\s*700;/s,
  );
  assert.match(
    stylesheet,
    /\.masthead \.brand-wordmark\s*\{[^}]*font-size:\s*clamp\(1\.05rem,\s*1\.35vw,\s*1\.18rem\);/s,
  );
  assert.match(
    stylesheet,
    /@media \(max-width:\s*560px\)[\s\S]*\.masthead \.brand-wordmark\s*\{[^}]*font-size:\s*1\.08rem;/s,
  );
  assert.match(
    stylesheet,
    /@media \(max-width:\s*560px\)[\s\S]*\.masthead\s*\{[^}]*max-inline-size:\s*100vw;[^}]*overflow-x:\s*clip;/s,
  );
  assert.match(
    stylesheet,
    /@media \(max-width:\s*560px\)[\s\S]*\.masthead-inner\s*\{[^}]*inline-size:\s*100vw;[^}]*max-inline-size:\s*100vw;/s,
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
  assert.match(stylesheet, /\.region-card\s*\{[^}]*max-width:\s*20rem;/s);
  assert.match(
    stylesheet,
    /\.homepage-main \.region-site-point\s*\{[^}]*height:\s*0\.34rem;[^}]*width:\s*0\.34rem;/s,
  );
  assert.match(
    stylesheet,
    /\.homepage-main \.region-grid\s*\{[^}]*grid-template-columns:\s*repeat\(4, minmax\(0, 20rem\)\);/s,
  );
  assert.match(
    stylesheet,
    /\.homepage-main \.region-visual img\s*\{[^}]*aspect-ratio:\s*auto;/s,
  );
  assert.match(controlsSource, /document\.cookie/);
  assert.match(controlsSource, /Domain=\.divetopo\.com/);
  assert.match(controlsSource, /className="language-choice"/);
  assert.match(
    controlsSource,
    /window\.location\.assign\(`\/\$\{nextLanguage\}\$\{window\.location\.search\}`\)/,
  );
  assert.doesNotMatch(controlsSource, /flushSync/);
  assert.doesNotMatch(controlsSource, /window\.history/);
  assert.doesNotMatch(controlsSource, /window\.location\.hash/);
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
  await access(new URL("../public/reunion-og.png", import.meta.url));
});

test("advertises the standalone DiveTopo app identity in server-rendered metadata", async () => {
  const response = await render();
  const html = await response.text();

  assert.match(
    html,
    /<link rel="manifest" href="https:\/\/divetopo\.com\/manifest\.webmanifest"\/>/,
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
    /<link rel="apple-touch-icon" href="https:\/\/divetopo\.com\/apple-touch-icon\.png" sizes="180x180" type="image\/png"\/>/,
  );
  assert.match(
    html,
    /<link rel="icon" href="https:\/\/divetopo\.com\/favicon\.svg" type="image\/svg\+xml"\/>/,
  );
  assert.match(
    html,
    /<link rel="shortcut icon" href="https:\/\/divetopo\.com\/favicon\.svg"\/>/,
  );
});

test("publishes crawlable robots and localized sitemap routes", async () => {
  const robotsResponse = await render("/robots.txt");
  const sitemapResponse = await render("/sitemap.xml");
  const robots = await robotsResponse.text();
  const sitemap = await sitemapResponse.text();

  assert.equal(robotsResponse.status, 200);
  assert.match(
    robotsResponse.headers.get("content-type") ?? "",
    /^text\/plain\b/i,
  );
  assert.match(robots, /User-Agent: \*/);
  assert.match(robots, /Allow: \//);
  assert.match(robots, /Host: https:\/\/divetopo\.com/);
  assert.match(
    robots,
    /Sitemap: https:\/\/divetopo\.com\/sitemap\.xml/,
  );

  assert.equal(sitemapResponse.status, 200);
  assert.match(
    sitemapResponse.headers.get("content-type") ?? "",
    /^(?:application|text)\/xml\b/i,
  );
  assert.match(sitemap, /https:\/\/divetopo\.com\/fr</);
  assert.match(sitemap, /https:\/\/divetopo\.com\/en</);
  assert.match(sitemap, /hreflang="fr"/);
  assert.match(sitemap, /hreflang="en"/);
  assert.match(sitemap, /hreflang="x-default"/);
  assert.match(
    sitemap,
    /<image:image>\s*<image:loc>https:\/\/divetopo\.com\/og\.png<\/image:loc>\s*<\/image:image>/,
  );
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
