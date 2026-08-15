import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import test from "node:test";

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
    { waitUntil() {}, passThroughOnException() {} },
  );
}

test("retires the PACA aggregate through localized redirects", async () => {
  for (const language of ["fr", "en"]) {
    const overview = await render(`/paca/${language}`);
    assert.equal(overview.status, 308);
    assert.equal(
      overview.headers.get("location"),
      `http://localhost/${language}#regions`,
    );
  }
  const site = await render("/paca/fr/sites/cap-des-medes");
  assert.equal(site.status, 308);
  assert.equal(
    site.headers.get("location"),
    "http://localhost/var-centre/fr/sites/cap-des-medes",
  );
});

test("redirects the merged La Merveilleuse route to Les Magnons", async () => {
  const response = await render("/var-ouest/fr/sites/la-merveilleuse");
  assert.equal(response.status, 308);
  assert.equal(
    response.headers.get("location"),
    "http://localhost/var-ouest/fr/sites/les-magnons",
  );
});

test("redirects the merged Sec du Langoustier route to Jeaune Garde", async () => {
  const response = await render("/var-centre/fr/sites/sec-du-langoustier");
  assert.equal(response.status, 308);
  assert.equal(
    response.headers.get("location"),
    "http://localhost/var-centre/fr/sites/sec-de-la-jeaune-garde",
  );
});

