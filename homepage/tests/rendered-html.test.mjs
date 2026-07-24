import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import test from "node:test";

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

test("server-renders the DiveTopo regional homepage", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(html, /<html lang="fr">/);
  assert.match(
    html,
    /<title>DiveTopo · Atlas topo-bathymétriques<\/title>/i,
  );
  assert.match(html, /Le relief sous-marin, région par région\./);
  assert.match(html, /La Réunion/);
  assert.match(html, /src="\/reunion-overview\.webp"/);
  assert.match(
    html,
    /href="https:\/\/reunion\.divetopo\.com"/,
  );
  assert.match(html, /aria-label="Explorer l’atlas de La Réunion"/);
  assert.match(html, /Un atlas pensé pour grandir\./);
  assert.match(html, /IGN RGE ALTI/);
  assert.match(html, /GEBCO Compilation Group \(2024\)/);
  assert.doesNotMatch(html, /codex-preview|Your site is taking shape/i);
});

test("keeps regions data-driven and bundles the exact island relief", async () => {
  const [regionsSource, packageJson] = await Promise.all([
    readFile(new URL("../content/regions.ts", import.meta.url), "utf8"),
    readFile(new URL("../package.json", import.meta.url), "utf8"),
  ]);

  assert.match(regionsSource, /export const regions/);
  assert.match(regionsSource, /https:\/\/reunion\.divetopo\.com/);
  assert.match(regionsSource, /reunion-overview\.webp/);
  assert.doesNotMatch(packageJson, /react-loading-skeleton|drizzle/);
  await access(new URL("../public/reunion-overview.webp", import.meta.url));
  await access(new URL("../public/og.png", import.meta.url));
});
