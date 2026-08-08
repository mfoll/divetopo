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
- No regional locator map, responsive Web derivatives, regional Web manifest or
  localized route is integrated yet.

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

This commit completes regional inventory integration, not publication QA. The
five drafts must remain unpublished until the missing regional map, Web assets,
manifest, desktop/mobile marker geometry and complete interactive requirements
have been produced, inspected and explicitly approved.
