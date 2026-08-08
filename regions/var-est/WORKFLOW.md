# Var Est topo-bathymetric workflow

This region is an autonomous DiveTopo region for the Estérel coast around
Saint-Raphaël, Le Dramont, Anthéor and Le Trayas. It is not a PACA subregion.
Its canonical route is `/var-est`; its site routes will be
`/var-est/<language>/sites/<slug>`.

## Regional boundary

The first-wave inventory is limited to exactly five sites:

- Les Pyramides;
- Sec de l’Île d’Or;
- Arche du Dramont;
- Cathédrale du Trayas;
- Le Village;

The following sites are explicitly deferred and their commits must not be
cherry-picked into the first wave:

- Sec des Suisses / Cigales;
- La Vitrine;
- Péniches d’Anthéor;
- Lion de Mer.

Only a site listed in `region.json` and carrying `web.published: true` is part
of the generated public inventory. A new site remains a draft with
`web.published: false` until full-resolution map QA, interactive QA, regional
marker QA and an explicit publication decision have all passed.

## Repository paths

```text
regions/var-est/region.json
regions/var-est/sites/<slug>.json
regions/var-est/outputs/<slug>-topobathy-2d.jpg
regions/var-est/outputs/<slug>-topobathy-2d-ortho.jpg
regions/var-est/outputs/<slug>-topobathy-3d.jpg
regions/var-est/outputs/<slug>-topobathy-3d-ortho.jpg
regions/var-est/outputs/<slug>-locator-var-est.jpg
regions/var-est/outputs/<slug>-planche.jpg
regions/var-est/outputs/<slug>-planche-topographique.jpg
regions/var-est/outputs/interactive-terrain/<slug>/
regions/var-est/outputs/var-est-regional-relief.png
apps/web/public/maps/var-est/<slug>/
apps/web/public/maps/var-est/var-est-regional-relief.png
```

The canonical generated maps and interactive packages live under
`regions/var-est/outputs/`. The Web tree contains publication derivatives,
not canonical render products.

## Detailed-map sources and projection

- Common CRS: RGF93 v1 / Lambert-93, `EPSG:2154`.
- Detailed bathymetry and land elevation: Shom–IGN Litto3D PACA 2015,
  one-metre gridded DTM, with the vertical reference and archive members pinned
  in each site configuration.
- Land imagery: IGN BD ORTHO. The capture date is checked for each site and
  recorded in its configuration; it is never inferred from another site.
- Regional map: EMODnet Bathymetry DTM 2024 offshore, Shom–IGN Litto3D PACA
  2015 nearshore, GEBCO 2024 only as a no-data fallback, IGN RGE ALTI on land,
  and the official Shom–IGN land-sea limit for the coastline mask.

The regional map receives its own Var Est extent and marker layout after every
target site's canonical marker has been integrated. It must not reuse the PACA
image or present itself as a crop of the PACA page. Its canonical image is used
both for the homepage card and the regional site picker; the Web copy is a
derived asset whose hash is recorded in the regional manifest.

For the first regional integration commit, `regionalMap.status` is
`awaiting-shared-builder`: the canonical and Web paths are reserved but no map
is fabricated, cropped from PACA, or published. The global coordinator owns
the shared regional builder. Map generation and its visual QA therefore belong
to a second, targeted commit after that builder is integrated.

Do not download source data or dependencies without explicit authorization.
Rendering may reuse a valid local cache only after its projection, extent,
resolution, signal and provenance have passed the pipeline checks.

`cartography.regions.var_est` owns the Var Est region identity and output
contract. It reuses the existing Lambert-93 Litto3D cache validation functions
and the shared renderer; this source-adapter reuse does not make Var Est part of
the PACA inventory or route.

## Migrating Les Pyramides

Les Pyramides is already published from
`regions/paca/sites/les-pyramides-cap-dramont.json`. Migrate it into Var Est
without canonical regeneration unless QA finds a concrete defect requiring a
separate decision:

1. record SHA-256 hashes for every canonical output, interactive-terrain file
   and Web derivative before the move;
2. move the configuration and canonical outputs to the Var Est paths, changing
   the region identity and publication paths only, and remove only the
   now-stale Les Pyramides entry from `regions/paca/region.json` as the narrowly
   approved cross-region exception;
3. move the Web derivatives from `/maps/paca/` to `/maps/var-est/`;
4. rebuild manifests without rendering the site;
5. compare all content hashes with the recorded pre-migration hashes;
6. verify the real Var Est routes, downloads and interactive initial view on
   desktop and mobile.

A moved artifact is inherited, not freshly rendered. The migration must not be
described as new cartographic validation.

## Integrating site commits

Site work arrives as task-scoped commits from separate worktrees. Before each
cherry-pick:

1. inspect the commit and confirm that it touches only the announced site and
   its allowed outputs;
2. reject or split changes to another region, the homepage, versions, releases
   or deployment files;
3. cherry-pick the commit, resolve only region-local conflicts, and rerun the
   site configuration checks;
4. keep a new site's `web.published` value false;
5. inspect the resulting diff before accepting the next site.

Do not silently generalize shared code while integrating a site. Discuss a
required shared structural change with the global coordinator first.

## Regional acceptance gate

Before proposing publication or the final zone commit:

1. ensure `region.json`, every site configuration, canonical output and Web
   manifest agree on region, slug, route and publication state;
2. verify that drafts are absent from every generated public inventory;
3. inspect the regional image at full resolution and verify coastline, relief,
   attribution, extent, marker positions and marker-to-site correspondence;
4. run the repository's browser geometry gate at `1280 × 720` DPR 2 and
   `390 × 844` DPR 1, retaining the measurements and screenshots;
5. inspect each published site route and interactive terrain on desktop and
   mobile, including labels, controls, initial view and downloads;
6. run the affected regional checks, the complete Python suite, and the Web
   lint, tests and production build without installing dependencies;
7. review the complete task-scoped diff and confirm that no other region,
   homepage, version, release or deployment file changed.

The final zone commit remains local. It is not pushed, released or deployed.
