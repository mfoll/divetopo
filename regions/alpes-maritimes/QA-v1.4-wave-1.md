# Alpes-Maritimes v1.4 first-wave integration QA

## Scope

The regional inventory contains exactly five unpublished site drafts:

1. Grande Baie – Cap-Ferrat
2. Pointe de la Causinière – Cap-Ferrat
3. La Vaquette
4. La Tradelière
5. Grotte à Corail – Villefranche

Cap Gros and La Fourmigue d’Antibes are excluded because no continuous MNT was
validated for their intended scope. Rascouï, Grand Boule, La Lauve, La Fouillée
and Enfer de Dante remain deferred. None of these seven sites is present in the
regional inventory.

## Integrated site commits

- La Vaquette: source `be5bd3247489a918fe8511a1010ea1fe4a335aed`,
  cherry-picked as `9aabfbb`.
- La Tradelière: source `cff811fe47dc27423ae6ec71e748ca2043385dd1`,
  cherry-picked as `a23fde1`.
- Grotte à Corail – Villefranche: source
  `efe2986284ce4db80a8c35eb89c081f4299e12db`, cherry-picked as `e45b75c`.
- Pointe de la Causinière – Cap-Ferrat: source
  `1927f594f74537c4064e170ead8a480b85e7782f`, cherry-picked as `5b385e5`.
- Grande Baie – Cap-Ferrat: source
  `43e353c15e083f7ced3d258e6b07edd20ac3c025`, cherry-picked as `4870982`.

## Integration checks

- Every inventory entry resolves to a configuration under
  `regions/alpes-maritimes/sites/` with the matching slug and
  `region: "alpes-maritimes"`.
- Every integrated configuration passes the live `validate_config` contract.
- Every integrated configuration declares `web.published: false`.
- All twelve static JPEGs were inspected directly from the committed
  full-resolution files. No source asset was regenerated during integration.
- The complete Python test suite passes in the existing local cartographic
  environment.
- The regional diff contains no PACA, Réunion, homepage, version, release or
  deployment change. The only shared-code change registers the autonomous
  Alpes-Maritimes source-validation contract.

## Asset status and remaining publication gates

- Grande Baie, Pointe de la Causinière and La Vaquette currently contain static
  2D/3D topographic outputs only.
- La Tradelière also contains a topographic interactive package, but no validated
  orthophoto texture.
- Grotte à Corail contains topographic and orthophoto static outputs and both
  interactive textures.
- The regional relief map and its byte-identical Web derivative are now
  integrated. The Web manifest intentionally contains `sites: []`, so none of
  the five drafts is exposed. No localized site route is integrated yet.

Full-resolution inspection found additional publication blockers:

- Grande Baie's QA note states `1600 × 1184`, while the committed 2D file is
  `1202 × 1002` and the 3D file is `1455 × 1069`. The 3D view also retains
  visible source-edge seams. The dimensions and intended canonical crop must be
  reconciled before publication.
- La Vaquette's 2D file has no compass, scale bar or attribution footer; its 3D
  compass is clipped at the top and the attribution footer is absent.
- La Tradelière is readable but uses a site-specific poster-style 2D layout and
  a differently instrumented 3D presentation. It has not yet passed a common
  regional presentation-equivalence gate.
- Pointe de la Causinière retains explicit open NoData boundaries; its oblique
  contour projection needs a final site-level review before responsive use.
- Grotte à Corail's orthophoto 3D view shows a strongly stretched and blurred
  land texture. It is not an acceptable publication fallback in its current
  form.

## Regional relief map QA

The regional relief builder was run without `--refresh` in the existing project
environment after integrating the shared polygon builder. Existing official
source caches were reused and the previously absent official Shom–IGN polygon
layer was fetched once. The final asset is an RGB PNG measuring `1864 × 1440`
pixels, with bounds:

- west: `6.896198253587896`
- south: `43.43069725776767`
- east: `7.387713264808246`
- north: `43.74269725776767`

The canonical output and its Web derivative are byte-identical, with SHA-256
`637d730966fc0b4e2bbb27a7a1e26aa29a94715a569720cee49151dbeea79759`.
The final build reports 67 Litto3D MNT5 tiles from three official archives and
an official Limite terre-mer polygon mask containing 647 features and 831,995
vertices. Its land area is `0.428`, with a difference below `0.001` from the
Natural Earth sanity guard. Full-resolution comparison with the earlier
line-flood map found a coherent and more detailed coastline and relief from
Théoule, Cannes and Lérins through Antibes, Nice and Villefranche. Lérins and
Cap-Ferrat remain continuous, small official harbour structures are retained,
and no implausible large SLCONS closure or terrestrial wedge survives offshore.

All five draft positions were projected against the generated bounds and
inspected on a temporary QA overlay that is not part of the committed output:

| Site | Map position | Pixel position |
| --- | --- | --- |
| Grande Baie – Cap-Ferrat | `86.50613%`, `18.13659%` | `1612, 261` |
| Pointe de la Causinière – Cap-Ferrat | `88.46154%`, `21.79933%` | `1648, 314` |
| La Vaquette | `11.53846%`, `83.27812%` | `215, 1198` |
| La Tradelière | `35.68255%`, `73.49271%` | `665, 1058` |
| Grotte à Corail – Villefranche | `83.95620%`, `16.72188%` | `1564, 241` |

The point locations are geographically plausible and remain inside the map
bounds. The three Cap-Ferrat/Villefranche labels overlap when rendered with the
temporary overlay's naive label placement. This does not affect the unlabelled
regional relief asset, but desktop/mobile marker and label geometry remains an
explicit publication gate.

The regional base-map gate therefore passes, while publication QA does not.
The five drafts must remain unpublished until their site-level asset blockers,
localized Web routing, responsive marker/label layout and complete interactive
requirements have been resolved, inspected and explicitly approved.
