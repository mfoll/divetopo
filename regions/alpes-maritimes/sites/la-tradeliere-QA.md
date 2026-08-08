# La Tradelière · provenance et QA v1.4

## Position et profondeur

- Le rapport DIRM Méditerranée, tableau 326 « Tradelière (Grotte à Corail) », donne `43.5134 N, 7.07158333 E`, une profondeur maximale de 40 m et la classe 20–40 m : [rapport DIRM, PDF](https://www.dirm.mediterranee.developpement-durable.gouv.fr/IMG/pdf/2_rapport-3.pdf), p. 203 du PDF.
- [Plongée Cannes · Les sites](https://plongee-cannes.com/les-sites) décrit La Tradelière entre 4 et 42 m. La limite cartographique est donc fixée à −42 m.
- La position DIRM est convertie en Lambert-93 / EPSG:2154 : `1029208.587, 6276747.228`. Elle sert de repère de site ; elle n’est pas assimilée au point profond.

## Géométrie et provenance

- Source continue : paquet officiel [Shom–IGN Litto3D PACA 2015](https://diffusion.shom.fr/donnees/litto3d-paca-2015.html), prépaquet `1025_6280.7z`, MNT maillé à 1 m, Lambert-93 / IGN69. Les cinq membres réellement utilisés sont énumérés exactement dans `la-tradeliere.json`.
- Emprise 2D : `[1028100, 6276600, 1029300, 6277100]`, soit environ 96,3 % de cellules valides ; emprise de contexte 3D : `[1028000, 6276600, 1029300, 6277200]`, soit environ 97,2 % de cellules valides. La profondeur mesurée atteint −45,66 m dans ces extraits.
- Contrôle secondaire : [Métropole Nice Côte d’Azur, Bathymétrie](https://www.data.gouv.fr/datasets/bathymetrie), isobathes métriques de 2007. Ces lignes servent uniquement au contrôle de cohérence. Elles ne sont ni fermées ni interpolées en MNT.
- Orthophoto : service officiel IGN, couche `HR.ORTHOIMAGERY.ORTHOPHOTOS`, prise de vue vérifiée au `2023-06-26`, résolution demandée 0,4 m en 2D et 0,8 m en 3D. La réponse WMS contient 97,96–97,97 % de pixels valides sur les extraits utiles. Son en-tête Lambert mal formé a été corrigé en EPSG:2154 sans rééchantillonnage.
- Les trous Litto3D sont conservés dans les masques et restent visibles en bordure. Aucune interpolation de comblement, aucun plateau profond et aucun substitut issu des seules isobathes n’est publié.

## Terrain interactif

- Paquet canonique : grille `513 × 321`, 327 680 triangles, 95,138 % de sommets valides, élévations physiques de −42,0 à +8,819 m.
- Masques distincts : `valid-mask.bin` pour les données mesurées et `isobath-mask.bin` pour les sommets où une isobathe source est sûre.
- Isobathes vectorielles à 5 m : 8 niveaux, 10 polylignes et 2 063 points. Résidu de reprojection : moyenne `2,68e-7 m`, p95 `6,23e-10 m`, maximum `0,0005305 m`, dans la tolérance.
- Textures topographique et orthophoto, crédits complets et date de prise de vue sont enregistrés dans `terrain.json`. Le même paquet est copié sous `apps/web/public/terrain/la-tradeliere/`.

## Contrôles visuels et Web

- Contrôle plein format des plans 2D topographique et orthophoto, des vues 3D statiques, des deux captures 3D dynamiques `2474 × 1712`, des variantes mobiles `960 × 662`, du localisateur régional et des deux planches `5400 × 3250` : cadrage, légendes, étiquettes, crédits et NoData sont lisibles et cohérents.
- QA interactive locale avec le composant Web réel : chargement du canvas, fond orthophoto initial, bascule topographique, rotation par glisser, réinitialisation, isobathes, plein écran et liens de téléchargement. Contrôle desktop et viewport mobile `390 × 844`; aucune erreur ni alerte console.
- Dérivés Web présents : plans 2D, trois tailles desktop par style, une taille mobile par style, téléchargements JPEG pleine définition, aperçus de planche et paquet terrain complet.
- La configuration et les builders ont été exécutés avec `/Users/follm/home-projects/divetopo/.venv/bin/python`. Les caches Litto3D/IGN, extraits WMS et captures intermédiaires ne font pas partie du commit.

## Statut d’intégration

`web.published` reste `false`. Aucun `region.json`, carte régionale, manifeste agrégé, accueil, version ou release n’est modifié ; aucun push ni déploiement n’est effectué. La publication reste une décision de la QA régionale.
