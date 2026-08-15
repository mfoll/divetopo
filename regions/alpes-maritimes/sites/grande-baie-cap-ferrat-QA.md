# QA — Grande Baie, Saint-Jean-Cap-Ferrat

## Statut

Paquet v1.5 publié : `web.published=true`, `plate_relief_source=interactive`. Le site dispose des quatre JPEG canoniques 2474×1712, des deux planches 5400×3250, du terrain interactif complet et des dérivés Web propres au slug. La pose initiale 3D est celle exportée et validée pour Grande Baie.

## Coordonnées et provenance

La fiche locale FFESSM 06 recense `Grande Baie (x2)` à Saint-Jean-Cap-Ferrat. Le mouillage ouest retenu est `43°41′10″N, 7°19′17″E`, soit `43.686111111, 7.321388889` et Lambert-93 `1048337.102, 6296987.064`. Le pixel Litto3D correspondant est à `−34.33 m`. Le nom et le tombant sont recoupés par Côte d’Azur France, l’étude plongée de la Métropole Nice Côte d’Azur et Nausicaa Plongée.

Source altimétrique : paquet officiel Shom–IGN Litto3D PACA 2015 `1045_6300.7z`, SHA-256 `2fae20c908db4f0b224e26c18ec28d3665d1e2f9924aff32941ff31f9b717633`, MNT 1 m, EPSG:2154, IGN69, MNT du 16/01/2015. Membres utilisés : `1048_6297`, `1048_6298`, `1049_6297`, `1049_6298`. Aucune interpolation hors cellules source.

Orthophoto : réponse officielle IGN BD ORTHO, couche `HR.ORTHOIMAGERY.ORTHOPHOTOS`, prise de vue `2023-07-10`, cache source EPSG:2154 de 1 m, SHA-256 `5f9f186eb17f62248ae3adcb9358ea71e92e7f1e745ca7922bd279c26ab783a7`. La résolution déclarée reste 1 m ; aucune sur-résolution n’est revendiquée.

Emprises finales, choisies dans la bande continue qui contient le mouillage et les profondeurs −20/−40 :

- focus : `[1048325, 6296800, 1048725, 6297150]` ;
- contexte : `[1048325, 6296800, 1048800, 6297200]` ;
- terrain orienté : centre `[1048537.5, 6297000]`, largeur 350 m, profondeur 425 m, regard 90°.

Les avertissements de rendu mesurent 5,4 % de NoData en 2D et 4,0 % dans le crop 3D. Ces cellules restent visibles comme NoData ou sont omises du maillage ; elles ne sont ni comblées ni présentées comme un MNT continu.

## Inventaire

- plans : `grande-baie-cap-ferrat-topobathy-2d.jpg`, `-2d-ortho.jpg` ;
- perspectives statiques : `-3d.jpg`, `-3d-ortho.jpg` ;
- planches : `grande-baie-cap-ferrat-planche-topographique.jpg`, `grande-baie-cap-ferrat-planche.jpg` ;
- terrain canonique et Web : `height.bin`, `valid-mask.bin`, `isobath-mask.bin`, `isobaths-vector.json`, `topographic.webp`, `orthophoto.webp`, `terrain.json` ;
- Web : deux plans JPEG, six variantes 3D desktop, deux variantes mobiles, deux téléchargements JPEG et deux aperçus de planche.

Le terrain final utilise une grille et des textures 425×350, avec 38 polylignes et 3394 points d’isobathes vectorielles source-dérivées de −5 à −45 m. Le contrôle de reprojection des 3394 points donne une moyenne de `0,0000115 m`, un p95 de `2,16e-8 m` et un maximum de `0,0092046 m`, dans la tolérance déclarée par `terrain.json`. La surface reste limitée aux cellules Litto3D officielles; les 5,4 % de NoData 2D et 4,0 % du crop 3D restent signalés et non comblés.

## Contrôles exécutés

- validation configuration et rasters avec `/Users/follm/home-projects/divetopo/.venv/bin/python -m cartography.regions.alpes_maritimes ... --check` : OK ;
- rendu des quatre JPEG avec `--render-only` : OK ;
- export et validation interne du paquet interactif schema v2 : OK ;
- composition des deux planches après captures propres hors mode calibration : OK, sans panneau de calibration dans les planches ;
- suite Python complète : 134/134 tests `unittest` passés ; lint Web : OK, 11 avertissements préexistants et aucune erreur ; tests Web : 41/41 passés ; build Web vinext : OK, avec les avertissements existants de taille de chunk et de classification des routes dynamiques ;
- inspection plein format des quatre JPEG 2474×1712, deux planches 5400×3250 et captures desktop/mobile : cadrage, échelle, nord, attributions, licence et textures lisibles ; rose nord et pied de source entièrement dans le cadre ; NoData limité au bord source ;
- pose exportée vérifiée : zoom `0.65`, azimut `34.9°`, élévation `19.77°`, `pan_right=-23.82`, `pan_up=44.09`, décalage est `-20 m`, décalage sud `0 m`, focus isobathe `0.05`, caméra `[-903.2988, 314.6462, 599.6212]`, cible `[-84.1281, -44.4541, 28.0696]` ; emprises inchangées ;
- provenance de la calibration groupée consignée sans copier le JSON brut : schéma `divetopo-camera-calibration-collection-v1`, export du `2026-08-15T06:21:38.384Z`, fichier local `/Users/follm/Downloads/divetopo-camera-calibrations-2.json`, SHA-256 `18269204b26988ad94ccb6decb60ff032d553492a74e3fa50a33ece70e5ae6ce` ;
- QA interactive dans le navigateur local : canvas WebGL visible, bascule Orthophoto/Topographie effective, commandes terrain disponibles ; aucune erreur spécifique à la route sur le rechargement final. Un message HMR transitoire est survenu pendant le redémarrage du serveur de génération ;
- `web.published` contrôlé à `true` ; routes FR/EN, terrain public, manifeste terrain et carte régionale Grande Baie vérifiés. Cap Gros reste absent des actifs Web, des routes et du manifeste terrain publié.
