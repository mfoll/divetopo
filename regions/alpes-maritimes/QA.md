# Alpes-Maritimes v1.5 regional QA

Validated locally on 2026-08-15 on the autonomous Alpes-Maritimes worktree.
The current inventory contains five published packages and Cap Gros as a
pending/preparing package. The older v1.4 measurements below remain historical
where they are not superseded by the current checks.

## Inventory and artifacts

- Exactly five configurations are published: Grande Baie, Pointe de la
  Causinière, La Vaquette, La Tradelière and Grotte à Corail.
- The regional map manifest contains six planning entries, with five published
  sites and Cap Gros marked `preparing`. The regional and public terrain
  manifests contain five packages; Cap Gros is absent from both.
- Every site has topographic and orthophoto 2D maps, both static 3D styles, two
  planches, the complete seven-file terrain package and fourteen Web map
  derivatives.
- Cap Gros remains QA-able only below `regions/alpes-maritimes/` with
  `web.published=false`; it has no public route, sitemap entry, Web asset or
  terrain-manifest entry.

## Full-resolution regional map

The canonical PNG and Web derivative are byte-identical, `1864 × 1440 px`,
SHA-256 `637d730966fc0b4e2bbb27a7a1e26aa29a94715a569720cee49151dbeea79759`.
Inspection at native resolution covered Théoule, Cannes and the Lérins Islands,
Antibes, Nice, Cap-Ferrat and Villefranche. The coastline, islands, ports and
bays are continuous. No triangle, diagonal closure, checkerboard, tile join,
grey/NoData patch or misleading coastal artifact remains visible.

The five marker percentages were recomputed from the declared WGS84 bounds and
coordinates by the regional builder. Browser measurement recovered their
positions with a maximum residual of `0.26` percentage point, attributable to
the rendered map border, while retaining the declared geographic order and
locations.

## Regional Web rendering

Current rendering was inspected in French and English at desktop `1280 × 720`
and mobile `390 × 844`, in light and dark themes.

- Desktop map box: `302.4 × 233.6 px`; mobile map box:
  `346.8 × 267.9 px`.
- Five published labels are visible and inside the map at both viewports, with
  no label-label or label-dot collision. Cap Gros is represented only by the
  preparing/planned state and has no public cartouche or link.
- The Cap-Ferrat/Villefranche cluster uses three distinct left-hand cartouches
  and connectors. La Tradelière and La Vaquette use separate right-hand
  cartouches; La Vaquette is offset beyond the scale footprint.
- No horizontal overflow was measured at either viewport. The mobile page
  width and scroll width were both `390 px`; the map remained proportionate.
- Selected and unselected labels remain legible in both themes. Measured label
  colors were white on `rgb(6, 28, 36)` for the selection and
  `rgb(8, 33, 42)` on the translucent light cartouches for the others.
- The shared mobile fix places the terrain scale above the two-line
  attribution: `sourceScaleOverlap=false`,
  `copyrightScaleOverlap=false`, `horizontalOverflow=false` at `390 × 844`.
- No route-specific browser console errors were observed on the final local
  reload; one transient HMR connection message occurred while the dev server
  was being restarted during generation.

## Routes and publication state

Each of the five visible cartouches was activated by click and by keyboard.
Every activation produced the expected `/alpes-maritimes/fr/sites/<slug>`
route, selected the matching marker, showed the matching article heading and
mounted a terrain viewer. The dropdown contains the same five slugs and was
also exercised. English links use the matching `/en/` routes. The geographic
dots are deliberately non-interactive because three points overlap at regional
scale; clicking their cluster does not open a wrong site.

The planned-site list contains Cap Gros in French and English. All five
published site configurations have `web.published=true`; Cap Gros alone has
`web.published=false`.
The five published FR/EN routes return 200, while Cap Gros and its local
calibration route remain 404 in the published app. The regional dropdown and
keyboard activation were exercised on a published marker.

## Automated checks

- Full Python suite: 134/134 tests passed via the repository's standalone
  `unittest` files.
- Web lint: passed with 11 pre-existing warnings and zero errors. Web tests:
  41/41 passed; the production build also passed, with the existing chunk-size
  and dynamic-route classification warnings.
- Final `git diff --check`, manifest consistency and region-scope checks are
  required immediately before the regional commits.
