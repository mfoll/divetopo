# Workflow topo-bathymetrique Reunion

Ce pipeline regenere depuis zero un plan 2D et une vue 3D oblique d'un site cotier de La Reunion. Il telecharge des donnees numeriques officielles, fusionne bathymetrie et topographie, extrait les isobathes puis produit les JPEG finaux.

## Sources

- Bathymetrie : MNT HYSCORES 2015 Ifremer, maille de 0,4 m, complete par Litto3D sur les pentes externes.
  - Catalogue : <https://www.data.gouv.fr/datasets/mnt-bathymetrique-a-haute-resolution-des-fonds-marins-des-zones-recifales-de-la-cote-ouest-de-lile-de-la-reunion-2015>
  - Saint-Gilles : <https://sextant.ifremer.fr/sextant_data/HYSCORES/HYSCORES_02_Bathy_OUEST_REU/Saint_Gilles/>
  - Saint-Leu : <https://sextant.ifremer.fr/sextant_data/HYSCORES/HYSCORES_02_Bathy_OUEST_REU/Saint_Leu/>
  - Etang-Sale : <https://sextant.ifremer.fr/sextant_data/HYSCORES/HYSCORES_02_Bathy_OUEST_REU/Etang_sale/>
  - Saint-Pierre : <https://sextant.ifremer.fr/sextant_data/HYSCORES/HYSCORES_02_Bathy_OUEST_REU/Saint_Pierre/>
- Topographie : IGN RGE ALTI, couche WMS `ELEVATION.ELEVATIONGRIDCOVERAGE.HIGHRES`, interrogee en GeoTIFF float 32 bits.
- Systeme de coordonnees commun : WGS 84 / UTM 40S, `EPSG:32740`.

HYSCORES ne couvre pas toute l'ile. Pour un site hors des quatre secteurs ci-dessus, il faut brancher une autre source bathymetrique numerique, par exemple Litto3D, avant d'utiliser le meme moteur de rendu.

## Prerequis

- Python local `.venv` avec `numpy`, `Pillow` et les bindings GDAL.
- Commandes GDAL accessibles dans le `PATH`, notamment `gdal_translate`.
- Acces reseau a `sextant.ifremer.fr` et `data.geopf.fr` lors de l'acquisition.

Le rendu seul est ensuite reproductible hors ligne a partir des GeoTIFF mis en cache dans `.tmp/bathy-renders/`.

## Regeneration du Cap La Houssaye

Depuis la racine du projet :

```bash
./bootstrap_macos.sh
.venv/bin/python generate_reunion_topobathy.py sites/cap-la-houssaye.json --refresh
```

`--refresh` force un nouveau telechargement. Sans cette option, les fichiers deja presents sont reutilises. Pour ne faire que le rendu :

```bash
.venv/bin/python generate_reunion_topobathy.py sites/cap-la-houssaye.json --render-only
```

Le fichier [sites/cap-la-houssaye.json](sites/cap-la-houssaye.json) contient tous les parametres propres au site et les chemins des deux sorties canoniques.

## Etapes executees

1. Le script ouvre l'index du secteur HYSCORES et identifie le GeoTIFF bathymetrique numerique, pas le JPEG2000 colore.
2. `gdal_translate` lit uniquement `context_bbox_utm40s` dans le GeoTIFF Ifremer de 2,5 Go grace a `/vsicurl/`.
3. Les altitudes marines negatives sont converties en profondeurs positives. Les valeurs terrestres et nodata deviennent `-99999`.
4. Le RGE ALTI est telecharge sur exactement la meme emprise, a 0,5 m par defaut.
5. L'emprise 2D `focus_bbox_utm40s` est recadree localement depuis les deux MNT de contexte.
6. Les rasters sont eventuellement tournes par quarts de tour afin de placer la mer en haut des tableaux de calcul.
7. La cote a 0 m est interpolee en polygone continu. HYSCORES et RGE ALTI sont fusionnes sans combler les lacunes internes par une couleur arbitraire.
8. Les isobathes `-5`, `-10`, `-15` et `-20 m` sont extraites vectoriellement puis lissees.
9. Le plan 2D utilise l'emprise de mise au point. La 3D utilise la grande emprise de contexte, mais conserve le cadrage final sur le site.
10. Les JPEG recoivent une echelle de 50 m et une rose des vents recalculee selon la rotation.

## Ajouter un site

Copier le JSON existant vers `sites/<slug>.json`, puis renseigner :

- `slug` et `title` ;
- `hyscores_directory`, choisi parmi les quatre secteurs officiels ;
- `focus_bbox_utm40s` : rectangle serre contenant le site a lire en 2D ;
- `context_bbox_utm40s` : rectangle plus grand contenant integralement le precedent ;
- `rotation_k` : rotation `numpy.rot90` qui place la mer en haut du raster de travail ;
- les parametres de camera et, si necessaire, les chemins de sortie.

Correspondance de `rotation_k` :

| Mer dans le raster UTM initial | `rotation_k` |
|---|---:|
| nord | 0 |
| est | 1 |
| sud | 2 |
| ouest | 3 |

La rose des vents 2D et la rose de la vue depuis le large sont adaptees automatiquement. Le plan n'est donc pas necessairement nord en haut, mais son orientation reste explicite et correcte.

Pour la 3D, prevoir dans `context_bbox_utm40s` environ 300 a 400 m de donnees reelles supplementaires vers le large, 100 a 200 m sur chaque cote et 200 a 300 m vers l'interieur. Cette marge doit etre augmentee si le point de vue est abaisse.

## Parametres de rendu

- `max_depth_m` : profondeur maximale de la palette et du relief affiche, actuellement 20 m.
- `camera_tilt` : angle apparent de la grille. Une valeur plus faible abaisse le point de vue.
- `coast_frame_fraction` : hauteur de la cote dans l'image 3D, de 0 en haut a 1 en bas.
- `vertical_exaggeration` : amplification verticale du relief.
- `topography_resolution_m` : resolution demandee au WMS IGN. La requete est refusee au-dela de 5 000 pixels sur un axe.

## Controle qualite obligatoire

Avant de retenir une figure :

1. Verifier que la cote noire suit la jonction terre-mer sans marches ni polygones de remplissage.
2. Verifier que les isobathes ne s'arretent pas au milieu de la surface visible. Si elles touchent le bord du raster source, agrandir le contexte au lieu de les prolonger graphiquement.
3. Verifier que le bord du MNT de contexte est hors image 3D. Une bande, des pointes miroir ou un faux ciel indiquent une marge insuffisante.
4. Comparer la rose des vents a une orthophoto ou a Google Maps.
5. Verifier la barre de 50 m a partir de la taille de pixel du GeoTIFF.
6. Inspecter le rendu final en pleine resolution, en particulier les tombants, les etiquettes et le bas de l'image.

## Fichiers du pipeline

- `generate_reunion_topobathy.py` : acquisition, cache, recadrage et orchestration.
- `render_fused_relief.py` : fusion, lissage, isobathes et rendus 2D/3D.
- `sites/*.json` : parametres reproductibles de chaque site.
- `.tmp/bathy-renders/` : sources et extraits regenerables, non destines a etre versionnes.
- `outputs/` : figures finales.
