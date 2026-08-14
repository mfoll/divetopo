# QA v1.5 — Pointe Escampobariou

Date du contrôle : 2026-08-14. Périmètre : le seul slug `pointe-escampobariou` dans `var-centre`.

## Reprise corrective NoData et tombants

- Audit pleine résolution effectué sur le raster Litto3D brut, le masque officiel `Masque_Source`, les caches d’altimétrie, le masque de validité et les triangles du terrain. Dans l’emprise interactive de 551 × 650 = 358 150 cellules, les 5 639 cellules NoData (1,57448 %) forment un seul secteur au bord sud-ouest (lignes locales 523–649, colonnes 0–58). Le masque Shom `Masque_Source=0` s’aligne exactement sur ces 5 639 cellules : le manque est donc source, pas créé par le cadrage, le rééchantillonnage ou les triangles.
- Avant correction, 234 cellules valides du raster bathymétrique étaient perdues au voisinage de trous NoData de l’altimétrie WMS terrestre, produisant des ruptures valides jusqu’à 40 m ; 190 cellules supplémentaires étaient atteintes par le lissage du masque côtier. Correction limitée : 444 cellules d’altimétrie WMS NoData ont été reprises uniquement lorsque le MNT Litto3D brut, valide et non négatif, fournissait une valeur source (0 à 22,73 m). Aucun remplissage marin, interpolation de relief ou prolongement du secteur NoData n’a été ajouté.
- Après correction, aucune cellule Litto3D valide n’est perdue dans la surface interactive ; le maximum des différences aux frontières terre/mer est 2,041 m et aucune ne dépasse 10 m. Les tombants encore très raides sont donc des formes du MNT source, visuellement renforcées par l’exagération verticale ×2, et non les ruptures artificielles de 40 m supprimées ici.
- La surface interactive corrigée est valide à 352 511 / 358 150 = 98,42552 % ; les 5 639 cellules source NoData restent invalides. Le terrain contient 219 640 / 223 155 sommets valides = 98,42486 %, avec 3 515 sommets exclus. `valid-mask.bin` et `isobath-mask.bin` sont identiques ; le moteur omet les facettes invalides et les isobathes restent source-dérivées. Le secteur NoData du bord marin n’est pas comblé.

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

Dans les emprises larges, les cellules NoData restantes sont conservées comme telles. Les fenêtres 50/150/300 m ne contiennent pas de NoData marin. Le correctif terrestre ci-dessus ne s’applique qu’aux pixels où le MNT Litto3D source apporte effectivement une altitude ; le NoData marin et le bord source restent exclus.

Le rendu signale une discontinuité profonde au bord offshore : environ 7,0 % du cadre 2D et 3,1 % du crop 3D ne sont ni bathymétrie ni élévation ; les facettes invalides sont omises et aucune profondeur synthétique n’est ajoutée. Les isobathes restent dérivées du MNT source.

## Terrain interactif et calibration

- Paquet terrain : 7 fichiers site-local, CRS EPSG:2154, emprise source `[952360, 6219150, 952911, 6219800]`, 551 × 650 m, grille 435 × 513, 444 416 triangles, plage encodée `-40 à +30 m`, exagération verticale ×2.
- Isobathes vectorielles méditerranéennes : niveaux 5, 10, 15, 20, 25, 30, 35, 40 m ; 53 polylignes et 5 204 points ; résidu de reprojection moyen `5.21e-06 m`, p95 `2.31e-07 m`, maximum `0.00242 m`, contrôle `withinTolerance=true`.
- Le mode dev local de calibration a été activé uniquement dans une copie temporaire de l’application. La caméra a été déplacée, les paramètres inspectés et un export groupé unique a été produit (`divetopo-camera-calibrations.json`, SHA-256 `1090191aeb9bb738ce60f304828b5cafa2f6d6c711835710a9ae1abe35432cf5`). Aucun JSON de calibration n’est livré par site.
- Pose finale enregistrée dans la configuration : zoom `0.84`, azimut `0°`, élévation `18°`, pan droit `59.49 m`, pan haut `-0.11 m`, position `[1363.1263, 469.039, 84.4923]`, cible `[-66.8737, 4.4038, 84.4923]`. Les 3D statiques et planches ont été régénérées après validation de cette pose.
- `tools/camera-calibration/manage.py status` confirme `disabled`; le contrôle release confirme que l’interface dev n’est pas exposée dans le build partagé.

## Sorties contrôlées

