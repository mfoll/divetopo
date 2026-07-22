# Workflow topo-bathymetrique Reunion

Ce pipeline regenere depuis zero un plan 2D, une vue 3D oblique et une carte de localisation insulaire d'un site cotier de La Reunion. Il telecharge des donnees numeriques officielles, fusionne bathymetrie et topographie, extrait les isobathes puis produit les JPEG finaux.

## Sources

- Bathymetrie : MNT HYSCORES 2015 Ifremer, maille de 0,4 m, complete par Litto3D sur les pentes externes. Attribution obligatoire : `Projet HYSCORES (Ifremer, UBO, Office de l'Eau Reunion)`. Licence source : CC BY-NC-SA, version non precisee dans la metadonnee.
  - Catalogue : <https://www.data.gouv.fr/datasets/mnt-bathymetrique-a-haute-resolution-des-fonds-marins-des-zones-recifales-de-la-cote-ouest-de-lile-de-la-reunion-2015>
  - Saint-Gilles : <https://sextant.ifremer.fr/sextant_data/HYSCORES/HYSCORES_02_Bathy_OUEST_REU/Saint_Gilles/>
  - Saint-Leu : <https://sextant.ifremer.fr/sextant_data/HYSCORES/HYSCORES_02_Bathy_OUEST_REU/Saint_Leu/>
  - Etang-Sale : <https://sextant.ifremer.fr/sextant_data/HYSCORES/HYSCORES_02_Bathy_OUEST_REU/Etang_sale/>
  - Saint-Pierre : <https://sextant.ifremer.fr/sextant_data/HYSCORES/HYSCORES_02_Bathy_OUEST_REU/Saint_Pierre/>
- Topographie : IGN RGE ALTI, couche WMS `ELEVATION.ELEVATIONGRIDCOVERAGE.HIGHRES`, interrogee en GeoTIFF float 32 bits. Licence Ouverte 2.0; mise a jour du produit arretee en 2024.
- Orthophoto terrestre optionnelle : IGN, couche WMS `HR.ORTHOIMAGERY.ORTHOPHOTOS` (Ortho 20 cm), interrogee en GeoTIFF sur la meme emprise UTM 40S : <https://data.geopf.fr/wms-r/wms>. Au Cap La Houssaye, `GetFeatureInfo` identifie la prise de vue du 22 juillet 2025.
- Relief marin de la carte insulaire : WMS officiel GEBCO, couche ombree `GEBCO_LATEST`, reprojetee sur la grille UTM 40S : <https://wms.gebco.net/mapserv>. Le service utilise ici GEBCO 2024; citation complete dans `THIRD-PARTY-NOTICES.md`.
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

Le fichier [sites/cap-la-houssaye.json](sites/cap-la-houssaye.json) contient tous les parametres propres au site et les chemins des sorties canoniques.

## Etapes executees

