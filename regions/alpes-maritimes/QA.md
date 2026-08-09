# Alpes-Maritimes v1.4 regional QA

Validated locally on 2026-08-08 after integrating the five autonomous site
packages and the shared Web fixes `8947940` and `7b9cc30`.

## Inventory and artifacts

- Exactly five configurations are published: Grande Baie, Pointe de la
  Causinière, La Vaquette, La Tradelière and Grotte à Corail.
- The regional map manifest contains five published sites and five published
  planning entries. The canonical terrain manifest contains five packages.
- Every site has topographic and orthophoto 2D maps, both static 3D styles, two
  planches, the complete seven-file terrain package and fourteen Web map
  derivatives.
- Cap Gros, La Fourmigue d’Antibes and the five deferred sites are absent from
  the published manifest.

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

Production rendering was inspected in French and English at desktop
`1440 × 1000` and mobile `390 × 844`, in light and dark themes.

- Desktop map box: `302.4 × 233.6 px`; mobile map box:
  `346.8 × 267.9 px`.
- Five labels visible, five inside the map, zero label-label collision and zero
  collision with the north arrow or scale at both viewports.
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
- Browser console errors and warnings: zero.

## Routes and publication state

Each of the five visible cartouches was activated by click and by keyboard.
Every activation produced the expected `/alpes-maritimes/fr/sites/<slug>`
route, selected the matching marker, showed the matching article heading and
mounted a terrain viewer. The dropdown contains the same five slugs and was
also exercised. English links use the matching `/en/` routes. The geographic
dots are deliberately non-interactive because three points overlap at regional
scale; clicking their cluster does not open a wrong site.

No `en préparation` or `in preparation` text is present in the French or
English regional render. All five site configurations have
`web.published=true`; no configuration in the regional inventory remains
unpublished.

## Automated checks

- Python suite: 124/124 tests passed after final publication assertions.
- Web production build: passed.
- Web suite: 37/37 tests passed after the shared Web fixes and regional
  publication assertions.
- Final `git diff --check`, manifest consistency and region-scope checks are
  required immediately before the regional commit.
