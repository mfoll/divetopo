import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import test from "node:test";

const pacaSites = [
  ["la-gabiniere-port-cros", "La Gabinière"],
  ["pointe-portissol", "Pointe de Portissol"],
  ["deux-freres-cap-sicie", "Les Deux Frères"],
  ["les-pyramides-cap-dramont", "Les Pyramides"],
  ["cap-des-medes", "Cap des Mèdes"],
];

async function render(pathname) {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set(
    "test",
    `${process.pid}-${Date.now()}-${Math.random()}`,
  );
  const { default: worker } = await import(workerUrl.href);

  return worker.fetch(
    new Request(`http://localhost${pathname}`, {
      headers: { accept: "text/html" },
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

test("server-renders the complete public PACA region and five sites", async () => {
  const regionalPages = [
    ["/paca/fr", "fr", "Plans des sites de plongée de la Côte d’Azur"],
    ["/paca/en", "en", "Dive site maps along the Côte d’Azur"],
  ];

  for (const [path, language, heading] of regionalPages) {
    const response = await render(path);
    assert.equal(response.status, 200, path);
    const html = await response.text();

    assert.match(html, new RegExp(`<html lang="${language}"`), path);
    assert.match(html, new RegExp(`<h1 id="topo-paca-title">${heading}</h1>`), path);
    assert.match(
      html,
      /\/maps\/paca\/france-metropolitan-situation\.png/,
      path,
    );
    assert.match(
      html,
      language === "fr"
        ? /Carte de situation de la France métropolitaine, sans annotations\./
        : /Situation map of metropolitan France, without annotations\./,
      `${path}: overview accessibility text must describe the clean map`,
    );
    assert.doesNotMatch(html, /rectangle indique|rectangle marks/, path);
    assert.ok(
      html.indexOf('class="site-picker-map is-paca"') <
        html.indexOf('class="reunion-overview is-paca"'),
      `${path}: local site map must precede the France situation map`,
    );
    assert.equal(
      html.match(/class="site-map-marker label-/g)?.length,
      5,
      `${path}: expected five PACA map markers`,
    );
    for (const [slug, displayName] of pacaSites) {
      assert.match(html, new RegExp(displayName), `${path}: ${displayName}`);
      assert.match(
        html,
        new RegExp(`href="/paca/${language}/sites/${slug}"`),
        `${path}: link for ${slug}`,
      );
    }
    assert.doesNotMatch(html, /noindex/i, path);
    assert.doesNotMatch(html, /test-assets\/paca/, path);
    assert.doesNotMatch(html, /Ouvrir .* en grand/, path);
    assert.doesNotMatch(html, /class="map-dialog overview-dialog"/, path);
  }

  for (const language of ["fr", "en"]) {
    for (const [slug, displayName] of pacaSites) {
      const path = `/paca/${language}/sites/${slug}`;
      const response = await render(path);
      assert.equal(response.status, 200, path);
      const html = await response.text();

      assert.match(html, new RegExp(`<html lang="${language}"`), path);
      assert.match(html, new RegExp(`<h2[^>]*>${displayName}</h2>`), path);
      assert.match(
        html,
        new RegExp(`/maps/paca/${slug}/maps/3d-dynamic-orthophoto-2474\\.webp`),
        `${path}: expected the consolidated 3D poster`,
      );
      assert.match(
        html,
        new RegExp(`/maps/paca/${slug}/maps/2d-orthophoto\\.jpg`),
        `${path}: expected the consolidated 2D map`,
      );
      assert.match(
        html,
        new RegExp(
          `/maps/paca/${slug}/maps/planche-orthophoto-1800\\.webp`,
        ),
        `${path}: expected the orthophoto printable planche`,
      );
      assert.match(
        html,
        new RegExp(
          `/maps/paca/${slug}/maps/downloads/planche-orthophoto-full\\.jpg`,
        ),
        `${path}: expected the orthophoto printable download`,
      );
      assert.match(html, /data-testid="topo-paca-viewer"/, path);
      assert.match(html, /"@type":"Map"/, path);
      assert.match(html, /"@type":"GeoCoordinates"/, path);
      assert.equal(
        html.match(/"@type":"ImageObject"/g)?.length,
        3,
        `${path}: expected 2D, 3D and printable-planche images`,
      );
      assert.doesNotMatch(html, /noindex/i, path);
      assert.doesNotMatch(html, /test-assets\/paca/, path);
      assert.doesNotMatch(html, /Ouvrir .* en grand/, path);
      assert.doesNotMatch(html, /class="map-dialog overview-dialog"/, path);
    }
  }
});

test("PACA asset paths resolve without regenerating or duplicating test maps", async () => {
  const manifest = JSON.parse(
    await readFile(
      new URL("../content/paca-map-manifest.json", import.meta.url),
      "utf8",
    ),
  );

  assert.equal(manifest.sites.length, 5);
  assert.deepEqual(manifest.reunionOverview.boundsWgs84, {
    west: -5.5,
    south: 42.0,
    east: 8.7,
    north: 51.3,
  });
  assert.equal(manifest.reunionOverview.width, 1000);
  assert.equal(manifest.reunionOverview.height, 840);
  assert.equal(manifest.reunionOverview.sourceUrl, "https://wms.gebco.net/2024/mapserv");
  assert.equal(manifest.reunionOverview.layer, "GEBCO_2024");
  assert.deepEqual(manifest.reunionOverview.request.bbox, [-5.5, 42.0, 8.7, 51.3]);
  assert.equal(manifest.reunionOverview.request.width, 1000);
  assert.equal(manifest.reunionOverview.request.height, 840);
  assert.match(manifest.reunionOverview.outlineSource, /Natural Earth 10m/);
  assert.deepEqual(manifest.westCoastLocator.boundsWgs84, {
    west: 5.65,
    south: 42.82,
    east: 7.0,
    north: 43.58,
  });
  assert.equal(
    manifest.westCoastLocator.sourceUrl,
    "https://ows.emodnet-bathymetry.eu/wcs",
  );
  assert.equal(manifest.westCoastLocator.layer, "emodnet:mean");
  assert.equal(
    manifest.westCoastLocator.marineSourceUrl,
    "https://ows.emodnet-bathymetry.eu/wcs",
  );
  assert.equal(manifest.westCoastLocator.marineLayer, "emodnet:mean");
  assert.match(
    manifest.westCoastLocator.marineResolution,
    /1\/16 arc minute native DTM grid/,
  );
  await access(
    new URL(
      `../public${manifest.reunionOverview.src}`,
      import.meta.url,
    ),
  );
  for (const site of manifest.sites) {
    for (const map of site.maps) {
      for (const variant of map.variants) {
        await access(new URL(`../public${variant.src}`, import.meta.url));
      }
      await access(new URL(`../public${map.download.src}`, import.meta.url));
      if (map.view === "3d") {
        await access(
          new URL(
            `../public${site.assetBasePath}/maps/3d-dynamic-${map.style}-mobile-960.webp`,
            import.meta.url,
          ),
        );
      }
    }
    assert.equal(site.planches?.length, 2, `${site.slug}: two planches`);
    for (const planche of site.planches) {
      await access(new URL(`../public${planche.preview.src}`, import.meta.url));
      await access(new URL(`../public${planche.download.src}`, import.meta.url));
    }
    await access(
      new URL(`../public/terrain/${site.slug}/terrain.json`, import.meta.url),
    );
    await access(
      new URL(
        `../public/terrain/${site.slug}/isobaths-vector.json`,
        import.meta.url,
      ),
    );
  }
});
