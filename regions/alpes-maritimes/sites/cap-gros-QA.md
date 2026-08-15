# QA site-local · Cap Gros

## Verdict

Paquet local v1.5 produit et contrôlé pour le seul site Cap Gros, Antibes, slug `cap-gros`. La publication reste explicitement désactivée (`web.published=false`). Le terrain est un produit dérivé local, non une observation bathymétrique continue mesurée : les isobathes officielles servent de contraintes vectorielles et la surface est interpolée localement. Cette limite et le contrôle de bordure sont conservés ici pour éviter de surinterpréter la précision du modèle.

## Identité et position

- Site : Cap Gros, Antibes · Cap d’Antibes.
- Coordonnées de référence : 43°33′07.0″ N · 7°08′42.0″ E, soit 43.551944444 · 7.145000000.
- Point projeté : EPSG:2154 / RGF93 Lambert-93, `[1034914.520, 6281334.213]` m.
- Contrôle indépendant : l’avis officiel du Département 06 décrit les repères Cap Gros Nord (43°33.158′ N, 7°08.720′ E, 7,5 m) et Cap Gros Sud (43°33.090′ N, 7°08.686′ E, 5,9 m), dans le secteur Cap d’Antibes.

## Sources et référentiels

- Bathymétrie officielle : [Métropole Nice Côte d’Azur, Bathymétrie](https://opendata.nicecotedazur.org/data/dataset/bathymetrie), isobathes tous les mètres, levé multifaisceaux entre Cap d’Ail et Antibes (2007), producteur Direction de l’environnement et de l’énergie, Licence Ouverte.
- Fichier source : [isobathes-1m.geojson](https://opendata.nicecotedazur.org/data/storage/f/2014-05-22T08%3A24%3A21.830Z/isobathes-1m.geojson), SHA-256 `e687a6e8166b6fc692b6182720f3f3c9b00dac665d5d0e8020d4a1a9a76f92ff`. Le fichier est WGS84 / EPSG:4326, reprojeté localement en EPSG:2154 pour les calculs.
- Topographie : [IGN RGE ALTI WMS](https://data.geopf.fr/wms-r/wms), couche `ELEVATION.ELEVATIONGRIDCOVERAGE.HIGHRES`, grille locale 1 m, référentiel vertical IGN69.
- Orthophoto : [IGN BD ORTHO](https://cartes.gouv.fr/rechercher-une-donnee/dataset/IGNF_BD-ORTHO), couche `HR.ORTHOIMAGERY.ORTHOPHOTOS`, résolution locale 0,5 m, prise de vue du 10-07-2023.
- Cartographie produite : CC BY-NC-SA 4.0, avec attribution NCA, IGN RGE ALTI et IGN BD ORTHO dans les sorties site-locales.

## Couverture et méthode

- Contexte calculé : `[1034150, 6280650, 1035650, 6282150]` EPSG:2154, 1 500 × 1 500 m à 1 m.
- Emprise de focus : `[1034500, 6281000, 1035200, 6281800]` EPSG:2154.
- Emprise interactive : centre `[1034900, 6281400]`, 650 × 800 m, regard 180°.
- Grille interactive : 417 × 513 sommets, 650 × 800 m, profondeur maximale -45 m. La surface exportée est valide à 100 % ; `deep_edge_nodata_terrain_fill=false` et les masques `valid-mask.bin` / `isobath-mask.bin` conservent les transitions et les zones non garanties.
- Méthode : sélection de branches locales cohérentes des isobathes NCA -5 à -45 m, lissage/suréchantillonnage vectoriel selon la méthode méditerranéenne v1.5, interpolation linéaire sur grille régulière, et contrôle de la côte par les points 0 m RGE ALTI. Les contours vectoriels source-dérivés restent exportés séparément.
- Résultat raster final : min 0 m, max 45 m de profondeur, moyenne 26,52748 m, écart-type 19,68555 m, validité 100 %.

## Contrôle numérique et limites

Sur 175 094 points de contrôle de l’emprise élargie, dont 4 367 contrôles 0 m, l’échantillonnage au pixel le plus proche du raster final donne :

- tous contrôles : MAE 0,198959 m, RMSE 0,480701 m, p95 absolu 0,961290 m, maximum absolu 7,001837 m ; 77 écarts absolus dépassent 5 m ;
- contrôles 0 m : MAE 0,022217 m, RMSE 0,126049 m, p95 absolu 0,109049 m, maximum absolu 2,553233 m ; aucun écart ne dépasse 5 m ;
- 49 échantillons tombent exactement sur la limite inférieure du raster et sont ramenés au dernier pixel disponible pour ce contrôle discret.

Ces chiffres valident la continuité opérationnelle et l’absence de NoData dans l’emprise livrée, mais ne constituent pas une précision verticale d’un levé continu : la source officielle fournie est un jeu de contours, pas un raster bathymétrique continu. Le plafond de -45 m est donc une limite de représentation locale, pas une profondeur mesurée au-delà des contrôles disponibles.

## Pose calibrée et QA visuelle

- Mode de calibration utilisé uniquement sur serveur local avec `?camera-calibration`, caméra déplaçable et paramètres exportés dans un JSON groupé `divetopo-camera-calibration-collection-v1`; aucune interface de téléchargement JSON par site n’est livrée.
- Pose finale exportée et appliquée : zoom `0.68`, azimut orbital `-67.77°`, élévation `14.4°`, `pan_right_m=80.13`, `pan_up_m=60.09`, offsets centre est/sud `0/0`, focus d’étiquette NDC `0.25` ; caméra `[1773.8383, 467.0649, -811.7817]`, cible `[-48.3203, -38.3408, -67.177]`. Les emprises et la continuité de la surface ne changent pas.
- Provenance de la calibration groupée consignée sans copier le JSON brut : schéma `divetopo-camera-calibration-collection-v1`, export du `2026-08-15T06:21:38.384Z`, fichier local `/Users/follm/Downloads/divetopo-camera-calibrations-2.json`, SHA-256 `18269204b26988ad94ccb6decb60ff032d553492a74e3fa50a33ece70e5ae6ce`.
- Quatre images statiques pleine résolution inspectées : 2D topographique, 2D orthophoto, 3D topographique et 3D orthophoto. Aucun artefact de relief ni pointe verticale observé avec la pose finale.
- Deux planches pleine résolution et le locator Cap Gros inspectés après régénération depuis les quatre images finales.
- Captures dynamiques desktop/mobile produites temporairement sur le serveur local avec l’attribution Cap Gros correcte : corrélations directes PNG/WebP `0.99117` (orthophoto) et `0.99142` (topographique), MAE `0.01786` et `0.01739`. Le vérificateur de dépôt n’est pas déclaré passant pour Cap Gros, car il force `sourceAttribution=""` et remplace l’attribution RGE ALTI par l’attribution générique de région sur la capture mobile ; aucun dérivé Cap Gros n’a été copié sous `apps/web/public/`.
- La page locale FR/EN avec `?camera-calibration` a été contrôlée uniquement pendant cette session de calibration ; la caméra est déplaçable, les paramètres sont visibles et l’export est groupé. Le serveur et l’UI de calibration ont ensuite été retirés du worktree avant QA publiée.

## Périmètre Git et publication

Le commit Cap Gros ne doit contenir que sa configuration, ce QA et ses sorties sous `regions/alpes-maritimes/`. `web.published=false` reste inchangé : aucun manifeste terrain publié, route, sitemap, actif Web ou test partagé Cap Gros n’est inclus. La calibration locale a été désactivée et retirée du code partagé avant staging.