1. Le script ouvre l'index du secteur HYSCORES et identifie le GeoTIFF bathymetrique numerique, pas le JPEG2000 colore.
2. `gdal_translate` lit uniquement `context_bbox_utm40s` dans le GeoTIFF Ifremer de 2,5 Go grace a `/vsicurl/`.
3. Les altitudes marines negatives sont converties en profondeurs positives. Les valeurs terrestres et nodata deviennent `-99999`.
4. Le RGE ALTI est telecharge sur exactement la meme emprise, a 0,5 m par defaut.
5. L'emprise 2D `focus_bbox_utm40s` est recadree localement depuis les deux MNT de contexte.
6. Les rasters sont eventuellement tournes par quarts de tour afin de placer la mer en haut des tableaux de calcul.
7. La cote a 0 m est interpolee en polygone continu. HYSCORES et RGE ALTI sont fusionnes sans combler les lacunes internes par une couleur arbitraire.
8. Les isobathes `-5`, `-10`, `-15` et `-20 m` sont extraites vectoriellement puis lissees. Toutes les lignes sont tracees avant les etiquettes afin qu'aucune isobathe ni cote ne puisse traverser le texte.
9. Le plan 2D utilise l'emprise de mise au point. La 3D utilise la grande emprise de contexte, mais conserve le cadrage final sur le site.
10. Les JPEG topo-bathymetriques recoivent une echelle de 50 m et une rose des vents recalculee selon la rotation.
11. La carte de localisation reutilise un RGE ALTI insulaire a 20 m, ajoute une grille latitude-longitude, une echelle de 20 km et le repere UTM propre au site.
12. `compose_site_plate.py` assemble les variantes orthophoto 2D/3D et la carte insulaire dans une planche haute resolution sur fond blanc. Le titre, l'auteur et les coordonnees WGS84 derivees du repere UTM sont produits depuis le JSON.

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
- `north_south_projection_scale` : amplification cartographique de l'axe nord-sud dans la vue 3D, sans modifier l'azimut de la camera.
- `horizontal_crop_fraction` : valeur de repli pour retirer la meme part sur les bords est et ouest de la vue 3D.
- `east_crop_fraction` et `west_crop_fraction` : parts retirees independamment de chaque cote de la vue 3D. Le plan 2D est recadre par son `focus_bbox_utm40s` afin de conserver une echelle metrique exacte.
- `south_crop_fraction` : part retiree du cote sud, soit en haut de la vue 3D depuis le nord. Le plan 2D est recadre au sud dans son `focus_bbox_utm40s`.
- `output_scale` : facteur de rendu natif des vecteurs, textes et annotations. Le fond raster est interpole avant leur trace, sans ajouter de detail spatial au-dela de la resolution des MNT sources.
- `plan_open_label_offsets_px` : corrections locales optionnelles des etiquettes principales, indexees par profondeur. Les valeurs `[dx, dy]` sont exprimees en pixels avant `output_scale`. Ne les utiliser qu'apres le placement automatique, pour sortir une etiquette d'une zone chargee. Au Cap La Houssaye, le `-10 m` est decale vers la gauche et le large.
- `orthophoto_enabled` : genere un second plan 2D hybride sans modifier le plan topographique original.
- `orthophoto_layer` et `orthophoto_resolution_m` : couche WMS IGN et resolution de l'orthophoto georeferencee utilisee uniquement dans le masque terrestre. La couche par defaut `HR.ORTHOIMAGERY.ORTHOPHOTOS` est diffusee a 20 cm.
- `orthophoto_3d_resolution_m` : resolution de la texture drapee sur le maillage altimetrique terrestre de la vue 3D. Une maille de 40 cm suffit avec l'echantillonnage actuel du relief.
- `bridge_decks` : correction locale opt-in d'un pont absent du modele de terrain nu. Chaque tablier est defini par `start_utm40s`, `end_utm40s`, `half_width_m` et `feather_m`. Le Cap La Houssaye en contient une pour le pont de la Ravine Patent Slip. Ne jamais recopier cette correction dans un autre site : laisser le parametre absent, sauf anomalie confirmee visuellement et corrigee au cas par cas.
- `locator_map_enabled`, `locator_bbox_utm40s`, `locator_marker_utm40s` et `locator_label` : activent la carte de localisation insulaire et placent le repere propre au site. Le fond RGE ALTI a 20 m est commun et reutilisable entre les sites.
- `locator_bathymetry_enabled`, `locator_gebco_layer`, `locator_gebco_request_width_px` et `locator_gebco_blur_px` : ajoutent uniquement en mer le relief ombre generalise de GEBCO et lissent sa maille de 15 secondes d'arc a l'echelle d'affichage. Cette couche insulaire sert a la localisation et ne remplace jamais HYSCORES dans les cartes detaillees ou pour la navigation.
- `plate_author`, `copyright_year` et `map_license` : signent discretement les sorties 2D et 3D originales ainsi que la planche, afin que l'attribution et la licence survivent a un recadrage d'une carte detaillee.

