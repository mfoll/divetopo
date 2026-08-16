# La Vaquette — QA v1.4

Status: **site package complete; regional publication deliberately disabled** (`web.published=false`).

## Identity and source provenance

- Site: La Vaquette, Théoule-sur-Mer / Pointe de l'Esquillon.
- Coordinate used by the configuration: 43.48286950 N, 6.95291150 E; projected position 1,019,791.30 E / 6,272,870.51 N in RGF93 / Lambert-93 (EPSG:2154).
- Bathymetry and land elevation: Shom–IGN Litto3D PACA 2015, prepackage `1015_6275`, archive `1015_6275.7z`, member `1015_6275/LITTO3D_FRA_1019_6273_20150529_LAMB93_RGF93_IGN69/MNT1m/LITTO3D_FRA_1019_6273_MNT_20150529_LAMB93_RGF93_IGN69.asc`.
- Official archive URL: `https://services.data.shom.fr/INSPIRE/telechargement/prepackageGroup/LITTO3D_PACA_2015_PACK_DL/prepackage/1015_6275/file/1015_6275.7z`.
- Downloaded archive SHA-256: `057d0058ff354c150177abde92baf05172484c0cb1283cf1b2a5b7c8efb9c98e` (raw archive retained outside Git).
- Source grid: 1 m, EPSG:2154, vertical datum IGN69, tile bounds 1,019,000–1,019,999 E / 6,272,001–6,273,000 N, source elevation range −46.38 to +34.39 m.
- Orthophoto: IGN BD ORTHO layer `HR.ORTHOIMAGERY.ORTHOPHOTOS`; official WFS mosaic graph returned two matching department 06 / `pva2023` records at the site, both dated 2023-06-26. The aligned extracts used 0.4 m for the plan and 0.8 m for the relief texture.
- The Nice Côte d'Azur isobath source was checked and excluded: its official longitude extent starts at 7.099581 E, east of the site at 6.9529115 E. No contour from that source was used and no contour-only interpolation was performed.

## Source coverage and terrain contract

- The configured source cache and all source rasters pass the Alpes-Maritimes pipeline check.
- The Litto3D grid supplies a genuine gridded surface across the reef. The interactive package uses its source elevations directly; it contains no terrain completion or isobath-derived surface.
- The 2D crop contains 11.5% source NoData. A 6.7% deep offshore edge gap is rendered with the maximum-depth display colour only and is excluded from contours and terrain. The 3D crop contains 9.8% invalid samples; corresponding mesh facets are omitted.
- The site depth scale is capped at 42 m, matching the P1 target depth.
- Vector isobaths are derived analytically from the valid Litto3D mesh at 5 m intervals: 8 levels, 19 polylines, 2,887 points. Reprojection residual maximum is 0.00001572 m and is within tolerance.

## Delivered assets

- Four canonical maps at 2474 × 1712 px: topographic and orthophoto plans; topographic and orthophoto static 3D views.
- Two print boards at 5400 × 3250 px: topographic and orthophoto.
- Canonical interactive terrain package: 513 × 468 vertices, 478,208 triangles, elevation range −42.0 to +23.1202 m, 680 × 620 m footprint, `height.bin`, validity and isobath masks, vector isobaths, both 680 × 620 textures, and `terrain.json` schema 2.
- The seven canonical terrain files and seven Web terrain files are byte-identical.
- Fourteen site-scoped Web map derivatives: both 2D JPEGs, desktop dynamic 3D WebP captures at 960/1600/2474 px, mobile 960 px captures, two full JPEG downloads, and two 1800 px board previews.
- The topographic and orthophoto 2D plans are byte-identical. This is expected here: the crop has no materially exposed orthophoto-covered land to drape, and imagery is not fabricated or projected underwater. The two static 3D images and both interactive textures remain distinct where the exposed rock is visible.

## Visual and interactive QA

- Full-resolution inspection completed for all four canonical maps and both 5400 px boards: reef centred, depth labels legible, compass and scale unobstructed, credits present, no clipping, and NoData represented without inventing terrain.
- Dynamic capture verification passed for all six initial views. Correlation/MAE versus a fresh renderer capture: desktop WebP 0.9992 / 0.0048–0.0049; desktop full JPEG 0.9996–0.9997 / 0.0033; mobile WebP 0.9953–0.9954 / 0.0085–0.0087.
- Browser QA passed at 1280 × 720 and 390 × 844: no horizontal overflow, canvas backing store present, no console warnings or errors, topographic/orthophoto switching works, isobath hide/show works, drag rotation and wheel zoom change the rendered frame, reset restores the initial view, and the CSS/iOS-safe full-screen mode expands then exits correctly.

## Reproducible checks

- `/Users/follm/home-projects/divetopo/.venv/bin/python -m cartography.regions.alpes_maritimes regions/alpes-maritimes/sites/la-vaquette.json --check`: pass.
- `/Users/follm/home-projects/divetopo/.venv/bin/python -m unittest discover -s tests -v`: 124/124 pass.
- Web lint using the already-installed local dependency tree: 0 errors, 11 pre-existing warnings in unrelated PACA test pages/capture script.
- Web build and Node tests using the same local dependency tree: build pass; 35/35 tests pass. The build reports only the existing Vinext deprecation and chunk-size warnings.
- No dependency was installed. Raw Litto3D, WFS metadata and BD ORTHO extracts remain outside Git.
- No regional manifest, `region.json`, regional map, homepage, version or release file was changed; no push or deployment was performed.

## Extension nord v1.5

- Focus : 780×800 m → 780×1 250 m ; couverture 88,637 % → 90,424 %.
- Contexte : 780×840 m → 840×1 400 m ; couverture 89,097 % → 87,136 %.
- Footprint interactif : 680×820 m → 740×1 230 m ; couverture mesurée environ 92,7 %. Ajout de la tuile officielle `1019_6274` ; aucun remplissage des cellules NoData.
- Gain accepté : récif et relief au nord nettement étendus, isobathes cohérentes. Les trous de bord restent exclus des contours et du maillage. La pose interactive calibrée est inchangée ; seul le cadrage statique a été recentré pour éviter d’exposer la limite de source.
- QA plein format : deux plans 2474×1712, deux vues 3D 2474×1712 et deux planches 5400×3250 inspectés ; nord, échelle et crédits présents.
