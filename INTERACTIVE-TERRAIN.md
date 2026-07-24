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
ecarter une marge de couverture source non fiable.

## Format

Le format est un petit paquet de cinq fichiers par site, plus un manifeste
global. Il ne s'agit pas d'un fichier 3D unique :

| Fichier | Role |
|---|---|
| `terrain.json` | Metadonnees, emprise, orientation, camera, encodages, credits et noms des textures |
| `height.bin` | Champ d'altitude `uint16` little-endian, en metres physiques avant exageration verticale |
| `valid-mask.bin` | Masque de validite compact, un bit par sommet |
| `topographic.webp` | Texture topo-bathymetrique |
| `orthophoto.webp` | Texture avec orthophoto |

`manifest.json` inventorie les sites et enregistre pour chaque fichier sa
taille et son empreinte SHA-256. Le navigateur charge les fichiers, construit
le maillage triangule avec Three.js et remplace seulement la texture lorsque
l'utilisateur bascule entre topographie et orthophoto.

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