- 2 plans canoniques : `2474 × 1712 px`.
- 2 vues 3D statiques correspondant à la caméra finale : `2474 × 1712 px`.
- 2 planches : `5400 × 3250 px`.
- Le SHA autonome initial `40c100f18bb501f2b17734956696be98d59288a1` contenait 14 dérivés Web sous `apps/web/public/maps/var-centre/pointe-escampobariou/maps/`. Ils restent volontairement exclus de cette reprise corrective ; le site demeure `web.published=false` et aucun actif Web n’est intégré.
- Dérivés Web : exactement 14 fichiers déjà présents sous `apps/web/public/maps/var-centre/pointe-escampobariou/maps/`. Ils n’ont volontairement pas été régénérés ni modifiés dans cette reprise corrective ; aucune surface Web partagée n’est incluse dans le commit.
- Inspection pleine résolution effectuée après régénération sur les 4 JPEG canoniques, les 2 planches et les 2 textures WebP du terrain : cadres, orientation, échelle, libellés, attributions, licence, relief, bord NoData et cohérence orthophoto contrôlés. Les planches ont été recomposées avec les vues natives corrigées dans le périmètre site-local autorisé.
- La QA de page FR/EN précédente en copie locale reste documentée : desktop `1280 × 900` et mobile `390 × 844`, HTTP 200, canvas rendu, `scrollWidth == innerWidth`. Elle ne vaut pas resynchronisation des dérivés Web, qui étaient explicitement hors périmètre de cette reprise.
- QA locale de page avec copie temporaire non versionnée du manifeste : routes FR et EN en desktop `1280 × 900` et mobile `390 × 844`, HTTP 200, canvas 3D rendu, `scrollWidth == innerWidth` dans les quatre cas. La carte régionale de navigation conserve ce site en préparation et ne le rend pas cliquable ni publié.

## Carte régionale Var Centre

- Inspection pleine résolution du raster régional `regions/var-centre/outputs/var-centre-regional-relief.png` : `1864 × 1440 px`, RGB, `835021` octets, SHA-256 `1c07f7646681960aff423a2d50ac2f43afa6c29f0ef0f150ab4a0ae6aadb06fc`. L’emprise du manifeste reste `[6.0, 42.885, 6.46, 43.125]` (WGS84) ; le cadrage couvre la zone Var Centre sans artefact de bord observé.
- Les six repères de `plannedSites` restent dans la carte et cohérents avec l’emprise : `les-fourmigues` `(15.05659, 35.44169)`, `pointe-escampobariou` `(21.26087, 40.34721)`, `sec-du-langoustier` `(33.69826, 52.19542)`, `sec-de-la-jeaune-garde` `(34.27510, 51.01017)`, `cap-des-medes` `(52.48926, 40.29875)`, `la-gabiniere-port-cros` `(85.45102, 56.80000)` en `(xPercent, yPercent)`.
- Le layout régional pending est maintenant `side=right`, `shiftYRem=-3.5`, `labelOffsetRem=7.5`, `widthRem=8.7`, `connectorAngleDeg=-19`, `connectorWidthRem=3.2`. Simulation avec les rectangles DOM mesurés du rendu publié : à `1280 × 720`, cartouche `[209.12, 417.36, 348.32, 454.16]` dans la carte `[39.68, 388.23, 375.68, 647.80]`, marge minimale `27.36 px`; à `390 × 844`, cartouche `[187.81, 988.12, 327.01, 1024.92]` dans la carte `[12, 949.64, 378, 1232.38]`, marge minimale `38.48 px`. Les deux routes choisies par le routeur évitent les cinq cartouches publiés et touchent le bord du cartouche à `1.5 px` de recouvrement contrôlé. Le pending reste non cliquable et rendu comme repère de préparation par l’UI actuelle ; aucune UI partagée n’a été modifiée.

## Tests et périmètre Git

- Configuration : `python -m cartography.regions.var_centre regions/var-centre/sites/pointe-escampobariou.json --check` réussi.
- Rendu et génération du terrain exécutés avec les scripts v1.5 existants ; validations CRS, dimensions, NoData, masque source, exclusion des sommets invalides et tolérance vectorielle réussies. Le cache raster intermédiaire corrigé est ignoré et aucun cache n’est staged.
- Calibration : `python3 tools/camera-calibration/manage.py check-release` réussi.
- Le paquet et le layout restent limités au Var Centre : configuration, QA et sorties site-local, plus l’entrée de planification du manifeste régional. `sites` reste limité aux cinq sites publiés et `plannedSites` contient six entrées ; aucun manifeste terrain global, manifeste terrain publié, sitemap, composant, route ou actif Web partagé n’a été modifié. `web.published=false` reste inchangé. Aucun release, push ou déploiement n’est autorisé par ce paquet.

Défauts et incertitudes résiduels : la donnée Litto3D est altimétrique et non navigable ; la profondeur affichée est plafonnée à 40 m malgré un maximum brut local proche de 42 m ; les cellules NoData du bord offshore restent explicitement exclues. Les dérivés Web n’ont pas été resynchronisés dans cette reprise. La fiche officielle décrit le site et son tombant, mais ce contrôle ne constitue pas une validation de sécurité, d’accès ou de mouillage.
