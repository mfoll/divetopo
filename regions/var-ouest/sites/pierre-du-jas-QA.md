# Pierre du Jas — QA v1.5

Statut : **paquet site-local pending, régénéré et QA-able ; publication Web volontairement désactivée** (`web.published=false`). Ce commit ne synchronise aucun actif pending vers `apps/web/public`, les manifestes terrain publiés, les routes ou le sitemap.

## Identité et décision de séparation

- Site : Pierre du Jas, Six-Fours-les-Plages · Le Brusc.
- Coordonnée primaire normalisée depuis la table officielle DREAL Natura : `43°04.879′ N, 5°45.109′ E`, soit `43.0813166667, 5.7518166667` ; position RGF93 / Lambert-93 EPSG:2154 `[924225.776, 6224132.648]`.
- Le dossier officiel DREAL décrit l’arête culminant vers `−28 m`, sur un fond sableux à `−34 / −36 m`. Le Brusc Plongée décrit Pierre du Jas comme une petite roche distincte autour de `26–38 m`, alors que Les Magnons sont des sites de `3–20 m`.
- Contrôle direct des terrains au point DREAL : Pierre du Jas `z=-34,075 m`, voisinage 100 m `−40,000..−25,765 m` (relief `14,235 m`) ; Les Magnons, capés par `max_depth=30`, `−30,000..−25,758 m` (relief `4,242 m`). Le recouvrement géométrique ne couvre donc pas utilement le relief profond de Pierre du Jas : l’identité reste distincte.
- Plate aux Mérous reste archivé sous `regions/var-ouest/`, regroupé dans l’emprise de Les Magnons et absent de l’inventaire/planning visible. Le nom affiché de Les Magnons est conservé.
- Sources d’identité : [diagnostic écologique officiel DREAL](https://www.paca.developpement-durable.gouv.fr/IMG/pdf/f09317p0217_diag_eco.pdf), [Le Brusc Plongée](https://le-brusc-plongee.com/nos-sites-de-plongees/) et [GPES](https://www.gpes.fr/?page_id=530&lang=en).

## Sources et couverture terrain

- Bathymétrie et topographie : [Shom–IGN Litto3D PACA 2015](https://diffusion.shom.fr/donnees/litto3d-paca-2015.html), MNT à 1 m, RGF93 / Lambert-93 EPSG:2154, référentiel vertical IGN69.
- Archives officielles utilisées : `0920_6225.7z` SHA-256 `d3bd7beef4d8922c5be71f657cc1f7597099fb41584a84f6f171b8bb02176c81` et `0925_6225.7z` SHA-256 `d4fc38163c7c3e0ce1b1d0aff7b62c0e7fd3f7f8de10c5dd34301a373505485d`. Les cinq membres MNT1m sont déclarés dans la configuration ; les archives brutes restent hors Git.
- Orthophoto : flux IGN BD ORTHO `HR.ORTHOIMAGERY.ORTHOPHOTOS`, extraction alignée EPSG:2154 à 1 m ; le `GetFeatureInfo` du point retourne la date de prise de vue `2023-07-13`. Le WKT de travail a été canonisé avant validation, sans modification de pixels.
- Couverture de référence autour du point : Litto3D marine `50 / 150 / 300 m = 100 / 74,1 / 62,5 %` ; le recalcul sur l’union brute disponible donne `100,0 / 73,7 / 62,3 %`, écart de méthode et d’arrondi seulement.
- Focus final élargi au sud selon la couverture des tuiles déclarées : `[924100, 6223300, 925300, 6224280]`, soit `1200 × 980 m`. Le MNT brut et le masque de profondeur positive contiennent `98,105 %` de cellules source valides ; plage brute `−41,06 à +7,37 m`.
- Contexte final : `[923900, 6223000, 925500, 6224500]`, soit `1600 × 1500 m`, `79,592 %` de cellules source valides ; plage brute `−42,04 à +33,21 m`. La limite sud suit la couverture des cinq membres déclarés, sans ajout des cellules 6223 non déclarées.
- Le rendu signale `1,9 %` de bord offshore sans bathymétrie ni élévation ; cette zone reste à la couleur de profondeur maximale mais est exclue des contours et du terrain. `deep_edge_nodata_terrain_fill` reste désactivé : aucun remplissage de profondeur, interpolation d’isobathe ou surface artificielle n’est utilisé.

## Calibration locale et terrain interactif

- Pose initiale calibrée conservée dans la configuration : `zoom=0,65`, `orbit_azimuth_deg=-32,8°`, `camera_elevation_deg=17,56°`, `pan_right_m=-9,57`, `pan_up_m=39,59`, `center_offset_east_m=0`, `center_offset_south_m=0`.
- Diagnostic associé : position caméra `[-2054.5109, 850.1384, -1482.8054]`, cible `[292.2841, -33.5874, 29.4704]`.
- Provenance de calibration : collection `divetopo-camera-calibration-collection-v1`, `exportedAt=2026-08-15T06:21:38.384Z`, SHA-256 `18269204b26988ad94ccb6decb60ff032d553492a74e3fa50a33ece70e5ae6ce`. Le JSON brut reste hors Git.
- Le mode local de calibration existant reste dev/local uniquement ; cette QA consigne la pose groupée sans ajouter de téléchargement JSON par site ni exposer de route publiée.
- Paquet terrain : emprise physique `1200 × 980 m`, grille `513 × 419`, `428032` triangles, élévation encodée `−40,0000..+0,0108 m`, masque valide `210864 / 214947 = 98,100 %`.
- Isobathes vectorielles : 8 niveaux, 69 polylignes et 8400 points ; résidu de reprojection maximal `0,007692 m`, `withinTolerance=true`. Les fichiers `terrain.json`, `height.bin`, `valid-mask.bin`, `isobath-mask.bin`, `isobaths-vector.json`, `topographic.webp` et `orthophoto.webp` sont cohérents avec la nouvelle emprise.

## Livrables régionaux pending

- Quatre cartes canoniques en `2474 × 1712 px` : plans 2D topographique et orthophoto, vues 3D statiques topographique et orthophoto.
- Deux planches en `5400 × 3250 px` : topographique et orthophoto.
- Les sorties statiques, 3D, planches et le paquet terrain ont été régénérés à partir de la configuration et des rasters validés. Seuls les fichiers site-scoped sous `regions/var-ouest/` sont concernés.
- Aucun dérivé Web pending n’a été généré ou copié sous `apps/web/public`. Le manifeste terrain régional publié reste limité aux quatre sites publiés ; le manifeste Web de planification reste à `sites=4`, `plannedSites=5`, avec Pierre du Jas en préparation et `web.published=false`.

## QA visuelle et contrôles

- Inspection pleine résolution des quatre cartes, des deux planches et des deux textures interactives : relief de l’arête et des fonds profonds visibles après l’extension sud, courbes `−5/−10/−15/−20/−25/−30/−35/−40 m` cohérentes avec le terrain, nord/compas, échelle, sources et licences présents ; pas de couture ni de débordement détecté. Les zones de bord NoData sont les zones documentées et masquées par les fichiers de validité.
- Les vues 3D montrent la continuité du relief vers le sud ; les variantes orthophoto appliquent l’orthophoto uniquement au domaine terrestre/shallow documenté. Les textures topographique et orthophoto conservent le même alignement.
- La carte régionale et ses surfaces partagées n’ont pas été modifiées ; le regroupement Les Magnons/La Merveilleuse reste inchangé et Plate n’est pas réintroduit comme doublon.
- Contrôles exécutés : `python -m cartography.regions.var_ouest ... --check` (pass), rendu régional `--render-only` (pass, avertissement NoData documenté), génération terrain interactive site-only en répertoire temporaire puis copie des sept fichiers Pierre (pass), `python -m cartography.plate ... --land-style both` (pass), contrôles GDAL des dimensions, CRS, résolutions, validité et plages (pass).
- Les tests Web partagés, le build/lint Web et les routes desktop/mobile FR/EN ne sont pas relancés pour ce paquet pending : aucune surface Web ne doit l’exposer avant autorisation globale. Aucun test partagé, manifeste global, route, sitemap, autre région, release, push ou déploiement n’a été modifié.
