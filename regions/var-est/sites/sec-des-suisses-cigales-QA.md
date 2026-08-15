# Sec des Suisses / Cigales — QA v1.5

Status: **regional package regenerated and QA-able; regional publication deliberately disabled** (`web.published=false`). The exact slug is `sec-des-suisses-cigales`; the canonical display name is **Sec des Suisses**.

## Regional integration boundary

This package is limited to `regions/var-est/` plus the Var Est planning manifest. No public Web asset was restored from the autonomous site SHA: `apps/web/public/maps/var-est/sec-des-suisses-cigales/` and `apps/web/public/terrain/sec-des-suisses-cigales/` are intentionally absent. The package does not change routes, sitemap, the global terrain manifest, shared tests, other regions, or publication metadata. The temporary pending overlay was fully restored before this QA.

The 14 regenerated Web derivatives are QA-only files in `/tmp/divetopo-sec-web-pending/`; they are not copied into Git or any published surface while the site remains pending.

## Identity and naming

- Canonical name: **Sec des Suisses**.
- Documented aliases: **Sec des Cigales / Les Cigales**. The [official Var Department PDESI list](https://var.fr/documents/d/departement-du-var/aad-2025_05-cp-1-pdf) names the relief “Sec des cigales (ou des suisses)”; the [Saint-Raphaël municipal description](https://saint-raphael.com/fr/saint-raphael/mer/monde-sous-marin/le-milieu-sous-marin) describes Les Cigales at Le Dramont as three rocks reaching nearly 40 m. These references establish one relief under one canonical fiche.
- Render anchor: `1011905 E, 6264395 N` in RGF93 / Lambert-93 (EPSG:2154), converted to `43.41021569 N, 6.85048164 E`.
- Public guide reference checked independently: `43.4094833 N, 6.8508333 E` (`1011937.434 E, 6264315.077 N` in EPSG:2154). It remains an identity/reference coordinate, not a second site or a hidden coordinate substitution.

## Source and reference systems

- Bathymetry and land elevation: [Shom–IGN Litto3D PACA 2015](https://services.data.shom.fr/INSPIRE/telechargement/prepackageGroup/LITTO3D_PACA_2015_PACK_DL/prepackage/1010_6265/file/1010_6265.7z), 1 m MNT, RGF93 / Lambert-93 (EPSG:2154), vertical reference IGN69, source NoData `-99999`.
- Archive SHA-256: `e9bb27247a3603a630bd655e6f8e68cf397ca1bd8a99e5238404c97d708f35f9`.
- Members used: `1011_6265` and `1012_6265`, both official `MNT1m/LITTO3D_FRA_*_MNT_20150529_LAMB93_RGF93_IGN69.asc` members. No source ASC was edited.
- Orthophoto: IGN BD ORTHO WMS layer `HR.ORTHOIMAGERY.ORTHOPHOTOS`, queried from `https://data.geopf.fr/wms-r/wms`; matching capture metadata is `2023-07-13Z`. Focus texture resolution is 0.4 m and context texture resolution is 1 m.

## Coverage, NoData and defensible extent

The extent was widened to the maximum reasonable window covered by the same two official Litto3D source members, without filling NoData:

- Focus bbox: `[1011200, 6264200, 1012600, 6265000]`, raw source valid **96.7262%**, raw NoData **3.2738%**.
- Context bbox: `[1011200, 6264100, 1012600, 6265000]`, raw source valid **90.9345%**, raw NoData **9.0655%**.
- Interactive source footprint: `[1011305, 6264145, 1012505, 6264645]`, raw source valid **92.5825%**, raw NoData **7.4175%**.
- Aligned cached context: valid **91.024603%**, NoData **8.975397%**. Aligned cached focus: valid **96.768125%**, NoData **3.231875%**. Source rows remain north-to-south; source NoData remains `-99999`.
- Final terrain valid-mask bitset: `101771/109782`, valid **92.702811%**, NoData **7.297189%**. This is a source-derived mask after grid encoding, not a filled surface.
- Physical interactive footprint: **1200 × 500 m**, with a `513 × 214` terrain grid. The display maximum depth remains `40 m`.
- Native render warnings are explicit and unchanged by fabrication: **3.2%** of the 2D footprint has neither bathymetry nor elevation, and **7.2%** of the 3D crop has neither. Invalid 3D facets are omitted; no surface, contour or height value is filled artificially.

The initial cache attempt used `np.flipud(values)` even though GDAL's ASC `ReadAsArray()` was already north-up. That produced the wrong alignment and the incorrect preliminary NoData figures. The cache was rebuilt without the flip, from the official ASC values, and the corrected orientation is recorded in `terrain.json` as `sourceRows: north-to-south`, `sourceColumns: west-to-east`, rotation `0`.

The related orthophoto validation failure was exact: `ValueError: IGN BD ORTHO context is not at 1 m: ...context-orthophoto.tif`. The context image was re-downloaded at 1 m; the current Var Est source check passes.

The terrain export itself completed with exit code 0 using the shared runtime and an isolated `/tmp` output directory. The only error in the follow-up copy/inspection command was the macOS `find` incompatibility: `find: -printf: unknown primary or operator`. The copy had completed before that diagnostic-only failure; the final file checks use portable `find -print`/Python inspection.

## Calibration and pose validation

- Calibration provenance: schema `divetopo-camera-calibration-collection-v1`, exported at `2026-08-15T06:21:38.384Z`, source SHA-256 `18269204b26988ad94ccb6decb60ff032d553492a74e3fa50a33ece70e5ae6ce`. The raw Downloads JSON was not copied into Git.
- Final semantic pose: `zoom=0.65`, `orbitAzimuthDeg=-14.56`, `cameraElevationDeg=22.61`, `panRightM=-34.44`, `panUpM=48.59`, `centerOffsetEastM=0`, `centerOffsetSouthM=0`.
- Final exact pose: `cameraPositionM=[-203.2828,336.4402,916.6475]`, `cameraTargetM=[28.5751,-47.6519,23.7785]`.
- The dev/local calibration mode remains grouped-export only, with camera movement, visible parameters and one collection JSON export. It is not exposed in the published build and does not replace QA. The release check confirms calibration controls are disabled for release.
- `terrain.json` records EPSG:2154, north-to-south source orientation, zero quarter-turn rotation, the calibrated view metadata, and texture UV origin `northwest`.

## Delivered assets

- Four regenerated native maps at `2474 × 1712 px`: topographic and orthophoto 2D plans, plus topographic and orthophoto static 3D views.
- Two regenerated presentation boards at `5400 × 3250 px`: `planche-topographique` and orthophoto `planche`.
- Canonical regional interactive terrain: schema 2, grid `513 × 214`, `218112` triangles, physical footprint `1200 × 500 m`, elevation range `−40.0` to `+43.583572 m`, vertical exaggeration `1.6`, 8 vector-isobath levels, 46 polylines and 5753 points. Reprojection residual mean is `2.8769e-06 m`, p95 `4.0839e-08 m`, maximum `0.0094321 m`, and validation is within tolerance.
- The seven terrain files remain only in `regions/var-est/outputs/interactive-terrain/sec-des-suisses-cigales/`. The five-site regional terrain manifest was not expanded.
- Pending Web derivatives were regenerated from the fresh native captures in the isolated temp directory only: 2D JPEGs, desktop/mobile dynamic WebP variants, full-resolution JPEG downloads and 1800 px board previews. They are not publication assets.

## Regional-map layout QA

The pending entry remains outside `sites` and is represented only in `plannedSites`: `sites=5`, `plannedSites=6`, status `preparing`, `web.published=false`.

- Locator: `xPercent=44.0`, `yPercent=66.3`.
- Label layout: `side=right`, `lines=["Sec des", "Suisses"]`, `shiftYRem=-4.8`, `labelOffsetRem=5.4`, `widthRem=5.8`, `connectorAngleDeg=325`, `connectorWidthRem=1.4`.
- Exact geometry simulation of the production connector/label algorithm at `1280 × 720`: Sec des Suisses has no rectangle intersection with Arche du Dramont or Cathédrale, with approximately `7.5 px` and `8.2 px` clearance respectively; the selected connector route intersects zero label obstacles.
- Exact geometry simulation at `390 × 844`: no rectangle intersection with Arche du Dramont or Cathédrale, with approximately `6.5 px` and `12.8 px` clearance respectively; the selected connector route intersects zero label obstacles.
- Full-format raster inspection covered all six regional marks, the frame, scale and north arrow. The Sec des Suisses cartouche no longer masks the Arche du Dramont cartouche or its point/connector.

The browser control attempt was not reliable: the isolated preview returned a connection-refused/data-error page when reopened. Browser FR/EN desktop/mobile smoke QA is therefore **not claimed as passed**. Delivery is based on the full-resolution native renders plus the exact responsive geometry simulation above. No route was added; the normal pending UI remains dot-only until publication authorization.

## Visual and page QA

- Full-resolution inspection completed for all four native maps, both 5400 px boards, and the regenerated interactive topographic/orthophoto textures. North arrows, scales, depth labels, contours and source/licence footers are present and legible.
- The widened 2D maps show the added land/offshore extent and contours where valid. The 3D maps preserve the calibrated pose and omit only invalid source facets at the documented NoData edges. The orthophoto perspective is softer than the topographic texture; this is a source/rendering characteristic, not fabricated data.
- No public overlay remains: the five other pending overlays and the Var Est Sec des Suisses overlay were restored outside the worktree's tracked surfaces, and `apps/web/public` has no site-specific pending assets.

## Reproducible checks and scope guard

- `/Users/follm/home-projects/divetopo/.venv/bin/python -m cartography.regions.var_est --check regions/var-est/sites/sec-des-suisses-cigales.json`: pass.
- `/Users/follm/home-projects/divetopo/.venv/bin/python -m cartography.regions.var_est --render-only regions/var-est/sites/sec-des-suisses-cigales.json`: pass; warnings are the documented 3.2% 2D and 7.2% 3D source gaps.
- `/Users/follm/home-projects/divetopo/.venv/bin/python -m cartography.interactive regions/var-est/sites/sec-des-suisses-cigales.json --output /tmp/divetopo-sec-terrain`: pass; regional seven-file copy was checked separately.
- `/Users/follm/home-projects/divetopo/.venv/bin/python3 tools/camera-calibration/manage.py check-release`: pass; calibration remains dev/local only.
- The Web build/lint and browser smoke remain unverified in this worktree because the dependency/preview environment is unavailable; no shared tests were modified or used as a substitute.
- No `region.json`, shared test, route, sitemap, global terrain manifest, `apps/web/public` asset, release file, push or deployment was changed.