test("renders regional inventories and keeps remaining drafts non-clickable", async () => {
  const published = [
    ["/var-ouest/fr", "topo-var-ouest-title", 4, 4],
    ["/var-centre/en", "topo-var-centre-title", 4, 5],
    ["/var-est/fr", "topo-var-est-title", 5, 6],
    ["/alpes-maritimes/fr", "topo-alpes-maritimes-title", 5, 6],
  ];
  for (const [path, titleId, siteCount, inventoryCount] of published) {
    const response = await render(path);
    assert.equal(response.status, 200, path);
    const html = await response.text();
    assert.match(html, new RegExp(`id="${titleId}"`), path);
    assert.equal(html.match(/class="site-map-marker label-/g)?.length, siteCount, path);
    assert.equal(
      html.match(/class="site-map-marker site-map-marker-preparing label-/g)?.length ?? 0,
      inventoryCount - siteCount,
      path,
    );
    const preparingHeading = path.endsWith("/en") ? /Sites in preparation/g : /Sites en préparation/g;
    assert.equal(html.match(preparingHeading)?.length ?? 0, siteCount < inventoryCount ? 1 : 0, path);
    const preparingNames = path.startsWith("/alpes-maritimes/") || path.startsWith("/var-ouest/") || path.startsWith("/var-est/")
      ? []
      : path.endsWith("/en")
        ? ["Sec de la Jeaune Garde", "Les Fourmigues"]
        : ["Pointe de la Cride", "Les Magnons"];
    for (const name of preparingNames) {
      assert.match(html, new RegExp(name), path);
    }
    if (path.startsWith("/alpes-maritimes/")) {
      assert.match(html, /Sites en préparation/);
      assert.match(html, /Cap Gros/);
      for (const slug of [
        "grande-baie-cap-ferrat",
        "pointe-causiniere-cap-ferrat",
        "la-vaquette",
        "la-tradeliere",
        "grotte-a-corail-villefranche",
      ]) {
        assert.match(html, new RegExp(`/alpes-maritimes/fr/sites/${slug}`), path);
      }
    }
    assert.doesNotMatch(html, /noindex/i, path);
    assert.match(html, /Shom–IGN Litto3D PACA 2015/, path);
    if (path.endsWith("/en")) {
      assert.match(html, /EMODnet 2024 offshore/, path);
      assert.match(html, /GEBCO 2024 is used only as a NoData fallback/, path);
    } else {
      assert.match(html, /EMODnet 2024 au large/, path);
      assert.match(html, /GEBCO 2024 sert uniquement de repli NoData/, path);
    }
    assert.match(html, /RGF93 \/ Lambert-93 \(EPSG:2154\)/, path);
    if (path.startsWith("/alpes-maritimes/")) {
      assert.match(html, /isobathes 2007 de la Métropole Nice Côte d’Azur/, path);
      assert.match(html, /ne sont pas interpolées dans le MNT/, path);
    }
  }

  const bouchesDuRhone = await render("/bouches-du-rhone/fr");
  assert.equal(bouchesDuRhone.status, 200);
  const bouchesDuRhoneHtml = await bouchesDuRhone.text();
  assert.match(bouchesDuRhoneHtml, /id="topo-bouches-du-rhone-title"/);
  assert.equal(
    bouchesDuRhoneHtml.match(/class="site-map-marker label-/g)?.length,
    5,
  );
  assert.equal(
    bouchesDuRhoneHtml.match(/class="site-map-marker site-map-marker-preparing label-/g)?.length ?? 0,
    1,
  );
  assert.match(bouchesDuRhoneHtml, /Sites en préparation/);
  assert.match(bouchesDuRhoneHtml, /Impérial du Milieu/);
  for (const slug of [
    "grotte-a-corail-maire",
    "pains-de-sucre-riou",
    "imperial-de-terre-riou",
    "pierre-a-la-bague-plateau",
    "tiboulen-du-frioul",
  ]) {
    assert.match(
      bouchesDuRhoneHtml,
      new RegExp(`/bouches-du-rhone/fr/sites/${slug}`),
      slug,
    );
  }

});

test("regional planning inventories contain the classified sites", async () => {
  for (const [region, expectedCount] of [
    ["bouches-du-rhone", 6],
    ["var-ouest", 4],
    ["var-centre", 5],
    ["var-est", 6],
    ["alpes-maritimes", 6],
  ]) {
    const manifest = JSON.parse(
      await readFile(
        new URL(`../content/${region}-map-manifest.json`, import.meta.url),
        "utf8",
      ),
    );
    assert.equal(manifest.plannedSites.length, expectedCount, region);
    assert.deepEqual(
      manifest.plannedSites.filter((site) => site.status === "published").map((site) => site.slug),
      manifest.sites.map((site) => site.slug),
      region,
    );
    for (const site of manifest.sites) {
      assert.deepEqual(site.compactAttributions, {
        topographic:
          "Bathymétrie / topographie : Shom–IGN Litto3D PACA 2015 · MNT 1 m · IGN69",
        orthophoto:
          "Bathymétrie / topographie : Shom–IGN Litto3D PACA 2015 · MNT 1 m · IGN69 · Orthophoto : IGN BD ORTHO",
      });
    }
  }
});

test("published autonomous-region asset paths resolve", async () => {
  for (const region of [
    "bouches-du-rhone",
    "var-ouest",
    "var-centre",
    "var-est",
    "alpes-maritimes",
  ]) {
    await access(
      new URL(
        `../public/maps/${region}/${region}-regional-relief.png`,
        import.meta.url,
      ),
    );
  }

  for (const [region, expectedSiteCount] of [
    ["var-ouest", 4],
    ["var-centre", 4],
    ["var-est", 5],
    ["alpes-maritimes", 5],
  ]) {
    const manifest = JSON.parse(
      await readFile(
        new URL(`../content/${region}-map-manifest.json`, import.meta.url),
        "utf8",
      ),
    );
    assert.equal(manifest.schemaVersion, 2);
    assert.equal(manifest.sites.length, expectedSiteCount);
    for (const site of manifest.sites) {
      assert.match(
        site.config,
        new RegExp(`^regions/${region}/sites/.+\\.json$`),
      );
      assert.equal(site.assetBasePath, `/maps/${region}/${site.slug}`);
      for (const map of site.maps) {
        for (const variant of map.variants) {
          await access(new URL(`../public${variant.src}`, import.meta.url));
        }
        if (map.view === "3d") {
          assert.match(
            map.download.src,
            new RegExp(
              `^https://github\\.com/mfoll/divetopo/releases/download/v1\\.4\\.0/${map.download.filename}$`,
            ),
          );
        } else {
          await access(
            new URL(`../public${map.download.src.split("?")[0]}`, import.meta.url),
          );
        }
      }
      await access(
        new URL(`../public/terrain/${site.slug}/terrain.json`, import.meta.url),
      );
    }
  }
});
