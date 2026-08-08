# Var Est regional QA

## Intermediate integration checkpoint, 8 August 2026

Status: **not publishable**. This checkpoint integrates the five first-wave
site commits and records the QA that is possible before the shared regional
map builder and Var Est Web route exist. Every site retains
`web.published: false`.

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
- The complete Python suite passes.
- Git recognizes every moved Pyramides binary as a 100% rename. No map or
  terrain asset was regenerated. Only the stale Pyramides inventory entry is
  removed from `regions/paca/region.json`; no other PACA site or content is
  changed by the regional correction.

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

## Deferred regional gates

- The canonical Var Est regional map and Web derivative are absent by design;
  `regionalMap.status` is `awaiting-shared-builder`.
- Marker/cartouche geometry, desktop/mobile route behavior, downloads, and
  interactive controls cannot be tested until the globally coordinated shared
  builder and Var Est Web route are integrated.
- `apps/web/node_modules` is absent in this restored worktree. No dependency
  installation was authorized, so Web lint, tests, and production build were
  not run. The existing shared PACA Web manifest still points at Pyramides and
  must be updated by the global Web integration; it is deliberately untouched
  here.
- No homepage, release, version, deployment, or publication action is included
  in this checkpoint.
