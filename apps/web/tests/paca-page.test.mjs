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

test("renders autonomous Mediterranean regions without exposing drafts", async () => {
  const published = [
    ["/var-ouest/fr", "topo-var-ouest-title", 2],
    ["/var-centre/en", "topo-var-centre-title", 2],
  ];
  for (const [path, titleId, siteCount] of published) {
    const response = await render(path);
    assert.equal(response.status, 200, path);
    const html = await response.text();
    assert.match(html, new RegExp(`id="${titleId}"`), path);
    assert.equal(
      html.match(/class="site-map-marker label-/g)?.length,
      siteCount,
      path,
    );
    assert.doesNotMatch(html, /noindex/i, path);
  }

  for (const region of [
    "bouches-du-rhone",
    "var-est",
    "alpes-maritimes",
  ]) {
    const response = await render(`/${region}/fr`);
    assert.equal(response.status, 200, region);
    const html = await response.text();
    assert.match(html, /cinq premières cartographies/, region);
    assert.doesNotMatch(html, new RegExp(`/${region}/fr/sites/`), region);
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

  for (const region of ["var-ouest", "var-centre"]) {
    const manifest = JSON.parse(
      await readFile(
        new URL(`../content/${region}-map-manifest.json`, import.meta.url),
        "utf8",
      ),
    );
    assert.equal(manifest.schemaVersion, 2);
    assert.equal(manifest.sites.length, 2);
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