Chaque JPEG porte ses propres credits de donnees. Les cartes detaillees reprennent l'attribution HYSCORES imposee, Litto3D et IGN RGE ALTI; les variantes hybrides ajoutent l'orthophoto IGN et sa campagne. La carte insulaire cite IGN RGE ALTI pour la terre et la reference GEBCO 2024 complete pour la mer. La planche reprend la liste complete.

## Licences et droits de reutilisation

- Les scripts sont sous licence MIT.
- Les cartes derivees de HYSCORES sont sous CC BY-NC-SA 4.0 pour respecter la clause `ShareAlike` de la source. Ne pas les marquer `CC BY-NC-ND` : la clause `NoDerivatives` ajouterait une restriction incompatible avec HYSCORES.
- Les donnees tierces ne sont pas relicenciees par le projet. Le detail des licences, dates, citations et avertissements se trouve dans `THIRD-PARTY-NOTICES.md`.
- La metadonnee HYSCORES ne donne pas de numero de version de sa licence CC BY-NC-SA. Avant une publication publique a fort enjeu, demander confirmation de la version a l'Ifremer; le passage a CC BY-NC-SA 4.0 suit ici la regle Creative Commons autorisant une version ulterieure pour les sources BY-NC-SA 2.0 ou suivantes.

Les variantes orthophoto sont des sorties supplementaires. En 2D, la texture remplace le fond topographique uniquement a l'interieur du masque terrestre defini par la cote 0 m. En 3D, elle est drapee sur les altitudes lissees du RGE ALTI puis soumise au meme ombrage que le relief colore. La mer et les isobathes restent issues exclusivement du modele bathymetrique.
- `coast_frame_fraction` : hauteur de la cote dans l'image 3D, de 0 en haut a 1 en bas.
- `vertical_exaggeration` : amplification verticale du relief.
- `topography_resolution_m` : resolution demandee au WMS IGN. La requete est refusee au-dela de 5 000 pixels sur un axe.

Lorsque `north_south_projection_scale` differe de `1`, la barre metrique de la vue 3D reste exacte sur l'axe est-ouest uniquement. Le plan 2D demeure la reference metrique dans toutes les directions.

## Controle qualite obligatoire

Avant de retenir une figure :

1. Verifier que la cote noire suit la jonction terre-mer sans marches ni polygones de remplissage.
2. Verifier que les isobathes ne s'arretent pas au milieu de la surface visible. Si elles touchent le bord du raster source, agrandir le contexte au lieu de les prolonger graphiquement.
3. Verifier que le bord du MNT de contexte est hors image 3D. Une bande, des pointes miroir ou un faux ciel indiquent une marge insuffisante.
4. Comparer la rose des vents a une orthophoto ou a Google Maps.
5. Verifier la barre de 50 m a partir de la taille de pixel du GeoTIFF.
6. Inspecter le rendu final en pleine resolution, en particulier les tombants, les etiquettes et le bas de l'image.
7. Verifier que les etiquettes sont au-dessus de toutes les lignes et qu'aucune isobathe, cote ou annotation ne traverse leur texte. Utiliser un decalage local seulement si le placement automatique reste charge.
8. Sur la carte de localisation, verifier que le repere tombe sur le bon segment de littoral et que les coordonnees ne se chevauchent pas.
9. Verifier que chaque sortie conserve sa signature, sa licence et les credits des donnees effectivement visibles.

## Fichiers du pipeline

- `generate_reunion_topobathy.py` : acquisition, cache, recadrage et orchestration.
- `render_fused_relief.py` : fusion, lissage, isobathes et rendus 2D/3D.
- `sites/*.json` : parametres reproductibles de chaque site.
- `compose_site_plate.py` : composition reproductible des trois cartes et conversion du repere UTM en sous-titre GPS.
- `.tmp/bathy-renders/` : sources et extraits regenerables, non destines a etre versionnes.
- `outputs/` : figures finales.
