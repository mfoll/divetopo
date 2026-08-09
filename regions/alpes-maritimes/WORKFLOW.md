# Alpes-Maritimes topo-bathymetric workflow

This directory owns the autonomous DiveTopo region covering Théoule-sur-Mer,
Cannes, the Lérins Islands, Antibes, Nice and Villefranche-sur-Mer. It is not a
sub-region of `regions/paca/`: its inventory, outputs, interactive packages,
regional map and Web route are independent.

Read the root [WORKFLOW.md](../../WORKFLOW.md) before using this workflow.

## Regional contract

- Region slug: `alpes-maritimes`.
- Localized routes: `/alpes-maritimes/fr` and `/alpes-maritimes/en`; site
  routes live below
  `/alpes-maritimes/<language>/sites/<slug>`.
- Site configurations: `regions/alpes-maritimes/sites/`.
- Canonical maps and printable sheets: `regions/alpes-maritimes/outputs/`.
- Canonical interactive packages:
  `regions/alpes-maritimes/outputs/interactive-terrain/`.
- Regional locator map:
  `regions/alpes-maritimes/outputs/alpes-maritimes-regional-relief.png`.

The route and sitemap integration are supplied by the shared autonomous-region
Web contract. Homepage promotion remains a global integration task and must not
be changed from a site or regional worktree.

## Sources and projection

- Bathymetry and coastal elevation: Shom–IGN Litto3D PACA 2015, 1 m grid,
  distributed in Lambert-93 (`EPSG:2154`). The elevation reference is IGN69.
- Land imagery: IGN BD ORTHO, with the capture date verified per site.
- Regional relief: pinned GEBCO 2024 data. A derived regional map must retain
  its exact source identity, bounds and attribution in its manifest or build
  record.

Do not infer access, authorization, current conditions or dive safety from the
terrain. Do not combine depths in another vertical datum with Litto3D elevations
without an explicit transformation.

## Target inventory for the v1.4 first wave

Add an inventory entry to `region.json` only in the same integration change
that adds its real site configuration, so the repository never points to a
missing file.

The first wave is finalized with exactly these five published sites:

1. Grande Baie – Cap-Ferrat;
2. Pointe de la Causinière – Cap-Ferrat;
3. La Vaquette;
4. La Tradelière;
5. Grotte à Corail – Villefranche.

Cap Gros and La Fourmigue d’Antibes were removed from the first wave because no
continuous MNT was validated. Do not cherry-pick or inventory them.

The following sites are explicitly deferred. Do not cherry-pick or add them to
the regional inventory during this wave:

- Rascouï
- Grand Boule
- La Lauve
- La Fouillée
- Enfer de Dante

Each configuration declares `region: "alpes-maritimes"`. The five active sites
have complete 2D, 3D, planche, interactive and Web packages and were switched
to `web.published: true` together only after their site and regional QA gates
passed. Any later site starts with `web.published: false` until a new explicit
publication decision.

## Integrating a site worktree

1. Receive the exact site commit from the global coordinator.
2. Confirm that the site belongs to the active five-site wave. Do not
   cherry-pick a deferred or MNT-rejected site even if its commit is available.
   Both Cap-Ferrat replacements were admitted only after receipt of their exact
   SHA and explicit MNT-validation evidence.
3. Inspect its parent, file list and diff before cherry-picking it.
4. Reject or split any commit that touches another region, shared Web routing,
   release metadata, versions or deployment state.
5. Cherry-pick the site-local commit into this detached coordination worktree.
6. Confirm that the configuration and outputs live under this region, then add
   its `region.json` inventory entry if the site commit did not already do so.
7. Preserve existing generated artifacts byte-for-byte when migrating an
   already published site. Compare SHA-256 values before and after the move;
   do not regenerate it merely to change ownership.
8. Keep `web.published` false for every later site until explicit approval and
   complete site plus regional QA.

## Regional map gate

The regional map is a canonical regional output used by both the homepage card
and the regional landing page. It must be generated independently of the PACA
Web manifest, cover the full Théoule-to-Villefranche scope, use documented
geographic bounds, and keep all labels and markers legible at the homepage-card
crop and the full regional-page size.

Before acceptance, inspect the full-resolution source and the exact responsive
derivatives. Verify coastline and relief coverage, marker positions, label and
connector collisions, attribution, dimensions and hashes. An automated image
or manifest check is not a substitute for visual inspection.

## Regional acceptance gate

Before a publication-ready zone commit:

1. All five first-wave configurations are present in the regional inventory and
   validate against the live cartographic contract; the two Cap-Ferrat
   replacements have explicit MNT-validation evidence.
2. No deferred or MNT-rejected site has been cherry-picked or added to the
   regional inventory.
3. Exactly the five approved first-wave sites are published; no deferred or
   MNT-rejected site is exposed.
4. Canonical outputs and interactive packages are complete and their manifests
   agree with the inventory.
5. The regional map is inspected at full resolution and in its homepage-card
   and regional-page renderings.
6. Regional markers, labels and connectors pass the root workflow geometry gate
   at desktop and mobile sizes.
7. The localized overview and site routes pass server-rendered, responsive,
   keyboard and touch checks without exposing a draft.
8. The complete diff is region-scoped apart from explicitly coordinated shared
   integration, and contains no version, release, homepage-global or deployment
   change.

The completed measurements and visual findings are recorded in
[`QA.md`](QA.md). The regional commit is local only; it does not push, deploy,
or modify the global homepage.
