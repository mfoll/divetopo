# QA — Grande Baie, Saint-Jean-Cap-Ferrat

## Statut

Paquet v1.4 complet et non publié : `web.published=false`, `plate_relief_source=interactive`. Le site dispose des quatre JPEG canoniques 1600×1184, des deux planches 5400×3250, du terrain interactif complet et des dérivés Web propres au slug.

## Coordonnées et provenance

La fiche locale FFESSM 06 recense `Grande Baie (x2)` à Saint-Jean-Cap-Ferrat. Le mouillage ouest retenu est `43°41′10″N, 7°19′17″E`, soit `43.686111111, 7.321388889` et Lambert-93 `1048337.102, 6296987.064`. Le pixel Litto3D correspondant est à `−34.33 m`. Le nom et le tombant sont recoupés par Côte d’Azur France, l’étude plongée de la Métropole Nice Côte d’Azur et Nausicaa Plongée.

Source altimétrique : paquet officiel Shom–IGN Litto3D PACA 2015 `1045_6300.7z`, SHA-256 `2fae20c908db4f0b224e26c18ec28d3665d1e2f9924aff32941ff31f9b717633`, MNT 1 m, EPSG:2154, IGN69, MNT du 16/01/2015. Membres utilisés : `1048_6297`, `1048_6298`, `1049_6297`, `1049_6298`. Aucune interpolation hors cellules source.

Orthophoto : réponse officielle IGN BD ORTHO, couche `HR.ORTHOIMAGERY.ORTHOPHOTOS`, prise de vue `2023-07-10`, cache source EPSG:2154 de 1 m, SHA-256 `5f9f186eb17f62248ae3adcb9358ea71e92e7f1e745ca7922bd279c26ab783a7`. La résolution déclarée reste 1 m ; aucune sur-résolution n’est revendiquée.

Emprises finales, choisies dans la bande continue qui contient le mouillage et les profondeurs −20/−40 :

- focus : `[1048325, 6296800, 1048725, 6297150]` ;
- contexte : `[1048325, 6296800, 1048800, 6297200]` ;
- terrain orienté : centre `[1048537.5, 6297000]`, largeur 350 m, profondeur 425 m, regard 90°.

Les avertissements de rendu mesurent 5,4 % de NoData en 2D et 4,1 % dans le crop 3D. Ces cellules restent visibles comme NoData ou sont omises du maillage ; elles ne sont ni comblées ni présentées comme un MNT continu.

## Inventaire

- plans : `grande-baie-cap-ferrat-topobathy-2d.jpg`, `-2d-ortho.jpg` ;
- perspectives statiques : `-3d.jpg`, `-3d-ortho.jpg` ;
- planches : `grande-baie-cap-ferrat-planche-topographique.jpg`, `grande-baie-cap-ferrat-planche.jpg` ;
- terrain canonique et Web : `height.bin`, `valid-mask.bin`, `isobath-mask.bin`, `isobaths-vector.json`, `topographic.webp`, `orthophoto.webp`, `terrain.json` ;
- Web : deux plans JPEG, six variantes 3D desktop, deux variantes mobiles, deux téléchargements JPEG et deux aperçus de planche.

Le terrain final utilise une grille et des textures 426×351, avec 11 polylignes et 815 points d’isobathes vectorielles source-dérivées de −5 à −40 m (dont une polyligne −40). Le contrôle de reprojection des vecteurs est dans la tolérance déclarée par `terrain.json`.

## Contrôles exécutés

- validation configuration et rasters avec `/Users/follm/home-projects/divetopo/.venv/bin/python -m cartography.regions.alpes_maritimes ... --check` : OK ;
- rendu des quatre JPEG avec `--render-only` : OK ;
- export et validation interne du paquet interactif schema v2 : OK ;
- composition des deux planches et vérification des dérivés Web par les builders au commit `e9b38a036cdad5bb0d24e26009fdefb7be7501a9` : OK ;
- 70 tests ciblés (`config`, `interactive`, `plate`, `regional_manifest`, `sync_interactive_terrain`, `vector_isobaths`) : OK ;
- build Web vinext : OK, avertissement existant de taille de chunk uniquement ;
- inspection plein format des quatre JPEG, deux planches et captures desktop/mobile : cadrage, échelle, nord, attributions, licence et textures lisibles ; NoData limité au bord source ;
- QA interactive dans le navigateur local : canvas WebGL visible, bascule Orthophoto/Topographie effective, commandes terrain disponibles, aucune erreur ni alerte console ;
- `web.published` contrôlé à `false`. Aucun manifeste agrégé, `region.json`, carte régionale, accueil, version ou release n’est inclus.
