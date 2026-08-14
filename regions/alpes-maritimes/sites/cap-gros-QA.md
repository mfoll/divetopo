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
- Pose finale : zoom 0,68, azimut orbital 0°, élévation 30°, `pan_right_m=89.06`, `pan_up_m=0`, offsets centre 0, focus d’étiquette NDC 0,25 ; caméra `[-75.0, 1016.1365, -1866.442]`, cible `[-75.0, 0, -106.442]`.
- Quatre images statiques pleine résolution inspectées : 2D topographique, 2D orthophoto, 3D topographique et 3D orthophoto. Aucun artefact de relief ni pointe verticale observé avec la pose finale.
- Deux planches pleine résolution et le locator Cap Gros inspectés après régénération depuis les quatre images finales.
- Dérivés Web inspectés en desktop et mobile pour les deux textures. Vérification de cohérence des captures dynamiques : corrélations 0,9948 à 0,9996, MAE 0,0036 à 0,0114 selon le dérivé.
- Page locale FR et EN contrôlée sur desktop ; les dérivés terrain mobile ont été contrôlés à pleine résolution. Les erreurs console bloquantes étaient absentes lors du contrôle local.

## Périmètre Git et publication

Le commit ne doit contenir que la configuration `cap-gros`, ce QA, les sorties `cap-gros` sous `regions/alpes-maritimes/` et les dérivés Web strictement sous les chemins `cap-gros`. Aucun manifeste régional, `region.json`, sitemap, composant Web partagé, release, push ou déploiement n’est inclus. La calibration locale a été désactivée et retirée du code partagé avant staging.
