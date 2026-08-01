# DiveTopo workflow

DiveTopo has one shared cartographic engine, one Web application, and one
configuration directory per region. The repository is the source of truth for
code and generated artifacts; the public interface is
[divetopo.com](https://divetopo.com).

## Start every mapping task from the live repository

Before changing or adding a site:

1. inspect the current Git `HEAD`, this file, `README.md`, the selected region's
   workflow, the cartographic modules, tests, region manifest, and existing site
   configurations;
2. do not rely on an earlier Codex task or remembered version of the workflow;
3. keep unrelated changes untouched and keep a new site region-local unless a
   shared change has been discussed;
4. leave generated work uncommitted and undeployed until its visual result has
   been validated.

For La Réunion, continue with
[regions/reunion/WORKFLOW.md](regions/reunion/WORKFLOW.md).

## Repository boundaries

```text
apps/web/                  one public application and deployment
cartography/               shared rendering and packaging engine
cartography/regions/       region-specific acquisition/orchestration modules
regions/<slug>/region.json regional identity, CRS, sources and site inventory
regions/<slug>/sites/      reproducible site configurations
regions/<slug>/outputs/    canonical generated maps and interactive packages
tests/                     shared and region-contract tests
```

The Web application consumes publication derivatives. It must never calculate
terrain, alter camera metadata, or become the canonical owner of maps and
interactive packages.

## Adding a region

A new region must provide:

- `regions/<slug>/region.json`, following the existing schema;
- one acquisition/orchestration module under `cartography/regions/`;
- source adapters or source-specific functions that normalize bathymetry,
  topography and imagery before invoking the shared renderer;
- a region-specific workflow documenting source coverage, projection,
  licences, attribution and acceptance constraints;
- site configurations under `regions/<slug>/sites/`;
- tests proving that the manifest, configurations, outputs and Web inventory
  agree.

Do not copy the React application, relief renderer, plate composer or
interactive exporter. A provider-specific adapter may be added when another
region uses different public data.

## Adding a site

Use the target region's workflow. At minimum, every published site must have:

- validated identity, coordinates, sources and source coverage;
- 2D and static 3D maps in topographic and aerial-imagery variants;
- a locator map and both printable sheets;
- a canonical interactive terrain package;
- responsive Web derivatives and downloads;
- configuration, provenance and automated checks;
- an initial-view equivalence check between the real route and every generated
  3D fallback/HD pair, following [INTERACTIVE-TERRAIN.md](INTERACTIVE-TERRAIN.md);
- full-resolution visual inspection and desktop/mobile interactive inspection.

Relief mapping never demonstrates access, authorization, present conditions or
safety. Document uncertainty instead of turning it into a geographic claim.

### Browser geometry gate for the site map

The server-rendered tests prove the route, manifest and asset contract. They do
not prove the final geometry of the regional site map. Run this additional gate
after generating the Web derivatives and before accepting a new site. It applies
to every regional landing map that displays site markers.

1. Open the final local Web build at the regional landing route, with the map
   image and fonts fully loaded. Test at a desktop viewport of `1280 × 720`
   with device-pixel ratio `2` and a mobile viewport of `390 × 844` with
   device-pixel ratio `1` (or record the nearest supported equivalents). Keep
   browser zoom at 100%.
2. In the browser DOM, inspect `.site-picker-map` and every
   `.site-map-marker`. For each marker, measure the `getBoundingClientRect()`
   of `.site-map-marker-dot` (point), `.site-map-marker-line` (connector), and
   `.site-map-marker-label` (cartouche). Record the computed values of
   `--label-shift-y`, `--label-offset`, `--label-width`, `--connector-angle`,
   and `--connector-width`.
3. The gate passes only when all of the following hold at both viewports:
   - the marker count equals the generated site inventory, and every marker has
     a non-empty point, connector and cartouche rectangle;
   - the point and cartouche remain inside the map rectangle, with no clipping
     or viewport overflow;
   - the cartouche does not intersect its own point, any other point, or any
     other cartouche;
   - the connector is rendered and visible, starts at the point centre, and
     reaches the intended left or right cartouche edge within `2 px`; check the
     transformed segment endpoints, not only the axis-aligned bounding box of
     a rotated line;
   - the connector does not pass through another point or cartouche, and no
     connector is absent, reversed, or hidden behind a cartouche;
   - the label text is not clipped or unintentionally wrapped, and its text
     rectangle is vertically centred inside the cartouche within `2 px`;
   - selecting the new site and exercising keyboard focus or touch does not
     introduce a new overlap, overflow, or hidden connector.
4. Save one desktop and one mobile screenshot, together with a compact record
   per site containing the side, cartouche width and height, label offsets,
   connector angle and length, point-to-connector error, connector-to-cartouche
   error, and the pass/fail result. A failing site is corrected through its
   regional layout parameters, then the complete two-viewport check is rerun.

For a reproducible first measurement, run this in DevTools and retain the
returned rectangles alongside the screenshots:

```js
(() => {
  const rect = (element) => {
    const { left, top, right, bottom, width, height } =
      element.getBoundingClientRect();
    return { left, top, right, bottom, width, height };
  };
  const variables = [
    "--label-shift-y",
    "--label-offset",
    "--label-width",
    "--connector-angle",
    "--connector-width",
  ];
  const map = document.querySelector(".site-picker-map");
  if (!map) throw new Error(".site-picker-map not found");
  return {
    map: rect(map),
    markers: [...map.querySelectorAll(".site-map-marker")].map((marker) => {
      const style = getComputedStyle(marker);
      return {
        site: marker.getAttribute("href"),
        side: marker.classList.contains("label-left") ? "left" : "right",
        point: rect(marker.querySelector(".site-map-marker-dot")),
        connector: rect(marker.querySelector(".site-map-marker-line")),
        label: rect(marker.querySelector(".site-map-marker-label")),
        css: Object.fromEntries(
          variables.map((name) => [name, style.getPropertyValue(name).trim()]),
        ),
      };
    }),
  };
})()
```

## Releasing

1. Run the affected region's configuration checks.
2. Run the complete Python suite.
3. If generated artifacts moved without regeneration, compare their SHA-256
   hashes before and after the move.
4. Run the unified Web application's lint, tests and production build.
5. Inspect the affected routes and interactions on desktop and mobile.
6. Review the complete task-scoped diff.
7. Commit and push the reviewed state to GitHub.
8. Publish the exact `apps/web/` tree through Sites and verify production.

The exact hosting invariant and release sequence are in
[DEPLOYMENT.md](DEPLOYMENT.md).
