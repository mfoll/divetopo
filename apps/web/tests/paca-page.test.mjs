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

test("renders five-site regional inventories and keeps remaining drafts non-clickable", async () => {
  const published = [
    ["/var-ouest/fr", "topo-var-ouest-title", 2],
    ["/var-centre/en", "topo-var-centre-title", 5],
  ];
  for (const [path, titleId, siteCount] of published) {
    const response = await render(path);
    assert.equal(response.status, 200, path);
    const html = await response.text();
    assert.match(html, new RegExp(`id="${titleId}"`), path);
    assert.equal(html.match(/class="site-map-marker label-/g)?.length, siteCount, path);
    assert.equal(
      html.match(/class="site-map-marker site-map-marker-preparing label-/g)?.length ?? 0,
      5 - siteCount,
      path,
    );
    const preparingHeading = path.endsWith("/en") ? /Sites in preparation/g : /Sites en préparation/g;
    assert.equal(html.match(preparingHeading)?.length ?? 0, siteCount < 5 ? 1 : 0, path);
    for (const name of path.endsWith("/en")
      ? ["Sec de la Jeaune Garde", "Sec du Langoustier", "Les Fourmigues"]
      : ["Pointe de la Cride", "Les Magnons", "La Merveilleuse"]) {
      assert.match(html, new RegExp(name), path);
    }
    assert.doesNotMatch(html, /noindex/i, path);
  }

  const bouchesDuRhone = await render("/bouches-du-rhone/fr");
  assert.equal(bouchesDuRhone.status, 200);
  const bouchesDuRhoneHtml = await bouchesDuRhone.text();
  assert.match(bouchesDuRhoneHtml, /id="topo-bouches-du-rhone-title"/);
  assert.equal(
    bouchesDuRhoneHtml.match(/class="site-map-marker label-/g)?.length,
    5,
  );
  assert.doesNotMatch(bouchesDuRhoneHtml, /En préparation|en préparation/);
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

  for (const region of [
    "var-est",
    "alpes-maritimes",
  ]) {
    const response = await render(`/${region}/fr`);
    assert.equal(response.status, 200, region);
    const html = await response.text();
    assert.match(html, /cinq premières cartographies/, region);
    assert.equal(
      html.match(/class="site-map-marker site-map-marker-preparing label-/g)?.length,
      5,
      region,
    );
    assert.equal(html.match(/<li>/g)?.length, 5, region);
    assert.equal(html.match(/<em>En préparation<\/em>/g)?.length, 5, region);
    assert.doesNotMatch(html, new RegExp(`/${region}/fr/sites/`), region);
  }
});

test("regional planning inventories contain exactly five classified sites", async () => {
  for (const region of [
    "bouches-du-rhone",
    "var-ouest",
    "var-centre",
    "var-est",
    "alpes-maritimes",
  ]) {
    const manifest = JSON.parse(
      await readFile(
        new URL(`../content/${region}-map-manifest.json`, import.meta.url),
        "utf8",
      ),
    );
    assert.equal(manifest.plannedSites.length, 5, region);
    assert.deepEqual(
      manifest.plannedSites.filter((site) => site.status === "published").map((site) => site.slug),
      manifest.sites.map((site) => site.slug),
      region,
    );
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

  for (const [region, expectedSiteCount] of [["var-ouest", 2], ["var-centre", 5]]) {
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
        await access(
          new URL(`../public${map.download.src}`, import.meta.url),
        );
      }
      await access(
        new URL(`../public/terrain/${site.slug}/terrain.json`, import.meta.url),
      );
    }
  }
});
