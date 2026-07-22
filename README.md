# Topo-bathymetrie des sites de plongee de La Reunion

Pipeline reproductible pour produire un plan 2D, une vue 3D oblique et une carte de localisation insulaire a partir de donnees officielles : bathymetrie HYSCORES de l'Ifremer et topographie RGE ALTI de l'IGN. Une variante 2D optionnelle remplace uniquement la terre par l'orthophoto IGN 20 cm georeferencee.

Le moteur fusionne les deux MNT, interpole la cote a 0 m, lisse le bruit de cellule, extrait les isobathes `-5`, `-10`, `-15` et `-20 m`, puis ajoute une rose des vents et une echelle metrique. Chaque site est defini par un fichier JSON distinct.

## Exemple : Cap La Houssaye

| Plan 2D | Vue 3D depuis le large |
|---|---|
| ![Plan 2D du Cap La Houssaye](outputs/cap-la-houssaye-pointe-westwide-rgealti-topo-bathy-final-2d.jpg) | ![Vue 3D du Cap La Houssaye](outputs/cap-la-houssaye-pointe-westwide-rgealti-topo-bathy-final-3d.jpg) |

### Variantes avec orthophoto terrestre

![Plan 2D hybride du Cap La Houssaye](outputs/cap-la-houssaye-pointe-westwide-rgealti-topo-bathy-final-2d-ortho.jpg)

![Vue 3D hybride du Cap La Houssaye](outputs/cap-la-houssaye-pointe-westwide-rgealti-topo-bathy-final-3d-ortho.jpg)

### Localisation dans l'ile

![Localisation du Cap La Houssaye a La Reunion](outputs/cap-la-houssaye-localisation-reunion.jpg)

### Planche assemblee

![Planche du Cap La Houssaye](outputs/cap-la-houssaye-planche.jpg)

## Installation sur macOS

Homebrew est requis. Le script installe Python et GDAL, puis cree un environnement local :

```bash
./bootstrap_macos.sh
```

## Regeneration complete

```bash
.venv/bin/python generate_reunion_topobathy.py sites/cap-la-houssaye.json --refresh
```

Sans `--refresh`, les GeoTIFF deja mis en cache sont reutilises. Pour refaire uniquement les images :

```bash
.venv/bin/python generate_reunion_topobathy.py sites/cap-la-houssaye.json --render-only
```

Les donnees sources et les extraits regenerables restent dans `.tmp/bathy-renders/` et ne sont pas versionnes.

Pour assembler les trois cartes apres leur regeneration :

```bash
.venv/bin/python compose_site_plate.py sites/cap-la-houssaye.json
```

## Reutilisation

Pour ajouter un site, copier `sites/cap-la-houssaye.json`, puis modifier le secteur HYSCORES, les emprises UTM 40S, l'orientation de la cote et les parametres de camera. Le moteur prend en charge les quatre orientations cardinales et recalcule automatiquement les compas 2D et 3D.

Le processus complet, les sources, chaque parametre et les controles qualite sont documentes dans [WORKFLOW.md](WORKFLOW.md).

## Licences

- Le code Python et les scripts sont distribues sous licence [MIT](LICENSE).
- Les cartes et figures de `outputs/` sont distribuees sous [CC BY-NC-SA 4.0](LICENSE-MAPS.md), sous reserve des droits attaches aux donnees sources.
- Les licences, attributions obligatoires, versions des jeux de donnees et avertissements sont detailles dans [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).

La licence `CC BY-NC-SA`, plutot que `CC BY-NC-ND`, est imposee par la clause de partage dans les memes conditions du MNT HYSCORES. Les cartes ne doivent pas etre utilisees pour la navigation ni comme seule base d'une decision engageant la securite en mer.
