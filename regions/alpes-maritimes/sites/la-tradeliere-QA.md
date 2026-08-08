# La Tradelière · provenance et QA

## Sources recoupées

- Le rapport DIRM Méditerranée, tableau 326 « Tradelière (Grotte à Corail) », donne `43.5134 N, 7.07158333 E`, une profondeur maximale indiquée de 40 m et la classe 20–40 m : [rapport DIRM, PDF](https://www.dirm.mediterranee.developpement-durable.gouv.fr/IMG/pdf/2_rapport-3.pdf), p. 203 du PDF.
- Une source de club décrit le site comme allant de 4 à 42 m : [Plongée Cannes · Les sites](https://plongee-cannes.com/les-sites).
- La coordonnée DIRM est convertie en EPSG:2154 / Lambert-93 dans le JSON : `1029208.587, 6276747.228`. La cellule Litto3D correspondante vaut environ −5,21 m. Elle est donc conservée comme repère de localisation, pas comme point de profondeur P1.

## Géométrie exploitée

La bathymétrie provient du paquet [Shom–IGN Litto3D PACA 2015](https://diffusion.shom.fr/donnees/litto3d-paca-2015.html) `1025_6280.7z`. Les cinq membres MNT1m effectivement recoupés sont ceux listés dans `la-tradeliere.json` pour les tuiles 1028/6276, 1028/6277, 1028/6278, 1029/6277 et 1029/6278, en Lambert-93 / IGN69.

Dans l’emprise statique, le MNT contient des cellules jusqu’à −47,57 m, dont 121 963 cellules à au moins −42 m. Le rectangle interactif orienté vers le sud-ouest conserve environ 82,9 % de vertices mesurés dans son masque. Les NoData du levé restent NoData : aucune interpolation, fermeture de bord ou plateau profond n’est publié.

Le jeu « Bathymétrie - Métropole de Nice » n’est pas utilisé : son catalogue décrit des isobathes tous les mètres issues d’un levé entre Cap d’Ail et Antibes, et son emprise ne couvre pas la coordonnée Tradelière. Des isobathes seules ne peuvent pas remplacer le MNT continu local.

## Sorties et limites

- `la-tradeliere-topobathy-2d.jpg` et `la-tradeliere-topobathy-3d.jpg` ont été contrôlés en pleine résolution ; les lacunes NoData sont visibles et annotées.
- `outputs/interactive-terrain/la-tradeliere/` contient le champ d’altitude, les masques, les isobathes vectoriels et la texture topographique correspondant au rectangle orienté.
- L’orthophoto IGN n’est pas incluse dans ce commit : `orthophoto_enabled` reste `false` pour ne pas présenter une texture non acquise comme une observation. Le paquet terrain est donc topographique uniquement et reste non publié.
- Le manifeste régional Alpes-Maritimes, les agrégats Web et les routes ne sont pas créés ici. Le validateur générique actuel réclame `regions/alpes-maritimes/region.json`; cette pièce relève du coordinateur régional et est explicitement hors de ce commit.
