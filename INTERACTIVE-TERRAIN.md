# Paquet de relief 3D interactif

Le relief interactif est un livrable cartographique du pipeline, au meme titre
que les JPEG 2D, les perspectives 3D et les planches. Le site web le consomme,
mais ne le genere pas.

La commande canonique est :

```bash
.venv/bin/python generate_interactive_terrain.py
```

Elle reconstruit les paquets de tous les fichiers `sites/*.json` a partir des
GeoTIFF valides du cache local et les ecrit dans
`outputs/interactive-terrain/`.
La profondeur maximale reprend `max_depth_m`, sauf lorsqu'une configuration
documente explicitement une limite `interactive_max_depth_m` inferieure pour
ecarter une marge de couverture source non fiable. Chaque site declare un
`interactive_footprint_utm40s`, rectangle oriente obligatoirement contenu dans
l'emprise de contexte. Sa largeur suit approximativement la cote et sa
profondeur l'axe de vue depuis le large vers la terre. Le pipeline recadre
d'abord son rectangle englobant nord en haut, puis masque le relief sur
l'emprise orientee exacte. Le paquet Web peut ainsi couvrir une zone plus large
que le plan 2D sans modifier celui-ci. Pointe au Sel conserve une profondeur
maximale de `40 m`.

La validation exige que `look_bearing_deg` corresponde a
`view_bearing_deg`, que la largeur depasse d'au moins 15 % la largeur visible
initiale et que la profondeur conserve au moins 20 % de marge selon
l'inclinaison, le rapport d'image et l'echelle de projection. Le champ
facultatif `interactive_view_visible_width_m` peut ajuster le seul cadrage Web
sans modifier la perspective statique.

Une limite marine profonde de bord peut etre completee explicitement par
`deep_edge_nodata_terrain_fill`. Seules les composantes sans contact terrestre,
entourees par une frontiere marine assez longue et plus profonde que
`deep_edge_nodata_terrain_min_depth_m`, deviennent un plateau uniforme a la
profondeur maximale. L'option est desactivee par defaut.

## Format

Le format est un petit paquet de six fichiers par site, plus un manifeste
global. Il ne s'agit pas d'un fichier 3D unique :

| Fichier | Role |
|---|---|
| `terrain.json` | Metadonnees, emprise, orientation, camera, encodages, credits et noms des textures |
| `height.bin` | Champ d'altitude `uint16` little-endian, en metres physiques avant exageration verticale |
| `valid-mask.bin` | Masque de validite compact, un bit par sommet |
| `isobath-mask.bin` | Masque compact des sommets ou les courbes restent strictement derivees de la source |
| `topographic.webp` | Texture topo-bathymetrique |
| `orthophoto.webp` | Texture avec orthophoto |

`manifest.json` inventorie les sites et enregistre pour chaque fichier sa
taille et son empreinte SHA-256. Le navigateur charge les fichiers, construit
le maillage triangule avec Three.js et remplace seulement la texture lorsque
l'utilisateur bascule entre topographie et orthophoto.

Le schema 2 distingue la validite du terrain de celle des isobathes. Lorsqu'une
lacune profonde de bord est completee par un plateau uniforme a la profondeur
maximale, `valid-mask.bin` conserve ce terrain visible, tandis que
`isobath-mask.bin` exclut le remplissage et toutes ses cellules de transition.
Les courbes WebGL restent ainsi derivees des seules altitudes source, sans
inventer de niveaux intermediaires autour du plateau.

Le champ d'altitude conserve ses sommets de bord et compte au maximum `513`
sommets sur son plus grand axe. Ce plafond modere augmente le detail
geometrique des emprises interactives elargies sans publier les grilles
submetriques beaucoup plus lourdes des perspectives statiques. L'autre
dimension conserve le rapport du raster source.

`terrain.json` contient aussi l'azimut, l'inclinaison et le cadrage initial. Il
enregistre l'emprise sous `footprint`, avec son centre, ses dimensions, son
azimut et ses quatre coins UTM 40S. Le
champ optionnel `view.horizontalCenterOffsetM` reprend la projection horizontale
du centre statique; une valeur positive deplace la cible vers la droite de
l'ecran. Il est actuellement utilise pour aligner les vues initiales de la
Passe de l'Hermitage et de Pont Rouge sur leurs perspectives imprimees.

Les isobathes ne sont ni une texture ni un fichier vectoriel supplementaire.
Le visualiseur les calcule analytiquement depuis l'altitude exportee, dans des
plans parfaitement horizontaux tous les 5 m. Les niveaux visibles vont de
`-5 m` au dernier multiple de 5 strictement inferieur a la profondeur maximale.
Le coeur reprend exactement la couleur de la palette bathymetrique a chaque
profondeur, tandis que le liseré noir, la legende fixe, le bouton d'affichage
et la rose dynamique relevent du visualiseur. Le masque
`isobath-mask.bin` garantit qu'aucune courbe n'est creee sur une completion
artificielle ou sa transition.

Ce decoupage est volontaire :

- la geometrie n'est telechargee qu'une fois pour les deux styles ;
- les textures se mettent en cache separement ;
- les altitudes physiques, la provenance et l'exageration restent explicites ;
- le paquet peut etre utilise par un autre visualiseur que le site actuel.

Un conteneur unique comme GLB serait possible, mais il dupliquerait ou
complexifierait le changement de texture et rendrait la provenance moins
directe. Une archive ZIP ne serait pas directement exploitable par le
navigateur sans une etape de decompression.

## Frontiere avec le site

Le site ne doit jamais appeler `generate_interactive_terrain.py`. Son etape
d'assets copie et verifie le paquet canonique vers `site/public/terrain/`,
comme elle derive deja les images responsives depuis les JPEG de `outputs/`.

La responsabilite est donc :

1. pipeline cartographique : configurations, donnees sources, cartes 2D,
   perspectives statiques, planches et paquets interactifs canoniques ;
2. site web : interface, navigation, visualiseur Three.js, assets responsifs,
   copie des paquets canoniques et deploiement.

Les fichiers de `site/public/terrain/` sont des derives de publication. La
source de verite reste `outputs/interactive-terrain/`.
