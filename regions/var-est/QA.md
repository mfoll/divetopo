# Var Est regional QA

## Regional map and integration checkpoint, 8 August 2026

Status: **not publishable**. This checkpoint integrates the five first-wave
site commits and the canonical Var Est regional relief. Every site retains
`web.published: false`; the regional Web manifest consequently exposes no
site marker.

## Automated checks

- `region.json` contains exactly Les Pyramides, Sec de l’Île d’Or, Arche du
  Dramont, Cathédrale du Trayas, and Le Village.
- All five configurations pass `cartography.config.validate_config`, use
  `region: "var-est"`, have a usable regional marker, and remain unpublished.
- The combined schema-v2 interactive manifest indexes every complete package
  delivered in this wave: Les Pyramides, Sec de l’Île d’Or, Cathédrale du
  Trayas, and Le Village. Every recorded byte count and SHA-256 matches its
  file. Arche du Dramont has no delivered interactive package and is therefore
  absent rather than represented by invented files.
- All delivered JPEGs decode successfully. Their native dimensions were
  checked rather than normalized after the fact.
- Only Les Pyramides includes completed plates. Arche du Dramont lacks
  orthophoto variants and an interactive package; the other three new sites
  lack plates. These missing deliverables are publication blockers.
- The 31 configuration and Var Est interactive-manifest checks pass. The full
  Python discovery run passes 114 of 120 tests; its single failure is the
  intermediate inventory assertion that still expects the former
  `awaiting-shared-builder` status, and its five errors require autonomous
  region directories absent from this restored Var Est branch. Those tests
  and unrelated regions are intentionally not changed by this map-only
  integration.
- Git recognizes every moved Pyramides binary as a 100% rename. No Pyramides
  map or terrain asset was regenerated. Only the stale Pyramides inventory
  entry is removed from `regions/paca/region.json`; no other PACA site or
  content is changed by the regional correction.

## Full-resolution visual inspection

| Site | Material inspected | Result |
| --- | --- | --- |
| Les Pyramides | Both 5400 × 3250 plates and detailed 2D panels | Migration integrity passes, but the inherited plates still say `Côte d’Azur` and retain the PACA locator. They require a later Var Est plate regeneration after the shared regional map exists. |
| Sec de l’Île d’Or | 2474 × 1712 2D and static 3D, topographic and orthophoto | Fails. Long diagonal/truncated contour segments cross the maps. The 3D framing leaves excessive sky, clips the useful relief, and exposes implausible spikes; the orthophoto footer overlaps at the lower right. |
| Arche du Dramont | 2474 × 1712 topographic 2D and static 3D | Fails. Only two variants were delivered. The 3D view contains implausible needle-like peaks, crossing/truncated contours, clipped framing, and no interactive package. |
| Cathédrale du Trayas | 1202 × 1602 2D and 1455 × 1069 static 3D, topographic and orthophoto | Fails. Output dimensions do not match the regional 2474 × 1712 standard. The 3D view is dominated by a coastal wall rather than the target relief, and the 2D orthophoto contains a visible horizontal imagery seam. |
| Le Village | 2474 × 1712 2D and static 3D, topographic and orthophoto | Fails. Compass and footer elements are clipped at the frame edges; several contours terminate inside the image or cross awkwardly, and the orthophoto 3D land texture is visibly stretched. |

These observations are acceptance failures, not requests to regenerate inside
this integration task. The source worktrees remain responsible for corrected
site assets if the sites are to progress toward publication.

## Regional relief and marker QA

- `build_regional_relief.py var-est` completed with the approved project
  runtime and without `--refresh`. Existing official-source caches were reused;
  the previously absent Shom–IGN polygon WFS response was fetched once and
  cached.
- The canonical and Web PNGs both decode at 1864 × 1440, contain 1,731,260
  bytes, and match SHA-256
  `0f03a6ccac5581749ad92af1e00f2088028dc6b67880ba80247d4bb8ea3c8e57`.
  The same digest and bounds are recorded in `region.json` and the Web map
  manifest.
- The full-resolution image was inspected directly. The coastline is
  continuous, the land/ocean classification is plausible, and no tile seam,
  isolated component, or cross-coast relief bleed is visible. The official
  Shom–IGN LIMTM polygon mask contains 1,079 features and 844,310 vertices;
  its land fraction is 0.437, within 0.001 of the Natural Earth sanity guard.
- Compared with the previous line-flood mask, 48,678 pixels change, primarily
  along the coastline. Direct before/after inspection confirms that the large
  artificial closures at Trayas and in regional bays are removed, the detailed
  Dramont coast remains continuous, and the Îles de Lérins and smaller islets
  retain crisp, complete land and shoreline geometry without ghosting.
- The regional bounds are west 6.67894138, south 43.28603339, east
  7.09494138, north 43.59803339. Every configured site coordinate lies inside
  them:

| Site | WGS84 latitude | WGS84 longitude | Locator x | Locator y | Position check |
| --- | ---: | ---: | ---: | ---: | --- |
| Les Pyramides | 43.40906678 | 6.84388276 | 39.64937% | 60.56622% | Dramont cluster |
| Sec de l’Île d’Or | 43.40986826 | 6.84479991 | 39.86984% | 60.30934% | Dramont cluster |
| Arche du Dramont | 43.40916000 | 6.84610999 | 40.18476% | 60.53634% | Dramont cluster |
| Cathédrale du Trayas | 43.47500000 | 6.93000001 | 60.35063% | 39.43378% | Distinct north-east position |
| Le Village | 43.41131715 | 6.85673293 | 42.73835% | 59.84495% | East of the Dramont cluster |

The relative positions match the intended coastline geography. They are QA
coordinates only: `apps/web/content/var-est-map-manifest.json` keeps
`sites: []` because none of the five configurations is published.

## Deferred publication gates

- `regionalMap.status` is now `generated`, but site-level marker/cartouche
  geometry, desktop/mobile route behavior, downloads, and interactive controls
  remain deferred until the globally coordinated Var Est Web route exists and
  individual sites pass their asset QA.
- `apps/web/node_modules` is absent in this restored worktree. No dependency
  installation was authorized, so Web lint, tests, and production build were
  not run. The existing shared PACA Web manifest still points at Pyramides and
  must be updated by the global Web integration; it is deliberately untouched
  here.
- No homepage, release, version, deployment, or publication action is included
  in this checkpoint.
