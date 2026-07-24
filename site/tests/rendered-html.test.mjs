import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import test from "node:test";

const templateRoot = new URL("../", import.meta.url);

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);

  return worker.fetch(
    new Request("http://localhost/", {
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

test("server-renders the finished atlas", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(
    html,
    /<title>Plans des sites de plongée à La Réunion<\/title>/i,
  );
  assert.match(html, /Plan des sites de plongée · La Réunion/);
  assert.match(html, /Plans des sites de plongée à La Réunion/);
  assert.match(html, /Cap La Houssaye/);
  assert.match(html, /Saint-Paul/);
  assert.match(html, /21° 01′ 02\.5″ S/);
  assert.match(html, /Voir le site sur Google Maps/);
  assert.match(html, /google\.com\/maps\/search/);
  assert.match(html, /3d-orthophoto-2474\.webp/);
  assert.match(html, /locator-640\.webp/);
  assert.match(html, /locator-1600\.webp/);
  assert.match(html, /Agrandir la carte/);
  assert.match(html, /Planche HD à imprimer/);
  assert.match(html, /Télécharger la planche HD/);
  assert.match(html, /Topographie/);
  assert.match(html, /Orthophoto/);
  assert.match(html, /3D interactive/);
  assert.match(html, /Données, méthode et licences/);
  assert.match(html, /données bathymétriques/);
  assert.match(html, /UTM 40S, EPSG:32740/);
  assert.match(html, /Grille bathymétrique GEBCO 2024/);
  assert.match(html, /Méthode de production/);
  assert.match(html, /https:\/\/github\.com\/mfoll\/reunion-topobathy/);
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
});

test("map manifest supports adding future sites without component changes", async () => {
  const manifest = JSON.parse(
    await readFile(
      new URL("../public/maps/manifest.json", import.meta.url),
      "utf8",
    ),
  );

  assert.equal(manifest.schemaVersion, 3);
  assert.ok(manifest.sites.length >= 3);

  for (const site of manifest.sites) {
    assert.equal(typeof site.slug, "string");
    assert.equal(typeof site.displayName, "string");
    assert.ok(site.displayName.length > 0);
    assert.equal(typeof site.maxDepthM, "number");
    assert.ok(site.locator?.src);
    assert.ok(site.locatorLarge?.src);
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

    const plancheStyles = site.planches
      .map((planche) => planche.style)
      .sort();
    assert.deepEqual(plancheStyles, ["orthophoto", "topographic"]);
  }
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
  await assert.rejects(access(new URL("../app/_sites-preview", templateRoot)));
});
