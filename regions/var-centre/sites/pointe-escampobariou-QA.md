# QA v1.5 — Pointe Escampobariou

Date du contrôle : 2026-08-15. Périmètre : le seul slug `pointe-escampobariou` dans `var-centre`.

## Reprise corrective NoData et tombants

- L’emprise est étendue vers le sud jusqu’à la limite Litto3D exploitable : focus `[952250, 6219000, 952950, 6219635]`, contexte `[952200, 6219000, 952999, 6219800]`, terrain interactif centré `[952635.6, 6219400]`, largeur `800 m`, profondeur `550 m`, regard `90°`.
- La tuile source `0952_6220-epsg2154.tif` est une grille 1000 × 1000 à 1 m, CRS EPSG:2154, origine `(951999.5, 6220000.5)`, NoData `-99999`, valeurs valides `-43.59 à +119.53 m`, validité globale `81,4622 %`.
- Dans le contexte choisi (799 × 800 cellules), 554 021 cellules sur 639 200 sont valides (`86,674124 %`) et 85 179 restent NoData. Dans l’emprise interactive brute (551 × 800), 412 272 cellules sur 440 800 sont valides (`93,528131 %`) et 28 528 restent NoData.
- Le bord sud officiel reste explicitement creux : dans les six bandes de 10 m au sud de l’emprise interactive, la couverture source mesurée est respectivement `5,209 %`, `21,234 %`, `51,180 %`, `65,408 %`, `74,646 %` et `82,940 %`. Aucun remplissage, prolongement de tombant ou interpolation artificielle n’a été ajouté. Les facettes invalides sont omises et les isobathes restent dérivées du MNT source.

## Identité et position

