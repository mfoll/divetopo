# QA v1.5 — Pointe Escampobariou

Date du contrôle : 2026-08-14. Périmètre : le seul slug `pointe-escampobariou` dans `var-centre`.

## Identité et position

- La source officielle Var identifie le site comme **La pointe d’Escampobariou et ses tombants**, feature GeoJSON 28 : [fiche Sport-Nature Var](https://sportnature.var.fr/plongee/la-pointe-descampobariou-et-ses-tombants/) et [GeoJSON officiel des sites](https://sportnature.var.fr/api/fr/dives.geojson).
- Coordonnée officielle contrôlée : WGS84 `[6.0978, 43.0281667]`, soit environ `43° 01′ 41.4″ N · 6° 05′ 52.1″ E`. Transformation indépendante vers RGF93 / Lambert-93 EPSG:2154 : `[952635.5973, 6219271.8268]`, utilisée pour `site_location_utm40s` et le marqueur.
- La feature 29, **La pointe des Chevaliers à Escampobariou**, est distincte et n’a pas été substituée.
- Le titre court de production est `Pointe Escampobariou`; le contexte est `Hyères · Giens`. Le site reste explicitement `web.published=false`.

## Sources, référentiels et licences

- Source bathymétrique et topographique : [Shom–IGN Litto3D PACA 2015](https://diffusion.shom.fr/donnees/altimetrie-littorale/litto3d-paca-2015.html), archive officielle [0950_6220.7z](https://services.data.shom.fr/INSPIRE/telechargement/prepackageGroup/LITTO3D_PACA_2015_PACK_DL/prepackage/0950_6220/file/0950_6220.7z), membre `0950_6220/LITTO3D_FRA_0952_6220_20150529_LAMB93_RGF93_IGN69/MNT1m/LITTO3D_FRA_0952_6220_MNT_20150529_LAMB93_RGF93_IGN69.asc`.
- Empreinte et contrôle du fichier brut : 1000 × 1000 cellules à 1 m, origine `(951999.5, 6220000.5)`, NoData `-99999`, plage valide `-43.59 à +119.53 m`, validité de la tuile `81.46 %`. SHA-256 de l’archive : `2e429c4bf290a97453661dc50dd996c5181a452399a2287b9d19f36d810a887b`.
- CRS planimétrique : RGF93 / Lambert-93, EPSG:2154. Référentiel vertical : IGN69. Litto3D est documenté comme donnée altimétrique, pas comme carte de navigation.
- Orthophoto : [WMS Géoplateforme IGN](https://data.geopf.fr/wms-r/wms), couche `HR.ORTHOIMAGERY.ORTHOPHOTOS`, capture `2023-07-13` vérifiée par GetFeatureInfo. Attribution et licence du projet : `© 2026 Matthieu Foll · CC BY-NC-SA 4.0`.

## Emprises, couverture et NoData

- Focus : `[952250, 6219150, 952950, 6219635]`, 700 × 485 m.
- Contexte : `[952200, 6219100, 952999, 6219800]`, 799 × 700 m.
- Terrain interactif : centre `[952635.6, 6219475]`, 650 × 550 m, regard 90°, visible 500 m, sans cadrage serré inutile.
- Le point officiel échantillonne environ `-5.6 m` dans le MNT. Profondeur brute maximale contrôlée : environ `-41.96 m` dans le focus et `-42.26 m` dans le contexte. L’affichage est plafonné à `40 m`, tandis que la fiche officielle annonce un tombant jusqu’à `35 m`.

Couverture calculée dans des fenêtres carrées centrées sur le point officiel ; le dénominateur est exclusivement constitué des cellules marines valides (`z < 0`), et non de la terre :

| Fenêtre | Cellules totales | Cellules marines | Marines valides | Couverture marine | Part marine du carré |
|---|---:|---:|---:|---:|---:|
| 50 m | 2 601 | 2 327 | 2 327 | 100 % | 89,47 % |
| 150 m | 22 801 | 9 619 | 9 619 | 100 % | 42,19 % |
| 300 m | 90 601 | 45 194 | 45 194 | 100 % | 49,88 % |

Dans les emprises larges, la validité brute est d’environ 93,0 % dans le focus et 91,9 % dans le contexte ; les cellules NoData restantes sont conservées comme telles. Les fenêtres 50/150/300 m ne contiennent pas de NoData marin. Le masque d’élévation WMS terrestre a été limité aux valeurs `> 0.01 m` pour éviter de traiter le remplissage marin à zéro comme du relief.

Le rendu signale une discontinuité profonde au bord offshore : environ 7,0 % du cadre 2D et 3,2 % du crop 3D ne sont ni bathymétrie ni élévation ; les facettes invalides sont omises et aucune profondeur synthétique n’est ajoutée. Les isobathes restent dérivées du MNT source.

## Terrain interactif et calibration

- Paquet terrain : 7 fichiers site-local, CRS EPSG:2154, emprise source `[952360, 6219150, 952911, 6219800]`, 551 × 650 m, grille 435 × 513, 444 416 triangles, plage encodée `-40 à +30 m`, exagération verticale ×2.
- Isobathes vectorielles méditerranéennes : niveaux 5, 10, 15, 20, 25, 30, 35, 40 m ; 59 polylignes et 4 945 points ; résidu de reprojection moyen `1.32e-05 m`, p95 `6.54e-07 m`, maximum `0.00878 m`, contrôle `withinTolerance=true`.
- Le mode dev local de calibration a été activé uniquement dans une copie temporaire de l’application. La caméra a été déplacée, les paramètres inspectés et un export groupé unique a été produit (`divetopo-camera-calibrations.json`, SHA-256 `1090191aeb9bb738ce60f304828b5cafa2f6d6c711835710a9ae1abe35432cf5`). Aucun JSON de calibration n’est livré par site.
- Pose finale enregistrée dans la configuration : zoom `0.84`, azimut `0°`, élévation `18°`, pan droit `59.49 m`, pan haut `-0.11 m`, position `[1363.1263, 469.039, 84.4923]`, cible `[-66.8737, 4.4038, 84.4923]`. Les 3D statiques et planches ont été régénérées après validation de cette pose.
- `tools/camera-calibration/manage.py status` confirme `disabled`; le contrôle release confirme que l’interface dev n’est pas exposée dans le build partagé.

## Sorties contrôlées

- 2 plans canoniques : `2474 × 1712 px`.
- 2 vues 3D statiques correspondant à la caméra finale : `2474 × 1712 px`.
- 2 planches : `5400 × 3250 px`.
- Le SHA autonome `40c100f18bb501f2b17734956696be98d59288a1` contenait 14 dérivés Web sous `apps/web/public/maps/var-centre/pointe-escampobariou/maps/`. Ils sont volontairement exclus de cette intégration car le site reste `web.published=false` ; aucun de ces actifs n’est présent dans le worktree régional intégré.
- Inspection pleine résolution effectuée sur les 4 JPEG canoniques et les 2 planches : cadres, orientation, échelle, libellés, attributions, licence, relief et NoData contrôlés.
- Inspection des 4 captures terrain finales : topographique et orthophoto en desktop `2474 × 1712` et mobile `960 × 662`; cadrage cohérent avec la pose finale, terrain marin lisible, fort et côte plausibles dans l’orthophoto, pas de débordement visible.
- QA locale de page avec copie temporaire non versionnée du manifeste : routes FR et EN en desktop `1280 × 900` et mobile `390 × 844`, HTTP 200, canvas 3D rendu, `scrollWidth == innerWidth` dans les quatre cas. La carte régionale de navigation n’a pas été modifiée et ne publie pas ce site.

## Tests et périmètre Git

- Configuration : `python -m cartography.regions.var_centre regions/var-centre/sites/pointe-escampobariou.json --check` réussi.
- Rendu et génération du terrain exécutés avec les scripts v1.5 existants ; validations CRS, dimensions, NoData, masque source et tolérance vectorielle réussies.
- Calibration : `python3 tools/camera-calibration/manage.py check-release` réussi.
- Intégration limitée aux fichiers site-local sous `regions/var-centre/` : configuration, QA, sorties JPEG canoniques et paquet terrain interactif. Aucun `region.json`, manifeste régional/global, manifeste terrain publié, sitemap, composant, route ou actif Web partagé n’a été modifié. Aucun release, push ou déploiement n’est autorisé par ce paquet.

Défauts et incertitudes résiduels : la donnée Litto3D est altimétrique et non navigable ; la profondeur affichée est plafonnée à 40 m malgré un maximum brut local proche de 42 m ; les cellules NoData du bord offshore restent explicitement exclues. La fiche officielle décrit le site et son tombant, mais ce contrôle ne constitue pas une validation de sécurité, d’accès ou de mouillage.
