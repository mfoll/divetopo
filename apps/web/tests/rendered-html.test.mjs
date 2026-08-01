import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { access, readFile } from "node:fs/promises";
import test from "node:test";
import {
  bathymetryColorCss,
  bathymetryColorRgb,
} from "../app/bathymetryPalette.mjs";
import { coveredOrthographicHalfExtents } from "../app/terrainCamera.mjs";

const templateRoot = new URL("../", import.meta.url);
const publishedSiteSlugs = new Set([
  "boucan-canot",
  "cap-homard",
  "cap-la-houssaye",
  "passe-hermitage",
  "plage-cimetiere-saint-leu",
  "pointe-des-aigrettes",
  "pointe-au-sel-sec-jaune",
  "pont-rouge",
  "roches-noires",
  "souris-chaude",
  "trois-bassins",
]);
const regionalMetadataDescriptions = {
  fr: "Plans topo-bathymétriques 2D et vues 3D interactives de sites de plongée à La Réunion.",
  en: "Explore 2D topographic-bathymetric maps and interactive 3D views of dive sites around Réunion Island.",
};

async function render(pathOrHeaders = "/reunion/fr", additionalHeaders = {}) {
  const path =
    typeof pathOrHeaders === "string" ? pathOrHeaders : "/reunion/fr";
  const requestHeaders =
    typeof pathOrHeaders === "string"
      ? additionalHeaders
      : pathOrHeaders;
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set(
    "test",
    `${process.pid}-${Date.now()}-${Math.random()}`,
  );
  const { default: worker } = await import(workerUrl.href);

  return worker.fetch(
    new Request(`http://localhost${path}`, {
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

function extractH1(html) {
  const heading = html.match(/<h1\b[\s\S]*?<\/h1>/i)?.[0];
  assert.ok(heading, "expected the rendered page to contain an H1");
  return visibleText(heading);
}

function visibleText(html) {
  return html
    .replace(/<!--[\s\S]*?-->/g, "")
    .replace(/<[^>]+>/g, "")
    .replace(/&nbsp;|&#xA0;|&#160;/gi, "\u00a0")
    .replace(/&copy;|&#xA9;|&#169;/gi, "©")
    .replace(/&#x27;|&#39;/gi, "'")
    .replace(/\s+/g, " ")
    .trim();
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

test("server-renders the French Topo Réunion page with Auto theme by default", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(html, /<html lang="fr" data-theme="auto">/);
  assert.match(
    html,
    /<title>Plans des sites de plongée à La Réunion<\/title>/i,
  );
  assert.match(
    html,
    /<link rel="canonical" href="https:\/\/divetopo\.com\/reunion\/fr"\/>/,
  );
  assert.match(
    html,
    /<link rel="alternate" hrefLang="en" href="https:\/\/divetopo\.com\/reunion\/en"\/>/,
  );
  assert.match(
    html,
    /<link rel="alternate" hrefLang="x-default" href="https:\/\/divetopo\.com\/reunion"\/>/,
  );
  assert.match(html, /"@type":"CollectionPage"/);
  assert.match(html, /"@type":"ItemList"/);
  assert.match(html, /aria-label="DiveTopo, revenir au site principal"/);
  assert.match(html, /href="\/fr"/);
  assert.match(html, /class="brand-home-cue" aria-hidden="true">←<\/span>/);
  assert.match(html, /class="brand-wordmark">DiveTopo<\/span>/);
  assert.match(html, /Plans des sites de plongée à La Réunion/);
  assert.match(
    html,
    /<h1 id="topo-reunion-title">Plans des sites de plongée à La Réunion<\/h1>/,
  );
  assert.match(
    html,
    /name="description" content="Plans topo-bathymétriques 2D et vues 3D interactives de sites de plongée à La Réunion\."/,
  );
  assert.doesNotMatch(
    html,
    /Une sélection non exhaustive de sites de plongée de la côte ouest\./,
  );
  assert.match(html, /Boucan Canot/);
  assert.match(html, /Cap La Houssaye/);
  assert.match(html, /Cap Homard/);
  assert.match(html, /Passe de l(?:'|&#x27;)Hermitage/);
  assert.match(html, /Pont Rouge/);
  assert.match(html, /Plage du Cimetière/);
  assert.match(html, /Pointe au Sel/);
  assert.match(html, /Saint-Paul/);
  assert.match(html, /21° 01′ 02\.5″ S/);
  assert.match(html, /Voir le site sur Google Maps/);
  assert.match(html, /google\.com\/maps\/search/);
  assert.match(html, /3d-dynamic-orthophoto-2474\.webp/);
  assert.match(html, /reunion-overview\.webp/);
  assert.match(html, /west-coast-locator\.webp/);
  assert.doesNotMatch(html, /Ouvrir .* en grand/);
  assert.doesNotMatch(html, /class="site-picker-range"/);
  assert.doesNotMatch(html, /Cap → Saint-Leu/);
  assert.doesNotMatch(html, /Sur l’île/);
  assert.doesNotMatch(html, /locator-640\.webp/);
  assert.doesNotMatch(html, /locator-1600\.webp/);
  assert.doesNotMatch(html, /Agrandir la carte/);
  assert.doesNotMatch(html, /Repère\s*:/);
  assert.match(html, /Planche HD à imprimer/);
  assert.match(html, /Télécharger la planche HD/);
  assert.match(
    html,
    /Télécharger la vue 3D de Cap La Houssaye, avec un fond en vue aérienne/,
  );
  assert.match(
    html,
    /href="\/maps\/cap-la-houssaye\/downloads\/3d-dynamic-orthophoto-full\.jpg"/,
  );
  assert.match(
    html,
    /download="cap-la-houssaye-3d-dynamique-orthophoto\.jpg"/,
  );
  assert.match(html, /Topographie/);
  assert.match(html, /Vue aérienne/);
  assert.match(html, /Imagerie aérienne géoréférencée IGN BD ORTHO/i);
  assert.doesNotMatch(html, />3D interactive<\/button>/);
  assert.doesNotMatch(html, /Vue 3D · (?:Vue aérienne|Topographie)/);
  assert.match(html, /Données, méthode et licences/);
  assert.match(html, /données bathymétriques/);
  assert.match(html, /WGS 84 \/ UTM 40S \(EPSG:32740\)/);
  assert.match(html, /Grille bathymétrique GEBCO 2024/);
  assert.match(html, /Méthode de production/);
  assert.match(html, /empreinte SHA-256/);
  assert.match(html, /opaque jusqu’à −1,5 m/);
  assert.match(html, /normales métriques/);
  assert.match(html, /champ d’altitude 16 bits/);
  assert.match(
    html,
    /Le code et les interfaces du site ont été entièrement générés avec l’IA/,
  );
  assert.match(html, /https:\/\/github\.com\/mfoll\/divetopo/);
  assert.match(html, /GitHub \(nouvelle fenêtre\)/);
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
  assert.match(html, /Sélectionnez un site sur la carte\./);
  assert.match(
    html,
    /<a(?=[^>]*class="site-map-marker label-right")(?=[^>]*data-selected="true")(?=[^>]*href="\/reunion\/fr\/sites\/cap-la-houssaye")[^>]*>/,
  );
  assert.doesNotMatch(html, /aria-current="page"/);
  assert.match(html, /href="\/reunion\/fr\/sites\/cap-homard"/);
  assert.match(html, /href="\/reunion\/fr\/sites\/pointe-des-aigrettes"/);
  assert.match(
    html,
    /href="\/reunion\/fr\/sites\/roches-noires"/,
  );
  assert.match(html, /Roches Noires/);
  assert.doesNotMatch(html, /Roches Noires - Le Cimetière/);
  assert.match(html, /href="\/reunion\/fr\/sites\/trois-bassins"/);
  assert.match(html, /href="\/reunion\/fr\/sites\/souris-chaude"/);
  assert.match(
    html,
    /<button(?=[^>]*data-testid="language-fr")(?=[^>]*aria-pressed="true")[^>]*>/,
  );
  assert.match(html, /data-testid="theme-auto"[^>]*checked=""/);
  assert.match(
    html,
    /data-testid="theme-light"[\s\S]*data-testid="theme-auto"[\s\S]*data-testid="theme-dark"/,
  );
  assert.match(html, /title="Utiliser le thème clair"/);
  assert.match(html, /title="Utiliser le thème du système"/);
  assert.match(html, /title="Utiliser le thème sombre"/);
  assert.match(html, /class="theme-choice-icon"/);
  assert.match(html, /https:\/\/doi\.org\/10\.12770\/ee059de2/);
  assert.doesNotMatch(html, /Lire la côte sous la surface/);
  assert.doesNotMatch(html, /Trois reliefs, trois lectures de la côte/);
  assert.doesNotMatch(html, /Plans 2D, vues 3D et reliefs interactifs\./);
  assert.doesNotMatch(html, /Cartes et reliefs/);
  assert.doesNotMatch(
    html,
    /Une même chaîne de production pour tous les formats/,
  );
  assert.doesNotMatch(html, /02\s*\/\s*Les sites/i);
  assert.doesNotMatch(html, /id="explorer"/);
  assert.doesNotMatch(html, /codex-preview|Building your site|SkeletonPreview/);
  const footer = extractFooter(html);
  assert.match(
    visibleText(footer),
    /Accès gratuit · sans publicité · code sous licence MIT · cartes sous licence CC BY-NC-SA 4\.0/,
  );
  assert.match(
    visibleText(footer),
    /Mesure d’audience agrégée, sans cookies, avec Cloudflare Web Analytics/,
  );
  assert.match(
    footer,
    /href="https:\/\/opensource\.org\/license\/mit"[^>]*>MIT<\/a>/,
  );
  assert.match(
    footer,
    /href="https:\/\/creativecommons\.org\/licenses\/by-nc-sa\/4\.0\/deed\.fr"[^>]*>CC BY-NC-SA 4\.0<\/a>/,
  );
  assert.match(
    visibleText(footer),
    /Plans © 2026 Matthieu Foll · CC BY-NC-SA 4\.0/,
  );
});

test("lets the contact question use the full available text column", async () => {
  const stylesheet = await readFile(
    new URL("../app/globals.css", import.meta.url),
    "utf8",
  );

  assert.doesNotMatch(
    stylesheet,
    /\.contact-inner p\s*\{[^}]*max-width:/s,
  );
});

test("uses the browser language for the English Topo Réunion page", async () => {
  const response = await render("/reunion/en", {
    "accept-language": "fr-FR,fr;q=0.9",
  });
  const html = await response.text();

  assert.match(html, /<html lang="en" data-theme="auto">/);
  assert.match(html, /<title>Dive site maps of Réunion Island<\/title>/i);
  assert.match(html, /property="og:locale" content="en_GB"/);
  assert.match(
    html,
    /name="twitter:image:alt" content="Dive site maps of Réunion Island"/,
  );
  assert.match(
    html,
    /property="og:image" content="https:\/\/divetopo\.com\/reunion-og\.png"/,
  );
  assert.match(html, /Dive site maps of Réunion Island/);
  assert.match(
    html,
    /<h1 id="topo-reunion-title">Dive site maps of Réunion Island<\/h1>/,
  );
  assert.match(
    html,
    /name="description" content="Explore 2D topographic-bathymetric maps and interactive 3D views of dive sites around Réunion Island\."/,
  );
  assert.doesNotMatch(
    html,
    /A non-exhaustive selection of dive sites along the west coast\./,
  );
  assert.match(html, /Saint-Paul<!-- -->, <!-- -->Réunion Island/);
  assert.match(html, /View site on Google Maps/);
  assert.match(html, />2D map<\/button>/);
  assert.match(html, />3D view<\/button>/);
  assert.doesNotMatch(html, />Interactive 3D<\/button>/);
  assert.match(html, />Aerial imagery<\/button>/);
  assert.match(html, /Download the 3D view of Cap La Houssaye/);
  assert.match(html, /Printable high-resolution map sheet/);
  assert.match(html, /Data, method and licences/);
  assert.match(html, /Production method/);
  assert.match(html, /Sources and cache validation/);
  assert.match(html, /opaque to −1\.5 m/);
  assert.match(
    html,
    /The code and website interfaces were generated entirely with AI/,
  );
  assert.match(html, /Safety/);
  assert.match(
    html,
    /Have a question, feedback, or a dive site you would like to see mapped\?<br\/>Email me at/,
  );
  assert.match(html, /href="mailto:contact@divetopo\.com"/);
  assert.match(html, /deed\.en/);
  assert.match(
    html,
    /<button(?=[^>]*data-testid="language-en")(?=[^>]*aria-pressed="true")[^>]*>/,
  );
  assert.match(html, /title="Use light theme"/);
  assert.match(html, /title="Use system theme"/);
  assert.match(html, /title="Use dark theme"/);
  assert.match(html, /aria-label="DiveTopo, return to the main website"/);
  assert.doesNotMatch(html, /Voir le site sur Google Maps/);
  assert.doesNotMatch(html, /Données, méthode et licences/);
  const footer = extractFooter(html);
  assert.match(
    visibleText(footer),
    /Free access · ad-free · code under the MIT License · maps under CC BY-NC-SA 4\.0/,
  );
  assert.match(
    visibleText(footer),
    /Aggregated, cookie-free audience measurement with Cloudflare Web Analytics/,
  );
  assert.match(
    footer,
    /href="https:\/\/opensource\.org\/license\/mit"[^>]*>MIT License<\/a>/,
  );
  assert.match(
    footer,
    /href="https:\/\/creativecommons\.org\/licenses\/by-nc-sa\/4\.0\/deed\.en"[^>]*>CC BY-NC-SA 4\.0<\/a>/,
  );
  assert.match(
    visibleText(footer),
    /Maps © 2026 Matthieu Foll · CC BY-NC-SA 4\.0/,
  );
});

test("server-renders an indexable localized page for every published site", async () => {
  const manifest = JSON.parse(
    await readFile(
      new URL("../public/maps/manifest.json", import.meta.url),
      "utf8",
    ),
  );

  for (const language of ["fr", "en"]) {
    for (const site of manifest.sites) {
      const path = `/reunion/${language}/sites/${site.slug}`;
      const response = await render(path, {
        "accept-language": language === "fr" ? "en" : "fr",
      });
      assert.equal(response.status, 200, path);
      const html = await response.text();

      assert.match(
        html,
        new RegExp(`<html lang="${language}" data-theme="auto">`),
        path,
      );
      assert.ok(
        visibleText(html).includes(site.displayName),
        `${path}: expected the selected site name`,
      );
      const expectedHeading =
        language === "fr"
          ? "Plans des sites de plongée à La Réunion"
          : "Dive site maps of Réunion Island";
      assert.equal(
        extractH1(html),
        expectedHeading,
        `${path}: expected the fixed regional H1`,
      );
      assert.ok(
        html.includes(`<title>${expectedHeading}</title>`),
        `${path}: expected the fixed regional document title`,
      );
      assert.doesNotMatch(
        html,
        /class="site-introduction"/,
        `${path}: site-specific introductory prose must not render`,
      );
      assert.ok(
        html.includes(
          `name="description" content="${regionalMetadataDescriptions[language]}"`,
        ),
        `${path}: expected the fixed regional metadata description`,
      );
      assert.match(
        html,
        new RegExp(
          `<link rel="canonical" href="https://divetopo\\.com${path}"\\/>`,
        ),
        path,
      );
      assert.match(
        html,
        new RegExp(
          `<a(?=[^>]*aria-current="page")(?=[^>]*href="${path}")[^>]*>`,
        ),
        path,
      );
      assert.match(
        html,
        new RegExp(
          `src="/maps/${site.slug}/3d-dynamic-orthophoto-2474\\.webp"`,
        ),
        path,
      );
      assert.match(html, /"@type":"Map"/, path);
      assert.match(html, /"@type":"GeoCoordinates"/, path);
      assert.equal(
        html.match(/"@type":"ImageObject"/g)?.length,
        3,
        `${path}: expected 2D, 3D and printable-sheet ImageObjects`,
      );
      assert.match(
        html,
        /"creator":\{"@type":"Person","name":"Matthieu Foll"\}/,
        path,
      );
      assert.match(
        html,
        /"license":"https:\/\/creativecommons\.org\/licenses\/by-nc-sa\/4\.0\/"/,
        path,
      );
      assert.equal(
        html.match(/"encodingFormat":"image\/jpeg"/g)?.length,
        3,
        `${path}: expected JPEG ImageObjects`,
      );
      assert.match(html, /"caption":"/, path);
      assert.match(
        html,
        new RegExp(
          `"latitude":${String(site.location.latitude).replace(".", "\\.")}`,
        ),
        path,
      );
      assert.match(
        html,
        new RegExp(
          `<link rel="alternate" hrefLang="x-default" href="https://divetopo\\.com/reunion/sites/${site.slug}"\\/>`,
        ),
        path,
      );
      assert.match(
        html,
        new RegExp(
          `<dialog(?=[^>]*class="map-dialog")[\\s\\S]*?<img(?=[^>]*src="/maps/${site.slug}/3d-dynamic-orthophoto-2474\\.webp")(?=[^>]*loading="lazy")[^>]*>`,
        ),
        `${path}: expected the hidden full-size map to load lazily`,
      );
      assert.doesNotMatch(
        html,
        /class="map-dialog overview-dialog"/,
        `${path}: the 2D regional overview must not expose a full-size button`,
      );
    }
  }
});

test("redirects the neutral Réunion URL from saved and weighted language preferences", async () => {
  const frenchResponse = await render("/reunion", {
    "accept-language": "de-DE,fr;q=0.9,en;q=0.8",
  });
  const englishResponse = await render("/reunion", {
    "accept-language": "fr;q=0,en;q=1",
  });
  const fallbackEnglishResponse = await render("/reunion", {
    "accept-language": "de-DE,de;q=0.9",
  });
  const savedFrenchResponse = await render("/reunion", {
    "accept-language": "en-US,en;q=0.9",
    cookie: "divetopo-language=fr; divetopo-theme=dark",
  });

  assert.equal(frenchResponse.status, 307);
  assert.equal(frenchResponse.headers.get("location"), "http://localhost/reunion/fr");
  assert.equal(englishResponse.status, 307);
  assert.equal(englishResponse.headers.get("location"), "http://localhost/reunion/en");
  assert.equal(fallbackEnglishResponse.status, 307);
  assert.equal(
    fallbackEnglishResponse.headers.get("location"),
    "http://localhost/reunion/en",
  );
  assert.equal(savedFrenchResponse.status, 307);
  assert.equal(
    savedFrenchResponse.headers.get("location"),
    "http://localhost/reunion/fr",
  );

  const darkEnglishHtml = await (
    await render("/reunion/en", {
      cookie: "divetopo-language=fr; divetopo-theme=dark",
    })
  ).text();
  assert.match(darkEnglishHtml, /<html lang="en" data-theme="dark">/);
  assert.match(darkEnglishHtml, /data-testid="theme-dark"[^>]*checked=""/);
  assert.match(darkEnglishHtml, /View site on Google Maps/);

  const neutralSiteResponse = await render("/reunion/sites/cap-homard", {
    "accept-language": "fr-FR,fr;q=0.9",
  });
  assert.equal(neutralSiteResponse.status, 307);
  assert.equal(
    neutralSiteResponse.headers.get("location"),
    "http://localhost/reunion/fr/sites/cap-homard",
  );
});

test("does not preserve the retired regional route shape", async () => {
  const [oldFrenchSite, oldNeutralSite] = await Promise.all([
    render("/fr/sites/cap-homard"),
    render("/sites/cap-homard"),
  ]);

  assert.equal(oldFrenchSite.status, 404);
  assert.equal(oldNeutralSite.status, 404);
  assert.equal(oldFrenchSite.headers.get("location"), null);
  assert.equal(oldNeutralSite.headers.get("location"), null);
});

test("publishes crawlable robots and multilingual sitemap metadata routes", async () => {
  const [robotsResponse, sitemapResponse] = await Promise.all([
    render("/robots.txt"),
    render("/sitemap.xml"),
  ]);

  assert.equal(robotsResponse.status, 200);
  assert.match(
    robotsResponse.headers.get("content-type") ?? "",
    /^text\/plain\b/i,
  );
  const robots = await robotsResponse.text();
  assert.match(robots, /User-Agent: \*\nAllow: \//);
  assert.match(
    robots,
    /Sitemap: https:\/\/divetopo\.com\/sitemap\.xml/,
  );

  assert.equal(sitemapResponse.status, 200);
  assert.match(
    sitemapResponse.headers.get("content-type") ?? "",
    /^application\/xml\b/i,
  );
  const sitemap = await sitemapResponse.text();
  const locations = [...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)].map(
    (match) => match[1],
  );
  const imageLocations = [
    ...sitemap.matchAll(/<image:loc>([^<]+)<\/image:loc>/g),
  ].map((match) => match[1]);
  assert.equal(locations.length, 38);
  assert.equal(imageLocations.length, 102);
  assert.ok(locations.includes("https://divetopo.com/fr"));
  assert.ok(locations.includes("https://divetopo.com/en"));
  assert.ok(locations.includes("https://divetopo.com/reunion/fr"));
  assert.ok(locations.includes("https://divetopo.com/reunion/en"));
  assert.ok(locations.includes("https://divetopo.com/paca/fr"));
  assert.ok(locations.includes("https://divetopo.com/paca/en"));
  assert.ok(
    locations.includes(
      "https://divetopo.com/reunion/fr/sites/cap-la-houssaye",
    ),
  );
  assert.ok(
    locations.includes(
      "https://divetopo.com/reunion/en/sites/pointe-au-sel-sec-jaune",
    ),
  );
  assert.ok(
    locations.includes(
      "https://divetopo.com/reunion/fr/sites/pointe-des-aigrettes",
    ),
  );
  assert.ok(
    locations.includes(
      "https://divetopo.com/reunion/en/sites/roches-noires",
    ),
  );
  assert.ok(
    locations.includes(
      "https://divetopo.com/reunion/fr/sites/trois-bassins",
    ),
  );
  assert.ok(
    locations.includes(
      "https://divetopo.com/reunion/en/sites/souris-chaude",
    ),
  );
  assert.ok(
    locations.includes(
      "https://divetopo.com/paca/fr/sites/la-gabiniere-port-cros",
    ),
  );
  assert.ok(
    locations.includes(
      "https://divetopo.com/paca/en/sites/cap-des-medes",
    ),
  );
  assert.match(sitemap, /hreflang="x-default"/);
  assert.match(
    sitemap,
    /https:\/\/divetopo\.com\/maps\/cap-homard\/downloads\/2d-orthophoto-full\.jpg/,
  );
  assert.match(
    sitemap,
    /https:\/\/divetopo\.com\/maps\/cap-homard\/downloads\/3d-orthophoto-full\.jpg/,
  );
  assert.match(
    sitemap,
    /https:\/\/divetopo\.com\/maps\/cap-homard\/downloads\/planche-orthophoto-full\.jpg/,
  );
  assert.equal(
    imageLocations.filter((location) => new URL(location).pathname.endsWith(".jpg"))
      .length,
    96,
    "expected the regional sitemap entries to use JPEG downloads",
  );
  assert.equal(
    imageLocations.filter(
      (location) => location === "https://divetopo.com/og.png",
    ).length,
    2,
    "expected each localized homepage entry to reference its social image",
  );
  assert.equal(
    imageLocations.filter(
      (location) =>
        location === "https://divetopo.com/reunion-og.png",
    ).length,
    2,
    "expected each localized Réunion entry to reference its social image",
  );
  assert.equal(
    imageLocations.filter(
      (location) =>
        location ===
        "https://divetopo.com/maps/paca/france-metropolitan-situation.png",
    ).length,
    2,
    "expected each localized PACA entry to reference the regional relief",
  );
});

test("map manifest supports adding future sites without component changes", async () => {
  const [publicManifest, bundledManifest] = await Promise.all([
    readFile(
      new URL("../public/maps/manifest.json", import.meta.url),
      "utf8",
    ),
    readFile(
      new URL("../content/map-manifest.json", import.meta.url),
      "utf8",
    ),
  ]);
  assert.equal(bundledManifest, publicManifest);
  const manifest = JSON.parse(publicManifest);

  assert.equal(manifest.schemaVersion, 6);
  assert.equal(manifest.sites.length, 11);
  assert.deepEqual(
    new Set(manifest.sites.map((site) => site.slug)),
    publishedSiteSlugs,
  );
  assert.equal(
    manifest.sites.find((site) => site.slug === "pointe-au-sel-sec-jaune")
      ?.displayName,
    "Pointe au Sel",
  );
  assert.equal(manifest.reunionOverview.src, "/reunion-overview.webp");
  assert.equal(manifest.reunionOverview.width, 1000);
  assert.equal(manifest.reunionOverview.height, 840);
  assert.equal(manifest.westCoastLocator.src, "/west-coast-locator.webp");
  assert.equal(manifest.westCoastLocator.width, 850);
  assert.equal(manifest.westCoastLocator.height, 1300);

  for (const site of manifest.sites) {
    assert.equal(typeof site.slug, "string");
    assert.equal(typeof site.displayName, "string");
    assert.ok(site.displayName.length > 0);
    assert.equal(typeof site.maxDepthM, "number");
    assert.equal(typeof site.planMaxDepthM, "number");
    assert.equal(
      typeof site.westCoastLocatorPosition?.xPercent,
      "number",
    );
    assert.equal(
      typeof site.westCoastLocatorPosition?.yPercent,
      "number",
    );
    assert.ok(site.westCoastLocatorPosition.xPercent >= 0);
    assert.ok(site.westCoastLocatorPosition.xPercent <= 100);
    assert.ok(site.westCoastLocatorPosition.yPercent >= 0);
    assert.ok(site.westCoastLocatorPosition.yPercent <= 100);
    assert.equal(typeof site.location?.city, "string");
    assert.ok(site.location.city.length > 0);
    assert.equal(typeof site.location?.latitude, "number");
    assert.equal(typeof site.location?.longitude, "number");

    const mapPairs = new Set(
      site.maps.map((map) => `${map.view}/${map.style}`),
    );
    assert.deepEqual(
      [...mapPairs].sort(),
      [
        "2d/orthophoto",
        "2d/topographic",
        "3d/orthophoto",
        "3d/topographic",
      ],
    );
    for (const map of site.maps) {
      assert.equal(map.download.width, map.sourceDimensions.width);
      assert.equal(map.download.height, map.sourceDimensions.height);
      assert.match(map.download.src, /\/downloads\/(?:2d|3d)-.+-full\.jpg$/);
      assert.match(map.download.filename, /\.jpg$/);
      const [published, canonical] = await Promise.all([
        readFile(new URL(`../public${map.download.src}`, import.meta.url)),
        readFile(
          new URL(
            `../../../regions/reunion/outputs/${map.download.filename}`,
            import.meta.url,
          ),
        ),
      ]);
      assert.ok(
        published.equals(canonical),
        `${site.slug}: published ${map.view}/${map.style} download differs from ${map.download.filename}`,
      );
      assert.equal(map.download.bytes, canonical.byteLength);
      assert.equal(
        map.download.sha256,
        createHash("sha256").update(canonical).digest("hex"),
      );
    }

    const plancheStyles = site.planches
      .map((planche) => planche.style)
      .sort();
    assert.deepEqual(plancheStyles, ["orthophoto", "topographic"]);
    for (const planche of site.planches) {
      assert.match(
        planche.download.src,
        /\/downloads\/planche-(?:orthophoto|topographic)-full\.jpg$/,
      );
      assert.match(planche.download.filename, /\.jpg$/);
      const [published, canonical] = await Promise.all([
        readFile(new URL(`../public${planche.download.src}`, import.meta.url)),
        readFile(
          new URL(
            `../../../regions/reunion/outputs/${planche.download.filename}`,
            import.meta.url,
          ),
        ),
      ]);
      assert.ok(
        published.equals(canonical),
        `${site.slug}: published ${planche.style} planche differs from ${planche.download.filename}`,
      );
      assert.equal(planche.download.bytes, canonical.byteLength);
      assert.equal(
        planche.download.sha256,
        createHash("sha256").update(canonical).digest("hex"),
      );
    }
  }
  assert.equal(
    manifest.sites.find((site) => site.slug === "pointe-au-sel-sec-jaune")
      ?.planMaxDepthM,
    30,
  );
  assert.equal(
    manifest.sites.find((site) => site.slug === "pointe-au-sel-sec-jaune")
      ?.maxDepthM,
    40,
  );
});

test("interactive terrain manifest covers the same eleven sites", async () => {
  const manifest = JSON.parse(
    await readFile(
      new URL("../public/terrain/manifest.json", import.meta.url),
      "utf8",
    ),
  );

  assert.equal(manifest.schemaVersion, 2);
  assert.equal(manifest.sites.length, 11);
  assert.deepEqual(
    new Set(manifest.sites.map((site) => site.slug)),
    publishedSiteSlugs,
  );
});

test("removes disposable starter artifacts", async () => {
  const [packageJson, page, layout] = await Promise.all([
    readFile(new URL("../package.json", import.meta.url), "utf8"),
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/layout.tsx", import.meta.url), "utf8"),
  ]);

  assert.doesNotMatch(packageJson, /react-loading-skeleton/);
  assert.doesNotMatch(page, /codex-preview|_sites-preview/);
  assert.doesNotMatch(layout, /Starter Project|codex-preview/);
  await Promise.all([
    assert.rejects(access(new URL("../app/_sites-preview", templateRoot))),
    assert.rejects(
      access(new URL("../content/site-details.json", templateRoot)),
    ),
  ]);
});

test("includes the shared west-coast site selector map", async () => {
  await Promise.all([
    access(new URL("../public/reunion-overview.webp", import.meta.url)),
    access(new URL("../public/west-coast-locator.webp", import.meta.url)),
    access(new URL("../public/icons/external-link.svg", import.meta.url)),
    access(new URL("../public/icons/isobaths.svg", import.meta.url)),
    access(new URL("../public/icons/reset-view.svg", import.meta.url)),
    access(new URL("../public/icons/fullscreen.svg", import.meta.url)),
  ]);
});

test("interactive terrain matches the static linear-light exposure", async () => {
  const [
    terrainViewer,
    styles,
    copySource,
    controlsSource,
    experienceSource,
  ] = await Promise.all([
    readFile(new URL("../app/TerrainViewer.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/globals.css", import.meta.url), "utf8"),
    readFile(new URL("../content/copy.ts", import.meta.url), "utf8"),
    readFile(new URL("../app/PreferenceControls.tsx", import.meta.url), "utf8"),
    readFile(
      new URL("../app/TopoReunionExperience.tsx", import.meta.url),
      "utf8",
    ),
  ]);

  assert.match(terrainViewer, /const RELIEF_EXPOSURE = 1\.55;/);
  assert.match(terrainViewer, /bathymetryColorRgb/);
  assert.match(terrainViewer, /bathymetryColorCss/);
  assert.match(terrainViewer, /Line2/);
  assert.match(terrainViewer, /LineGeometry/);
  assert.match(terrainViewer, /LineMaterial/);
  assert.match(terrainViewer, /vectorIsobathsPath/);
  assert.match(terrainViewer, /alongCenterOffsetM\?: number/);
  assert.match(
    terrainViewer,
    /metadata\.view\.alongCenterOffsetM !== undefined/,
  );
  assert.match(
    terrainViewer,
    /!hasExplicitCenterOffset[\s\S]*metadata\.view\.alongCenterOffsetM !== undefined/,
  );
  assert.match(terrainViewer, /linewidth: 3\.6/);
  assert.match(terrainViewer, /linewidth: 1\.7/);
  assert.match(
    terrainViewer,
    /installFragmentDepthBias\(\s*outlineMaterial,\s*VECTOR_ISOBATH_DEPTH_BIAS/s,
  );
  assert.doesNotMatch(terrainViewer, /isobath-vector/);
  assert.doesNotMatch(terrainViewer, /isobath-plane-offset/);
  assert.doesNotMatch(terrainViewer, /ISOBATH_LEVEL_COLORS/);
  assert.match(
    terrainViewer,
    /renderer\.toneMapping = THREE\.LinearToneMapping;/,
  );
  assert.match(
    terrainViewer,
    /renderer\.toneMappingExposure = RELIEF_EXPOSURE;/,
  );
  assert.match(terrainViewer, /aria-label=\{text\.resetView\}/);
  assert.match(terrainViewer, /text\.westCardinal/);
  assert.match(copySource, /westCardinal: "O"/);
  assert.match(copySource, /westCardinal: "W"/);
  assert.match(copySource, /resetView: "Réinitialiser la vue"/);
  assert.match(copySource, /resetView: "Reset view"/);
  assert.match(terrainViewer, /className="terrain-icon-button"/);
  assert.match(terrainViewer, /terrain-action-icon is-reset/);
  assert.match(terrainViewer, /terrain-action-icon is-isobaths/);
  assert.match(terrainViewer, /terrain-action-icon is-fullscreen/);
  assert.match(
    experienceSource,
    /initialOrbitAzimuthDeg=\{\s*activeSite\.interactiveInitialView\?\.orbitAzimuthDeg\s*\}/s,
  );
  assert.match(
    experienceSource,
    /initialCameraElevationDeg=\{\s*activeSite\.interactiveInitialView\s*\?\.cameraElevationDeg\s*\}/s,
  );
  assert.match(
    experienceSource,
    /initialPanRightM=\{\s*activeSite\.interactiveInitialView\?\.panRightM\s*\}/s,
  );
  assert.match(
    experienceSource,
    /initialPanUpM=\{\s*activeSite\.interactiveInitialView\?\.panUpM\s*\}/s,
  );
  assert.doesNotMatch(terrainViewer, />\s*Isobathes 5 m\s*</);
  assert.doesNotMatch(terrainViewer, />\s*Réinitialiser la vue\s*</);
  assert.doesNotMatch(terrainViewer, />\s*Plein écran\s*</);
  assert.match(
    styles,
    /\.external-link-icon\s*\{[^}]*transform:\s*translateY\(-0\.08rem\)/s,
  );
  assert.match(styles, /:root\[data-theme="dark"\]/);
  assert.match(
    styles,
    /@media \(prefers-color-scheme: dark\)[\s\S]*:root\[data-theme="auto"\]/,
  );
  assert.match(styles, /--accent-contrast:\s*#071b22/);
  assert.match(styles, /--viewer-control-divider:/);
  assert.match(styles, /\.segmented-control button \+ button/);
  assert.match(
    styles,
    /\.viewer-head\s*\{[^}]*margin-bottom:\s*var\(--topo-row-gap\)[^}]*\}[\s\S]*\.planche-download\s*\{[^}]*margin-top:\s*var\(--topo-row-gap\)/,
  );
  assert.match(
    styles,
    /@media \(max-width: 900px\)[\s\S]*?\.viewer-head\s*\{[^}]*margin-bottom:\s*var\(--topo-row-gap\)/,
  );
  assert.match(controlsSource, /Domain=\.divetopo\.com/);
  assert.match(controlsSource, /onLanguageChange\(nextLanguage\)/);
  assert.match(controlsSource, /className="language-choice"/);
  assert.doesNotMatch(controlsSource, /flushSync/);
  assert.doesNotMatch(controlsSource, /window\.scrollTo/);
  assert.doesNotMatch(controlsSource, /window\.location\.reload/);
  assert.match(experienceSource, /window\.history\.pushState/);
  assert.match(experienceSource, /window\.history\.replaceState/);
  assert.match(experienceSource, /window\.addEventListener\("popstate"/);
  assert.doesNotMatch(controlsSource, /localStorage/);
  assert.doesNotMatch(
    terrainViewer,
    /<strong>\{text\.isobaths\}<\/strong>/,
  );
  assert.doesNotMatch(terrainViewer, /text\.isobaths/);
  assert.doesNotMatch(copySource, /\bisobaths:\s*["']/);
  assert.doesNotMatch(terrainViewer, />\s*Isobath(?:es|s)\s*</);
  assert.match(terrainViewer, /aria-label=\{`\$\{text\.isobathLegend\}/);
  assert.doesNotMatch(styles, /\.site-picker-range\b/);
});

test("interactive isobaths reuse the static bathymetric palette", () => {
  const expectedByMaximumDepth = new Map([
    [
      20,
      [
        [250, 132, 30],
        [113, 219, 137],
        [36, 113, 202],
      ],
    ],
    [
      30,
      [
        [249, 128, 29],
        [127, 221, 120],
        [39, 123, 210],
        [10, 37, 112],
        [6, 25, 89],
      ],
    ],
    [
      40,
      [
        [249, 126, 29],
        [133, 222, 112],
        [40, 129, 211],
        [12, 41, 118],
        [6, 26, 90],
        [4, 20, 79],
        [2, 14, 60],
      ],
    ],
  ]);

  for (const [maximumDepthM, expected] of expectedByMaximumDepth) {
    assert.deepEqual(
      expected.map((_, index) =>
        bathymetryColorRgb((index + 1) * 5, maximumDepthM),
      ),
      expected,
    );
  }
  assert.equal(bathymetryColorCss(5, 20), "rgb(250, 132, 30)");
});

test("portrait fullscreen stays inside the validated camera frustum", () => {
  const canonicalAspect = 2474 / 1712;
  const verticalStretch = Math.sqrt(1 + (0.34 * 1.35) ** 2);
  const canonicalHalfWidth = 290;
  const canonicalHalfHeight =
    canonicalHalfWidth / (canonicalAspect * verticalStretch);

  const portrait = coveredOrthographicHalfExtents(
    canonicalHalfWidth,
    canonicalHalfHeight,
    390 / 844,
    verticalStretch,
  );
  assert.ok(portrait.halfWidth < canonicalHalfWidth);
  assert.equal(portrait.halfHeight, canonicalHalfHeight);

  const landscape = coveredOrthographicHalfExtents(
    canonicalHalfWidth,
    canonicalHalfHeight,
    844 / 390,
    verticalStretch,
  );
  assert.equal(landscape.halfWidth, canonicalHalfWidth);
  assert.ok(landscape.halfHeight < canonicalHalfHeight);

  for (const resized of [portrait, landscape]) {
    assert.ok(resized.halfWidth <= canonicalHalfWidth);
    assert.ok(resized.halfHeight <= canonicalHalfHeight);
  }
});

test("interactive terrain synchronizes its canvas box and backing store", async () => {
  const [terrainViewer, styles] = await Promise.all([
    readFile(new URL("../app/TerrainViewer.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/globals.css", import.meta.url), "utf8"),
  ]);

  assert.match(terrainViewer, /new ResizeObserver/);
  assert.match(
    terrainViewer,
    /currentRenderer\.setSize\(widthPx, heightPx, true\)/,
  );
  assert.match(
    terrainViewer,
    /if \(\s*!pixelRatioChanged &&\s*widthPx === lastWidth &&\s*heightPx === lastHeight\s*\)/s,
  );
  assert.match(terrainViewer, /resizeObserver\.observe\(mount\);\s*resize\(\)/s);
  assert.doesNotMatch(terrainViewer, /resizeTerrainRef/);
  assert.doesNotMatch(terrainViewer, /fullscreenRecoveryFrameRef/);
  assert.doesNotMatch(terrainViewer, /scheduleViewportRecovery/);
  assert.doesNotMatch(terrainViewer, /\[120, 350, 750\]/);
  assert.doesNotMatch(
    terrainViewer,
    /currentRenderer\.setSize\(widthPx - 1/,
  );
  assert.doesNotMatch(
    styles,
    /\.terrain-host canvas\s*\{[^}]*(?:height|width):\s*100%/s,
  );
});

test("keeps the viewer and download card in ordinary block flow", async () => {
  const styles = await readFile(
    new URL("../app/globals.css", import.meta.url),
    "utf8",
  );

  assert.doesNotMatch(
    styles,
    /\.topo-reunion-main\s*\{[^}]*display:\s*grid/s,
  );
  assert.match(
    styles,
    /\.topo-reunion-main\s*\{[^}]*display:\s*block/s,
  );
  assert.match(
    styles,
    /\.planche-download\s*\{[^}]*margin-top:\s*var\(--topo-row-gap\)/s,
  );
});

test("interactive terrain provides an iOS-safe fullscreen fallback", async () => {
  const [terrainViewer, styles] = await Promise.all([
    readFile(new URL("../app/TerrainViewer.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/globals.css", import.meta.url), "utf8"),
  ]);

  assert.match(terrainViewer, /host\.requestFullscreen/);
  assert.match(terrainViewer, /setIsCssFullscreen\(true\)/);
  assert.match(terrainViewer, /useLayoutEffect/);
  assert.doesNotMatch(terrainViewer, /body\.style\.position = "fixed"/);
  assert.match(terrainViewer, /root\.style\.overflow = "hidden"/);
  assert.match(terrainViewer, /classList\.add\("has-css-fullscreen"\)/);
  assert.match(
    terrainViewer,
    /classList\.remove\("has-css-fullscreen"\)/,
  );
  assert.doesNotMatch(terrainViewer, /window\.scrollTo\(scrollX, scrollY\)/);
  assert.match(terrainViewer, /force-css-fullscreen/);
  assert.match(terrainViewer, /event\.key === "Escape"/);
  assert.match(terrainViewer, /aria-pressed=\{isFullscreen\}/);
  assert.match(styles, /\.terrain-host\.is-css-fullscreen/);
  assert.match(styles, /\.viewer-frame\.has-css-fullscreen/);
  assert.doesNotMatch(
    styles,
    /\.viewer-frame\.has-css-fullscreen\s*\{[^}]*position:\s*fixed/s,
  );
  assert.match(
    styles,
    /\.terrain-host\.is-css-fullscreen\s*\{[^}]*position:\s*fixed/s,
  );
  assert.match(
    styles,
    /\.terrain-host:fullscreen,\s*\.terrain-host\.is-css-fullscreen\s*\{[^}]*height:\s*100dvh/s,
  );
  assert.match(
    styles,
    /\.viewer-frame\.has-css-fullscreen\s*\{[^}]*overflow:\s*visible/s,
  );
  assert.match(styles, /safe-area-inset-top/);
  assert.match(styles, /safe-area-inset-bottom/);
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
    /<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent"\/>/,
  );
  assert.match(
    html,
    /<meta name="viewport" content="[^"]*viewport-fit=cover[^"]*"\/>/,
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

test("ships a scoped standalone manifest and correctly sized PNG icons", async () => {
  const manifest = JSON.parse(
    await readFile(
      new URL("../public/manifest.webmanifest", import.meta.url),
      "utf8",
    ),
  );

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