- La source officielle Var identifie le site comme **La pointe d’Escampobariou et ses tombants**, feature GeoJSON 28 : [fiche Sport-Nature Var](https://sportnature.var.fr/plongee/la-pointe-descampobariou-et-ses-tombants/) et [GeoJSON officiel des sites](https://sportnature.var.fr/api/fr/dives.geojson).
- Coordonnée officielle contrôlée : WGS84 `[6.0978, 43.0281667]`, soit environ `43° 01′ 41.4″ N · 6° 05′ 52.1″ E`. Transformation indépendante vers RGF93 / Lambert-93 EPSG:2154 : `[952635.5973, 6219271.8268]`, utilisée pour `site_location_utm40s` et le marqueur.
- La feature 29, **La pointe des Chevaliers à Escampobariou**, est distincte et n’a pas été substituée.
- Le titre court de production est `Pointe Escampobariou`; le contexte est `Hyères · Giens`. Le site reste explicitement `web.published=false`.
- Le libellé visible court est `Escampobariou` dans la configuration Web et le layout régional ; le slug, le titre officiel, les coordonnées et l’identité régionale restent inchangés.

## Sources, référentiels et licences

- Source bathymétrique et topographique : [Shom–IGN Litto3D PACA 2015](https://diffusion.shom.fr/donnees/altimetrie-littorale/litto3d-paca-2015.html), archive officielle [0950_6220.7z](https://services.data.shom.fr/INSPIRE/telechargement/prepackageGroup/LITTO3D_PACA_2015_PACK_DL/prepackage/0950_6220/file/0950_6220.7z), membre `0950_6220/LITTO3D_FRA_0952_6220_20150529_LAMB93_RGF93_IGN69/MNT1m/LITTO3D_FRA_0952_6220_MNT_20150529_LAMB93_RGF93_IGN69.asc`.
- Empreinte et contrôle du fichier brut : 1000 × 1000 cellules à 1 m, origine `(951999.5, 6220000.5)`, NoData `-99999`, plage valide `-43.59 à +119.53 m`, validité de la tuile `81.46 %`. SHA-256 de l’archive : `2e429c4bf290a97453661dc50dd996c5181a452399a2287b9d19f36d810a887b`.
- CRS planimétrique : RGF93 / Lambert-93, EPSG:2154. Référentiel vertical : IGN69. Litto3D est documenté comme donnée altimétrique, pas comme carte de navigation.
- Orthophoto : [WMS Géoplateforme IGN](https://data.geopf.fr/wms-r/wms), couche `HR.ORTHOIMAGERY.ORTHOPHOTOS`, capture `2023-07-13` vérifiée par GetFeatureInfo. Attribution et licence du projet : `© 2026 Matthieu Foll · CC BY-NC-SA 4.0`.

## Emprises, couverture et NoData

- Focus : `[952250, 6219000, 952950, 6219635]`, 700 × 635 m.
- Contexte : `[952200, 6219000, 952999, 6219800]`, 799 × 800 m.
- Terrain interactif : centre `[952635.6, 6219400]`, 800 × 550 m, regard 90°, visible 500 m, sans interpolation de relief.
- Le point officiel échantillonne environ `-5.6 m` dans le MNT. Profondeur brute maximale contrôlée : environ `-41.96 m` dans le focus et `-42.26 m` dans le contexte. L’affichage est plafonné à `40 m`, tandis que la fiche officielle annonce un tombant jusqu’à `35 m`.

Les statistiques de couverture sont calculées directement sur le MNT brut, sans compter les cellules NoData comme de la mer valide. Le contexte contient `554 021 / 639 200` cellules valides ; l’emprise interactive brute contient `412 272 / 440 800`. Les bandes sud montrent que l’extension atteint bien la limite de donnée et non une surface extrapolée.

Le rendu signale une discontinuité profonde au bord offshore ; aucune profondeur synthétique n’est ajoutée. Les cellules NoData officielles restent exclues de la surface et des facettes.

## Terrain interactif et calibration

- Paquet terrain : 7 fichiers site-local, CRS EPSG:2154, emprise source `[952360, 6219000, 952911, 6219800]`, 551 × 800 m, grille `353 × 513`, `360 448` triangles, plage encodée `-40 à +30 m`, exagération verticale ×2.
- La grille contient `169 159 / 181 089` sommets valides (`93,412079 %`) et `11 930` sommets exclus. `valid-mask.bin` et `isobath-mask.bin` sont identiques (`SHA-256 5fa30ae3…`) ; le moteur omet les facettes invalides.
- Isobathes vectorielles : niveaux 5, 10, 15, 20, 25, 30, 35, 40 m ; 30 polylignes et 3 559 points ; résidu de reprojection maximal `0,006383 m`, contrôle `withinTolerance=true`.
- Le mode dev local de calibration a été utilisé uniquement pour déplacer la caméra, inspecter ses paramètres et exporter une collection groupée. Provenance : schéma `divetopo-camera-calibration-collection-v1`, `exportedAt=2026-08-15T06:21:38.384Z`, SHA-256 `18269204b26988ad94ccb6decb60ff032d553492a74e3fa50a33ece70e5ae6ce`. Le JSON brut n’est pas copié dans Git.
- Pose finale enregistrée dans la configuration : zoom `0.861`, azimut `-88.07°`, élévation `22.52°`, pan droit `-62.1 m`, pan haut `49.81 m`, offsets centre `0/0`, position `[45.4934, 586.7364, 1556.6791]`, cible `[-1.2712, 10.8035, 168.5507]`. L’inspection après extension sud n’a montré aucun écart nécessaire.
- `tools/camera-calibration/manage.py status` confirme `disabled`; le contrôle release confirme que l’interface dev n’est pas exposée dans le build partagé.

## Sorties contrôlées

- 2 plans canoniques : `2474 × 1712 px`.
- 2 vues 3D statiques correspondant à la caméra finale : `2474 × 1712 px`.
- 2 planches : `5400 × 3250 px`.
- Inspection pleine résolution effectuée après régénération sur les 4 JPEG canoniques, les 2 planches, le raster régional et les textures terrain : cadres, orientation, échelle, libellés, attributions, licence, relief, bord NoData et cohérence orthophoto contrôlés. Les planches ont été recomposées avec les vues natives corrigées.
- Les dérivés Web pending ont été générés dans un overlay local temporaire afin de contrôler les captures réelles, puis supprimés avant le commit. Aucun actif pending ne reste sous `apps/web/public` et aucun manifeste terrain global n’a été modifié.
- Le premier accès navigateur à `http://127.0.0.1:3130` a échoué par timeout, le serveur Vinext écoutant sur `localhost`/IPv6. La relance unique avec `http://localhost:3130` a produit les captures topographique et orthophoto desktop/mobile, toutes inspectées visuellement.
- QA locale avec l’overlay temporaire : FR et EN, clair et sombre, desktop `1280 × 720` et mobile `390 × 844`, routes d’aperçu, canvas 3D, terrain, nord, échelle et attributions présents. `scrollWidth == clientWidth` dans les quatre tailles ; l’overlay a ensuite été restauré.
- Le contrôle clavier du dropdown reste une limite : le rendu n’expose pas de `<select>` natif (`locator` : `0`) et la touche `End` n’a pas changé l’option active. Les routes directes, les captures réelles et la mesure DOM/config servent de QA de repli ; aucune UI partagée n’a été modifiée.

## Carte régionale Var Centre

- Inspection pleine résolution du raster régional `regions/var-centre/outputs/var-centre-regional-relief.png` : `1864 × 1440 px`, RGB, `835021` octets, SHA-256 `1c07f7646681960aff423a2d50ac2f43afa6c29f0ef0f150ab4a0ae6aadb06fc`. L’emprise du manifeste reste `[6.0, 42.885, 6.46, 43.125]` (WGS84) ; le cadrage couvre la zone Var Centre sans artefact de bord observé.
- Après consolidation du Langoustier dans Jeaune Garde, les cinq repères de
  `plannedSites` restent dans la carte : `les-fourmigues`,
  `pointe-escampobariou`, `sec-de-la-jeaune-garde`, `cap-des-medes` et
  `la-gabiniere-port-cros`.
- Le layout régional pending est `side=left`, `shiftYRem=3.5`, `labelOffsetRem=-0.15`, `widthRem=5.8`, `connectorAngleDeg=0`, `connectorWidthRem=2.6`, avec `Escampobariou` conservé intact sur une ligne. Le cartouche utilise l’espace libéré au sud-ouest après la consolidation du Langoustier ; le point et le connecteur de Cap des Mèdes restent entièrement visibles.
- Mesure DOM de l’overlay local à `1280 × 720` : carte `[39,6797, 388,2344, 375,6797, 647,8047]`, point Escampobariou `[105,4453, 486,9141, 117,9219, 499,3906]`, cartouche `[40,5781, 529,5547, 136,0859, 566,3516]`, connecteur droit `M 0 0 L -16,1018 37,7783`. À `390 × 844` : carte `[12, 949,6406, 378, 1232,3828]`, point `[84,1406, 1057,6641, 96,6172, 1070,1406]`, cartouche `[19,2734, 1100,3047, 114,7813, 1137,1016]`, même connecteur droit. Aux deux largeurs, les cinq cartouches sont entièrement dans la carte et les mesures donnent zéro collision cartouche-cartouche, cartouche-point, cartouche-échelle et cartouche-nord, sans débordement horizontal. Le pending reste non cliquable et en préparation.

## Tests et périmètre Git

- Configuration : `/Users/follm/home-projects/divetopo/.venv/bin/python -m cartography.regions.var_centre regions/var-centre/sites/pointe-escampobariou.json --check` réussi.
- Rendu et génération du terrain exécutés avec les scripts v1.5 existants ; validations CRS, dimensions, NoData, masque source, exclusion des sommets invalides et tolérance vectorielle réussies. Le cache raster intermédiaire corrigé est ignoré et aucun cache n’est staged.
- Calibration : `/Users/follm/home-projects/divetopo/.venv/bin/python tools/camera-calibration/manage.py check-release` réussi.
- Le paquet et le layout restent limités au Var Centre : configuration et QA du site pending, plus son entrée dans le manifeste régional. `sites` reste limité aux quatre sites publiés et `plannedSites` contient cinq entrées ; aucun actif de site ou terrain, raster régional, manifeste terrain global, sitemap, composant, route ou autre région n’a été modifié. `web.published=false` reste inchangé. L’overlay de calibration et l’aperçu pending ont été retirés avant le contrôle Git. Aucun release, push ou déploiement n’est autorisé par ce paquet.

Défauts et incertitudes résiduels : la donnée Litto3D est altimétrique et non navigable ; la profondeur affichée est plafonnée à 40 m malgré un maximum brut local proche de 42 m ; les cellules NoData du bord offshore restent explicitement exclues. Les dérivés Web n’ont pas été resynchronisés dans cette reprise. La fiche officielle décrit le site et son tombant, mais ce contrôle ne constitue pas une validation de sécurité, d’accès ou de mouillage.
