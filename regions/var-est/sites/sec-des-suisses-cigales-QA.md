# Sec des Suisses / Cigales — QA v1.5

Status: **site package complete; regional publication deliberately disabled** (`web.published=false`). The exact slug is `sec-des-suisses-cigales`; no second fiche was created.

## Regional integration boundary

This regional commit retains only the canonical package under `regions/var-est/`: the site configuration, QA record, six static outputs and seven interactive-terrain files. The autonomous site SHA also contained fourteen map derivatives under `apps/web/public/maps/var-est/sec-des-suisses-cigales/` and seven terrain derivatives under `apps/web/public/terrain/sec-des-suisses-cigales/`; they were audited but are deliberately excluded here. This commit changes no `region.json`, manifest, route, sitemap, shared Web asset, release file or publication surface. With `web.published=false`, the package remains QA-able region-locally and is not exposed publicly.

## Identity and naming

- Canonical name: **Sec des Suisses**.
- Documented aliases: **Sec des Cigales / Les Cigales**. The [official Var Department PDESI list](https://var.fr/documents/d/departement-du-var/aad-2025_05-cp-1-pdf) names the relief “Sec des cigales (ou des suisses)”; the [Saint-Raphaël municipal description](https://saint-raphael.com/fr/saint-raphael/mer/monde-sous-marin/le-milieu-sous-marin) describes Les Cigales at Le Dramont as three rocks reaching nearly 40 m. These references establish one relief under one canonical fiche.
- Source-derived render anchor: `1011905 E, 6264395 N` in RGF93 / Lambert-93 (EPSG:2154), converted to `43.41021569 N, 6.85048164 E`.
- Public guide reference checked independently: `43.4094833 N, 6.8508333 E` (`1011937.434 E, 6264315.077 N` in EPSG:2154). It is approximately 80 m from the render anchor and falls on the same three-rock chain. It remains an identity/reference coordinate, not a second site or a hidden coordinate substitution.

## Source and reference systems

- Bathymetry and land elevation: [Shom–IGN Litto3D PACA 2015](https://services.data.shom.fr/INSPIRE/telechargement/prepackageGroup/LITTO3D_PACA_2015_PACK_DL/prepackage/1010_6265/file/1010_6265.7z), 1 m MNT, RGF93 / Lambert-93 (EPSG:2154), vertical reference IGN69, source NoData `-99999`.
- Archive SHA-256: `e9bb27247a3603a630bd655e6f8e68cf397ca1bd8a99e5238404c97d708f35f9`.
- Members used: `1011_6265` and `1012_6265`, both `MNT1m/LITTO3D_FRA_*_MNT_20150529_LAMB93_RGF93_IGN69.asc`. The raw archive remains outside Git.
- Orthophoto: IGN BD ORTHO WMS layer `HR.ORTHOIMAGERY.ORTHOPHOTOS`, queried from `https://data.geopf.fr/wms-r/wms`; the matching capture metadata returned `2023-07-13Z`. Focus texture resolution is 0.4 m and context texture resolution is 1 m.

## Coverage, NoData and defensible extent

- The source-derived anchor reproduces the requested starting coverage using the raw NoData mask: radius 50 m **100.000%**, radius 150 m **100.000%**, radius 300 m **86.9839%** (reported as 87%). The package therefore does not claim complete 300 m coverage.
- The 2D footprint contains **5.6%** cells with neither bathymetry nor elevation. This is a deep offshore edge gap shown with the maximum-depth colour only and excluded from contours and terrain.
- The 3D crop contains **2.3%** invalid source samples. Corresponding mesh facets are omitted; no surface or isobath-derived terrain was fabricated.
- Defensible site extent: the validated focus/context boxes and the interactive footprint are limited to the real Litto3D coverage, with maximum display depth `40 m`. The interactive physical footprint is `261 × 361 m` and its displayed view width is `220 m`.

## Calibration and pose validation

- The local-only calibration interface was exercised from the isolated dev overlay using `?camera-calibration`: camera drag changed the rendered view, reset restored the initial pose, `Enregistrer ce cadrage` stored the exact site pose, and the single grouped export produced schema `divetopo-camera-calibration-collection-v1` with one `calibrations` array entry. No per-site JSON download control exists.
- Final exported semantic values: `zoom=0.78`, `orbitAzimuthDeg=0`, `cameraElevationDeg=22.97`, `panRightM=0`, `panUpM=7.78`.
- Final exact pose retained in the site configuration: `cameraPositionM=[0,380,920]`, `cameraTargetM=[0,-10,0]`. The exact pose is authoritative; the semantic values are retained for diagnostics and manifest conversion.
- Static 3D views, dynamic captures, Web derivatives and both planches were regenerated after this pose validation. The calibration patch was removed from the actual working tree; `python3 tools/camera-calibration/manage.py check-release` passes.

## Delivered assets

- Four canonical maps at `2474 × 1712 px`: topographic and orthophoto 2D plans, plus topographic and orthophoto static 3D views.
- Two presentation boards at `5400 × 3250 px`: `planche-topographique` and orthophoto `planche`.
- Canonical interactive terrain: schema 2, EPSG:2154, grid `261 × 361`, `187200` triangles, elevation range `−40.0` to `+13.8780 m`, 5 m vector isobaths at 8 levels, 19 polylines and 1725 points. Reprojection residual maximum is `0.000422142 m`; the vector validation is within tolerance. The seven terrain files remain only in the canonical regional package; the site-local Web terrain copy from the autonomous SHA is not integrated.
- Web-derivative QA: both 2D JPEGs, desktop/mobile dynamic 3D WebP captures, full-resolution JPEG downloads and board previews were inspected in the autonomous SHA, but all fourteen map derivatives and seven terrain derivatives under `apps/web/public/` are explicitly excluded from this regional commit.

## Visual and page QA

- Full-resolution inspection completed for all four canonical maps, both 5400 px planches, the interactive topographic/orthophoto textures, and the autonomous-SHA final desktop/mobile terrain captures. North arrows, scales, depth labels and source/licence footers remain legible; no broken contour geometry or image corruption was observed.
- The orthophoto perspective is softer/banded than the topographic texture because the 1 m context imagery is stretched in perspective; coastline and exposed-rock alignment remain coherent. This is recorded as a visual quality caveat, not a fabricated-data issue.
- Final dynamic equivalence verification passed all six comparisons at the `0.985` threshold: correlations `0.9986–0.9995` for desktop and full JPEGs, and `0.9938–0.9940` for mobile WebP.
- In the isolated local manifest overlay, FR and EN routes returned HTTP 200. Browser smoke QA passed at `1280 × 800` and `390 × 844`: canonical site identity visible, no horizontal overflow, canvas rendered, no console warnings/errors, and normal routes showed no calibration panel. The FR/EN page screenshots were inspected separately.
- Shared-shell observation outside this site scope: the FR page carries French content and `og:locale=fr_FR`, but the root HTML element still reports `lang="en"`. No shared Web component was changed under the single-site constraint.

## Reproducible checks and scope guard

- `/Users/follm/home-projects/divetopo/.venv/bin/python -m cartography.regions.var_est --check regions/var-est/sites/sec-des-suisses-cigales.json`: pass.
- `/Users/follm/home-projects/divetopo/.venv/bin/python -m cartography.regions.var_est --render-only regions/var-est/sites/sec-des-suisses-cigales.json`: pass with the documented 5.6%/2.3% NoData warnings.
- `/Users/follm/home-projects/divetopo/.venv/bin/python -m cartography.plate regions/var-est/sites/sec-des-suisses-cigales.json --land-style both`: pass.
- The autonomous SHA's `/opt/homebrew/bin/node /tmp/divetopo-web-capture/scripts/verify_unified_terrain_capture.mjs` capture check passed; its `apps/web/public/` capture output is intentionally absent from this regional commit.
- `python3 tools/camera-calibration/manage.py check-release`: pass; the published working tree has calibration disabled.
- No `region.json`, regional/global manifest, sitemap, shared Web component, release file, push or deployment was changed. The local FR/EN page overlay was temporary and isolated; it is not a publication manifest.
