# QA site-local v1.5 — Plate aux Mérous

Date de contrôle : 2026-08-14. Périmètre strict : `var-ouest / plate-aux-merous` uniquement. La configuration conserve `web.published=false`.

## Identité et sources

- Identité retenue : **Plate aux Mérous**, Ouest des Embiez, Six-Fours-les-Plages, site reconnu dans la zone de la Basse de la Moulinière.
- Confirmation officielle de l’appellation dans la documentation Natura 2000 de la [Ville de Six-Fours-les-Plages](https://www.ville-six-fours.fr/pdf/decouvrir/charte-natura-2000.pdf), qui cite Plate aux mérous parmi les hauts-fonds des Embiez.
- Contrôle indépendant : la table C34 de [Martin et al., *An ecosystem-based index for Mediterranean coralligenous reefs*](https://www.researchgate.net/publication/393627190_An_ecosystem-based_index_for_Mediterranean_coralligenous_reefs_A_protocol_to_assess_the_quality_of_a_complex_key_habitat) donne `5.75100 E / 43.08044 N` et une profondeur indiquée de 34 m pour La Plate aux mérous.
- Coordonnées de travail WGS84 : `43.08044 N, 5.75100 E`. Conversion indépendante vers RGF93 / Lambert-93 : `EPSG:2154`, `E=924162.654, N=6224032.917`. Le point est identique dans `site_location_utm40s` et `locator_marker_utm40s`.
- Bathymétrie officielle : [Shom Litto3D PACA 2015](https://diffusion.shom.fr/donnees/litto3d-paca-2015.html), MNT 1 m, RGF93 / Lambert-93, référentiel vertical IGN69. Les quatre cellules finales sont les MNT `0924_6224`, `0924_6225`, `0925_6224` et `0925_6225` des archives Shom officielles [0920_6225.7z](https://services.data.shom.fr/INSPIRE/telechargement/prepackageGroup/LITTO3D_PACA_2015_PACK_DL/prepackage/0920_6225/file/0920_6225.7z) et [0925_6225.7z](https://services.data.shom.fr/INSPIRE/telechargement/prepackageGroup/LITTO3D_PACA_2015_PACK_DL/prepackage/0925_6225/file/0925_6225.7z).
- Empreintes d’archives contrôlées : `0920_6225.7z` SHA-256 `d3bd7beef4d8922c5be71f657cc1f7597099fb41584a84f6f171b8bb02176c81` ; `0925_6225.7z` SHA-256 `d4fc38163c7c3e0ce1b1d0aff7b62c0e7fd3f7f8de10c5dd34301a373505485d`.
- Orthophoto officielle : WMS IGN [data.geopf.fr/wms-r/wms](https://data.geopf.fr/wms-r/wms), couche `HR.ORTHOIMAGERY.ORTHOPHOTOS`, prise de vue vérifiée `2023-07-13Z` (`orthophoto_capture_date=2023-07-13`).

La profondeur Litto3D au pixel MNT voisin du point est environ `-28.87 m`, alors que la source indépendante indique 34 m. Cette différence est conservée comme incertitude de position/résolution/référence et justifie l’affichage reconnu `20–40 m`, sans présenter 34 m comme une mesure locale absolue.

## Emprise et couverture

- `focus_bbox_utm40s = context_bbox_utm40s = [924000, 6223600, 925200, 6224300]`, soit `1200 × 700 m`.
- Emprise interactive compacte : centre `[924600, 6223950]`, largeur `500 m`, profondeur `1000 m`, regard `90°`. Coins : `[924100,6224200]`, `[924100,6223700]`, `[925100,6223700]`, `[925100,6224200]`.
- Le point du site reste à environ 62 m de la limite ouest de l’emprise interactive.
- Contrôle de couverture locale autour du point de départ : `50 / 150 / 300 m = 100 / 90,5 / 77,0 %`, métriques de départ reproduites avant la sélection de l’emprise compacte.
- Contrôle cellulaire final sur le contexte MNT : `790977 / 840000 = 94,1639 %` de cellules finies ; `5,8361 %` NoData. Aucun remplissage artificiel n’a été ajouté.
- Contrôle cellulaire de l’empreinte interactive avant réduction : `497593 / 500000 = 99,5186 %` de cellules finies. Dans le paquet réduit `513 × 257`, `131184 / 131841 = 99,5017 %` de sommets valides ; `657` sommets restent invalides dans `valid-mask.bin` et `isobath-mask.bin`.
- Plage brute observée dans le contexte : `-42,04 m` à `+7,37 m`. Le rendu est borné à `max_depth_m=40` et `interactive_max_depth_m=40`; la partie plus profonde n’est pas extrapolée.

## Terrain et isobathes

- Paquet interactif reproductible : schéma v2, CRS `EPSG:2154`, texture `1001 × 501`, grille `513 × 257`, `262144` triangles, hauteur uint16 little-endian, masques bitset, vertical exaggeration `3.9935327405`.
- Méthode méditerranéenne appliquée : isobathes vectorielles dérivées du MNT, suréchantillonnées/lissées, pas de 5 m, niveaux requis `20/25/30/35 m`, palette bathymétrique v1.4 conservée.
- Statistiques vectorielles : 8 niveaux déclarés, 37 polylignes, 4116 points. Résidu de reprojection : moyenne `8,89e-7 m`, P95 `3,45e-8 m`, maximum `0,00148 m`, `withinTolerance=true`.
- Le NoData reste masqué dans la géométrie et les textures ; les complétions de bord profond sont distinguées par `isobath-mask.bin` et ne sont pas utilisées comme contours source.

## Calibration de la caméra initiale

Le mode de calibration dev/local existant a été activé uniquement dans un worktree temporaire, avec serveur local. Une rotation volontaire a été effectuée, puis la vue a été réinitialisée, enregistrée et exportée dans l’export groupé final. Les paramètres ont été contrôlés dans cet export, qui contient les valeurs sémantiques et la paire diagnostique exacte, sans téléchargement JSON par site.

Pose finale retenue et utilisée pour les vues statiques 3D :

```json
{
  "zoom": 1,
  "orbitAzimuthDeg": 0,
  "cameraElevationDeg": 30.96,
  "panRightM": 0,
  "panUpM": 0,
  "centerOffsetEastM": 0,
  "centerOffsetSouthM": 0,
  "cameraPositionM": [-2199.7557, 1325.1975, 0],
  "cameraTargetM": [2.4443, 4.0738, 0]
}
```

L’export local a utilisé le schéma `divetopo-camera-calibration-collection-v1` avec une entrée pour `plate-aux-merous`. Le mode a ensuite été désactivé : `camera-calibration status` indique `disabled` et `check-release` passe. Le panneau de calibration n’est présent dans aucun parcours normal ni dans les dérivés Web publiés.

## QA images et Web

- Deux plans 2D canoniques inspectés à leur résolution native `2474 × 1712` : topographique et orthophoto.
- Deux vues 3D statiques canoniques inspectées à leur résolution native `2474 × 1712`. Elles proviennent des captures dynamiques Web réalisées après validation de la pose finale.
- Deux planches HD inspectées à leur résolution native `5400 × 3250` : topographique et orthophoto. Le sous-titre géographique a été ajusté après inspection pour ne plus déborder à gauche.
- Aperçus Web des planches inspectés à `1800 × 1083`.
- Dérivés Web présents : plans 2D, captures 3D `960/1600/2474`, variantes mobiles `960`, deux JPEG pleine résolution de téléchargement, terrain interactif et deux textures.
- Vérification de cohérence capture/page : toutes les six comparaisons topographique/orthophoto desktop, pleine résolution et mobile passent ; corrélation desktop 2474 `0,9975–0,9976`, JPEG pleine résolution `0,9990`, mobile `0,9911–0,9912`, MAE maximale `0,0100`.

Parcours local inspecté sur le serveur de vérification isolé :

| Parcours | Viewport | Canvas 3D | Débordement horizontal | Erreurs | Calibration |
| --- | ---: | --- | --- | --- | --- |
| FR desktop | 1400 × 900 | oui | non | aucune | absente |
| FR mobile | 390 × 844 | oui | non | aucune | absente |
| EN desktop | 1400 × 900 | oui | non | aucune | absente |
| EN mobile | 390 × 844 | oui | non | aucune | absente |

## Tests et périmètre Git

- `python -m cartography.regions.var_ouest ... --check` : passe.
- Génération interactive reproductible dans un répertoire temporaire : les 7 fichiers du paquet (`terrain.json`, `height.bin`, deux masques, vecteurs et deux textures) correspondent octet pour octet aux sorties finales.
- Tests Python complets : `134` tests, tous OK. Tests ciblés configuration/interactive/vector/Var Ouest : `62` tests, tous OK.
- Tests Web ciblés de viewer/calibration/layout dans le worktree de vérification : `10` tests, tous OK.
- La suite Web SSR complète n’est pas déclarée verte dans la copie temporaire : 9 tests nécessitent `apps/web/dist/server/index.js`, absent de ce worktree, et l’assertion d’inventaire global rejette logiquement un site ajouté seulement à la route locale alors que `web.published=false`. Cette suite n’a donc pas été utilisée comme preuve de publication.
- `python3 tools/camera-calibration/manage.py check-release` : passe, calibration désactivée.
- Aucun `region.json`, manifeste régional/global, sitemap, composant Web partagé, release, push ou déploiement n’a été modifié. Les modifications temporaires du worktree de calibration n’ont pas été recopiées dans le dépôt.
