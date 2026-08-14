# Pierre du Jas — QA v1.5

Status : **paquet site-local défendable ; publication régionale volontairement désactivée** (`web.published=false`). Le périmètre ne contient que Pierre du Jas et ses sorties.

## Identité et provenance

- Site : Pierre du Jas, Six-Fours-les-Plages · Le Brusc.
- Coordonnée primaire normalisée depuis la table officielle DREAL Natura : `43°04.879′ N, 5°45.109′ E`, soit `43.0813166667, 5.7518166667` ; position RGF93 / Lambert-93 EPSG:2154 `[924225.776, 6224132.648]`.
- Le dossier officiel DREAL décrit le relief du secteur comme une arête culminant vers −28 m, sur un fond sableux à −34 / −36 m. Les fiches locales de plongée servent uniquement de contrôle d’identité et de profondeur : sommet autour de 26–38 m, base autour de 40 m.
- Sources d’identité : [diagnostic écologique officiel DREAL](https://www.paca.developpement-durable.gouv.fr/IMG/pdf/f09317p0217_diag_eco.pdf), [Le Brusc Plongée](https://le-brusc-plongee.com/nos-sites-de-plongees/) et [GPES](https://www.gpes.fr/?page_id=530&lang=en).
- Bathymétrie et topographie : [Shom–IGN Litto3D PACA 2015](https://diffusion.shom.fr/donnees/litto3d-paca-2015.html), MNT à 1 m, RGF93 / Lambert-93 EPSG:2154, référentiel vertical IGN69.
- Archives officielles utilisées : `0920_6225.7z` SHA-256 `d3bd7beef4d8922c5be71f657cc1f7597099fb41584a84f6f171b8bb02176c81` et `0925_6225.7z` SHA-256 `d4fc38163c7c3e0ce1b1d0aff7b62c0e7fd3f7f8de10c5dd34301a373505485d`. Les cinq membres MNT1m sont déclarés dans la configuration ; les archives brutes restent hors Git.
- Orthophoto : flux IGN BD ORTHO `HR.ORTHOIMAGERY.ORTHOPHOTOS`, extraction alignée EPSG:2154 à 1 m ; le `GetFeatureInfo` du point retourne la date de prise de vue `2023-07-13`. Le WKT de travail a été canonisé avant validation, sans modification de pixels.

## Couverture et contrat terrain

- Contrôle de référence autour du point : couverture marine Litto3D `50 / 150 / 300 m = 100 / 74,1 / 62,5 %`. Le recalcul sur l’union brute disponible donne `100,0 / 73,7 / 62,3 %`, écart de méthode et d’arrondi seulement.
- Emprise focus finale : `[924100, 6223980, 925300, 6224280]`, soit `1200 × 300 m`. Le MNT d’élévation brut contient `94,108 %` de pixels source valides ; le masque profondeur marine positive contient `93,571 %` de cellules valides. Plage brute : `−41,06 à +7,37 m`.
- Emprise contexte : `[923900, 6223700, 925500, 6224500]`, `1600 × 800 m`, `83,164 %` de pixels source valides. Le bord offshore NoData du focus, `5,9 %` dans le plan, est conservé visuellement à la couleur de profondeur maximale et exclu des isobathes et du maillage ; le crop 3D exclut `3,2 %` de facettes invalides.
- `deep_edge_nodata_terrain_fill` reste désactivé. Aucun remplissage de profondeur, interpolation d’isobathe ou surface artificielle n’est utilisé.
- Terrain interactif : grille `513 × 129`, `131072` triangles, élévation encodée `−40,0000 à +0,0059 m`, masque valide `62272 / 66177 = 94,099 %`. Les isobathes vectorielles couvrent 8 niveaux, 14 polylignes et 1531 points ; résidu de reprojection maximal `0,001944 m`, dans la tolérance.
- Vue initiale déclarée et partagée entre statique/interactif : azimut de regard `90°`, largeur visible `260 m`, footprint `300 × 1200 m`, exagération verticale `3,9935327405`, sans décalage de pan. La pose locale réinitialisée et validée est `orbit_azimuth_deg=0`, `camera_elevation_deg=25,64°`, `zoom=1`, sans pan ; la paire diagnostique est conservée dans la configuration.

## Livrables

- Quatre cartes canoniques en `2474 × 1712 px` : plans 2D topographique et orthophoto, vues 3D statiques topographique et orthophoto.
- Deux planches en `5400 × 3250 px` : topographique et orthophoto.
- Paquet terrain canonique de sept fichiers : `terrain.json`, `height.bin`, `valid-mask.bin`, `isobath-mask.bin`, `isobaths-vector.json`, `topographic.webp`, `orthophoto.webp`.
- Copie Web bit-à-bit du paquet terrain sous `apps/web/public/terrain/pierre-du-jas/`.
- Quatorze dérivés Web site-scoped sous `apps/web/public/maps/var-ouest/pierre-du-jas/maps/` : deux plans JPEG, deux aperçus de planche à 1800 px, six variantes desktop 3D à 960/1600/2474 px, deux variantes mobile 960 px et deux JPEG HD de téléchargement.
- Les variantes Web 3D ont été dérivées des vues statiques canoniques correspondant à la vue initiale ; elles ne constituent pas une capture WebGL indépendante. Cette limite de production est conservée explicitement plutôt que masquée ; la session WebGL locale de contrôle a néanmoins été exécutée avec les dépendances déjà présentes dans le dépôt voisin.

## QA visuelle et calibration locale

- Inspection pleine résolution réalisée pour les quatre cartes, les deux planches, les deux textures interactives, les variantes Web desktop/mobile et les téléchargements HD : contours continus, labels −5/−10/−15/−25/−30/−35 m lisibles selon la vue, compas, échelle et crédits présents, aucune complétion de NoData visible ni artefact de couture.
- Après validation de la pose initiale réinitialisée, les quatre JPEG statiques canoniques sont restés bit-identiques par SHA-256 ; le renderer Python complet n’a pas pu être relancé dans ce worktree faute de Pillow. Les planches et dérivés Web ont été régénérés à partir de ces mêmes vues, sans masquer cette limite.
- Le plan 2D orthophoto reste très majoritairement bathymétrique : l’orthophoto n’est appliquée qu’au domaine terrestre/shallow documenté, jamais inventée sous l’eau. La différence orthophoto/topographique est visible sur les rochers terrestres dans les vues 3D et les textures interactives.
- Le mode local de calibration existant est conservé hors bundle publié : activation par `?camera-calibration` uniquement sur `localhost`, déplacement via `OrbitControls`, stockage d’une pose par slug et export d’une collection JSON unique `divetopo-camera-calibrations.json` contenant les paramètres sémantiques et la pose diagnostique. La session locale Pierre du Jas a validé déplacement, enregistrement, visibilité des paramètres dans le JSON groupé et export ; `npm run camera-calibration:check-release` et le gestionnaire retournent `disabled` après la vérification.
- La route régionale FR/EN n’a pas été substituée par une route publiée, puisque le site reste explicitement hors manifeste. La route de vérification locale temporaire a été testée en français sur desktop et mobile avec le paquet site-scoped, puis retirée avant staging. La variante EN et la validation du site régional publié restent hors périmètre tant que `web.published=false`.

## Vérifications reproductibles

- `cartography.config.validate_config` : pass pour `regions/var-ouest/sites/pierre-du-jas.json`.
- Contrôles GDAL read-only des rasters : EPSG:2154, résolution 1 m, emprises exactes, NoData et plages de profondeur vérifiés ; orthophotos RGB vérifiées.
- Validation structurelle du paquet interactif : pass ; tailles de grille, masques, encodage binaire, textures et payload vectoriel vérifiés.
- `/opt/homebrew/bin/python3 -m unittest tests.test_config tests.test_vector_isobaths tests.test_var_est_region tests.test_regional_manifest` : `44/44` pass.
- `tests.test_interactive` n’a pas pu être importé dans l’environnement Python courant (`Pillow` absent) ; build/lint/tests Web du worktree non exécutés. La QA navigateur locale a utilisé les dépendances déjà présentes dans le dépôt voisin, sans installation ni modification de ce dépôt. Aucun package n’a été installé.
- Pierre du Jas reste la seule entrée pending de l’inventaire régional et du manifeste de planification (`sites=4`, `plannedSites=5`) ; `web.published=false` est conservé. Plate aux Mérous est archivé sous `regions/var-ouest/`, regroupé dans l’emprise Les Magnons et absent de toute surface visible. Aucun manifeste terrain publié, sitemap, route, composant Web partagé, autre site, autre région, release, push ou déploiement n’a été modifié.
