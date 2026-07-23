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
12. `compose_site_plate.py` assemble la carte insulaire et les vues detaillees dans deux planches haute resolution sur fond blanc : une variante avec orthophoto terrestre et une variante sans image satellite, utilisant le relief topographique colore. Le bandeau superieur utilise un cartouche typographique centre : nom complet du site sur une seule ligne en sans-serif epaisse uniforme, lieu encadre par deux filets, puis latitude et longitude en degres, minutes et secondes, agrandies en deux blocs separes par un filet vertical. Un second filet separe le cartouche de la carte insulaire. Les vues 2D et 3D occupent ensemble la rangee inferieure. Les panneaux sont plats, sans ombre, avec un filet noir discret.

## Ajouter un site

Copier le JSON existant vers `sites/<slug>.json`, puis renseigner :

- `slug` et `title` ;
- `hyscores_directory`, choisi parmi les quatre secteurs officiels ;
- `focus_bbox_utm40s` : rectangle serre contenant le site a lire en 2D ;
- `context_bbox_utm40s` : rectangle plus grand contenant integralement le precedent ;
- `rotation_k` : rotation `numpy.rot90` reservee au raster de travail 3D ; le plan 2D reste toujours nord en haut ;
- les parametres de camera et, si necessaire, les chemins de sortie.

Correspondance de `rotation_k` :

| Mer dans le raster UTM initial | `rotation_k` |
|---|---:|
| nord | 0 |
| est | 1 |
| sud | 2 |
| ouest | 3 |

La rose des vents 2D indique toujours le nord en haut. La rose de la vue depuis le large est adaptee automatiquement a l'azimut de camera.

Pour la 3D, prevoir dans `context_bbox_utm40s` environ 300 a 400 m de donnees reelles supplementaires vers le large, 100 a 200 m sur chaque cote et 200 a 300 m vers l'interieur. Cette marge doit etre augmentee si le point de vue est abaisse.

## Parametres de rendu

- `max_depth_m` : profondeur maximale de la palette et du relief affiche. Les isobathes sont generees automatiquement tous les 5 m jusqu'a cette valeur; Boucan utilise 30 m.
- `context_topography_resolution_m` : resolution optionnelle du MNT de la grande emprise 3D lorsqu'elle doit etre moins fine que `topography_resolution_m` pour respecter les limites du service IGN. L'Hermitage utilise `0,8 m` sur son contexte agrandi, sans modifier le plan 2D.
- `coast_mode` : `profile` conserve la cote simple historique, decrite par une traversee terre/eau par colonne; `mask` extrait un masque terrestre bidimensionnel pour les baies, ilots, pointes et piscines naturelles. Utiliser `mask` lorsque la cote n'est pas monotone dans l'orientation choisie. En mode `mask`, le remplissage terrestre et le trait 0 m proviennent de la meme surface continue lissee : le trait suit exactement son isovaleur 0,5 et aucun pixel terrestre ne peut depasser en mer.
- `view_bearing_deg` : azimut regarde par la camera 3D, en degres horaires depuis le nord. S'il est absent, la camera regarde vers le bas du raster oriente; `135` correspond au sud-est. Le maillage, ses textures et ses vecteurs sont tournes par interpolation avant projection, et non comme une simple image apres rendu.
- `view_crop_width_m` et `view_crop_depth_m` : emprise metrique conservee apres la rotation arbitraire du maillage. Extraire un contexte plus large que ce cadre permet de garder les bords du GeoTIFF et les isobathes tronquees hors champ sans augmenter inutilement le nombre de facettes rendues.
- La projection 3D calcule automatiquement son zoom transversal a partir de la largeur de `focus_bbox_utm40s`. La 2D et la 3D ont ainsi une echelle proche, et identique sur l'axe de la barre de 50 m lorsque `view_visible_width_m` n'est pas surcharge. Cette egalite n'est pas un objectif absolu : `view_visible_width_m` permet de cadrer la perspective sur le relief utile sans modifier l'emprise 2D. Boucan utilise `580 m` et l'Hermitage `650 m`.
- `camera_tilt` : angle apparent de la grille. Une valeur plus faible abaisse le point de vue.
- `north_south_projection_scale` : amplification cartographique de l'axe nord-sud dans la vue 3D, sans modifier l'azimut de la camera.
- `horizontal_crop_fraction` : valeur de repli pour retirer la meme part sur les bords est et ouest de la vue 3D.
- `east_crop_fraction` et `west_crop_fraction` : parts retirees independamment de chaque cote de la vue 3D. Le plan 2D est recadre par son `focus_bbox_utm40s` afin de conserver une echelle metrique exacte.
- `south_crop_fraction` : part retiree du cote sud, soit en haut de la vue 3D depuis le nord. Le plan 2D est recadre au sud dans son `focus_bbox_utm40s`.
- Une bande uniforme, un mur vertical ou des pixels etires en haut d'une vue 3D signalent d'abord la limite du maillage ou du GeoTIFF. Agrandir `context_bbox_utm40s`, puis `view_crop_depth_m`, afin de projeter des donnees reelles jusqu'au-dela du cadre. Ne pas masquer ce defaut avec `south_crop_fraction` ou `horizon_cleanup_fraction`.
- `output_scale` : facteur de rendu natif des vecteurs, textes et annotations. Le fond raster est interpole avant leur trace, sans ajouter de detail spatial au-dela de la resolution des MNT sources.
- `plan_output_scale` et `relief_output_scale` : facteurs optionnels distincts pour produire un rendu intermediaire haute resolution malgre les moteurs 2D et 3D differents.
- `map_style_scale` : facteur graphique commun exprime dans l'espace de sortie final. Le moteur compense automatiquement les resolutions intermediaires et le reechantillonnage final afin de conserver les memes epaisseurs d'isobathes, corps d'etiquettes, roses, barres d'echelle, sources et licences sur tous les sites et sur les vues 2D et 3D. Utiliser une meme valeur, actuellement `2.0`, dans toutes les configurations. La longueur de la barre de 50 m reste determinee par l'echelle metrique propre au cadrage.
- `final_output_size_px` : dimensions finales exactes communes aux cartes 2D et 3D. Les trois sites de reference utilisent `2474 x 1712 px`, apres un reechantillonnage Lanczos.
- Une translation du plan 2D se fait en translatant `focus_bbox_utm40s` sans changer sa largeur ni sa hauteur, puis en regenerant les trois rasters `focus_*`. Pour modifier aussi le format, recalculer largeur et hauteur avec le rapport final voulu avant de regenerer les rasters.
- `relief_suppressed_label_levels` : etiquettes d'isobathes a masquer uniquement sur la vue 3D, sans supprimer les lignes ni les donnees. A Boucan, `-30 m` est masque car sa ligne est hors cadrage perspectif. A l'Hermitage, l'etiquette reste visible depuis que le cadrage inclut clairement cette ligne.
- `land_sieve_threshold_px` : taille minimale, en pixels du MNT source, des composantes terrestres deconnectees conservees par le masque bidimensionnel. L'augmenter seulement pour retirer des micro-ilots artefactuels confirmes visuellement; la Passe de l'Hermitage utilise `10000`.
- `imagery_sea_full_depth_m` et `imagery_sea_max_depth_m` : bornes explicites de l'extension optionnelle de l'orthophoto dans un lagon peu profond. L'image est opaque jusqu'a la premiere profondeur puis fond progressivement jusqu'a devenir transparente a la seconde. `imagery_sea_depth_m` et `imagery_sea_feather_m` restent acceptes pour les anciennes configurations.
- `imagery_sea_smoothing_m` : pre-lissage spatial applique uniquement a la profondeur qui pilote le masque visuel; il ne modifie ni le relief ni les isobathes. A l'Hermitage et a Boucan, l'image reste complete jusqu'a `-1 m`, disparait a `-2 m` et le masque est pre-lisse sur 5 m. Lorsqu'une extension marine est active, ce masque de profondeur continu remplace la combinaison des masques terre/mer et evite les rectangles autour des piscines, plages ou ouvrages situes a 0 m.
- La palette bathymetrique utilise systematiquement `-2 m` comme zero chromatique rouge, correspondant a la fin du fondu orthophoto. Elle est ensuite recomprimee jusqu'a `max_depth_m` pour conserver la couleur profonde historique a la limite de chaque carte. Le premier fond integralement bathymetrique reste ainsi rouge au lieu de commencer directement dans l'orange.
- `view_center_offset_east_m` et `view_center_offset_north_m` : decalage geographique du centre du recadrage 3D avant projection. Les valeurs positives vont vers l'est et le nord. L'Hermitage utilise respectivement `140` et `240` pour rapprocher le cadrage de la passe et retirer du premier plan profond inutile, sans changer l'orientation de la camera. Son maillage projete couvre 3200 m de profondeur dans un contexte source de `3300 x 3600 m`; cette marge place la limite du raster terrestre hors image.
- `coastline_visible` et `orthophoto_coastline_visible` : affichage du trait vectoriel 0 m sur toutes les variantes ou seulement sur la variante orthophoto. Le masque et le cadrage continuent d'utiliser la cote meme si son trait n'est pas dessine. Par defaut, le trait est conserve sur les variantes topographiques et masque sur toutes les orthophotos; `orthophoto_coastline_visible: true` permettrait une exception explicite.
- `clip_rotated_outside` : rend invalides les coins situes hors du raster apres une rotation arbitraire. L'activer lorsque le contexte source est assez large pour contenir toute l'emprise tournee; cela evite de prolonger artificiellement les pixels de bord a l'horizon.
- `horizon_cleanup_fraction` : masque de dernier recours pour une frange d'horizon residuelle. Preferer d'abord un contexte plus large et `clip_rotated_outside`; laisser `0` lorsque ces mesures suffisent.
- `view_canvas_width_px` et `view_canvas_height_px` : dimensions logiques du canevas 3D avant `relief_output_scale`. Les choisir avec le meme rapport largeur/hauteur que `focus_bbox_utm40s`, en tenant compte du recadrage, afin que les panneaux aient la meme forme sans deformation.
- Le rapport du canevas restant apres `east_crop_fraction`, `west_crop_fraction` et `south_crop_fraction` doit correspondre a `final_output_size_px`. Le redimensionnement final conserve toujours un facteur uniforme et rogne seulement un eventuel excedent minimal; il n'etire jamais separement les axes X et Y. L'Hermitage utilise un canevas de `1237 x 1069 px`, qui devient `1237 x 856 px` apres son recadrage sud de 20 %, exactement au rapport `2474/1712`.
- `plan_open_label_offsets_px` : corrections locales optionnelles des etiquettes principales, indexees par profondeur. Les valeurs `[dx, dy]` sont exprimees en pixels avant `output_scale`. Ne les utiliser qu'apres le placement automatique, pour sortir une etiquette d'une zone chargee. Au Cap La Houssaye, le `-10 m` est decale vers la gauche et le large.
- `orthophoto_enabled` : genere un second plan 2D hybride sans modifier le plan topographique original.
- `orthophoto_layer` et `orthophoto_resolution_m` : couche WMS IGN et resolution de l'orthophoto georeferencee utilisee uniquement dans le masque terrestre. La couche par defaut `HR.ORTHOIMAGERY.ORTHOPHOTOS` est diffusee a 20 cm.
- `orthophoto_3d_resolution_m` : resolution de la texture drapee sur le maillage altimetrique terrestre de la vue 3D. Une maille de 40 cm suffit generalement; l'Hermitage utilise 80 cm afin que son contexte de `3300 x 3600 m` respecte la limite de 5000 pixels par axe du service IGN.
- `bridge_decks` : correction locale opt-in d'un pont absent du modele de terrain nu. Chaque tablier est defini par `start_utm40s`, `end_utm40s`, `half_width_m` et `feather_m`. Le Cap La Houssaye en contient une pour le pont de la Ravine Patent Slip. Ne jamais recopier cette correction dans un autre site : laisser le parametre absent, sauf anomalie confirmee visuellement et corrigee au cas par cas.
- `locator_map_enabled`, `locator_bbox_utm40s`, `locator_marker_utm40s` et `locator_label` : activent la carte de localisation insulaire et placent le repere propre au site. Le fond RGE ALTI a 20 m est commun et reutilisable entre les sites.
- `locator_bathymetry_enabled`, `locator_gebco_layer`, `locator_gebco_request_width_px` et `locator_gebco_blur_px` : ajoutent uniquement en mer le relief ombre generalise de GEBCO et lissent sa maille de 15 secondes d'arc a l'echelle d'affichage. Cette couche insulaire sert a la localisation et ne remplace jamais HYSCORES dans les cartes detaillees ou pour la navigation.
- `plate_author`, `copyright_year` et `map_license` : signent discretement les sorties 2D et 3D originales afin que l'attribution et la licence survivent a un recadrage d'une carte detaillee. La planche ne les repete pas dans son bandeau superieur.
- `paths.output_plate` et `paths.output_plate_topography` : sorties respectives de la planche orthophoto et de la planche topographique. La commande de composition genere les deux par defaut; `--land-style` limite la regeneration a une variante.
- `plate_canvas_width_px` et `plate_canvas_height_px` : dimensions optionnelles de la planche. Augmenter la hauteur lorsqu'un plan 2D presque carre doit rester a la meme largeur que la vue 3D sans remonter sur le cartouche.

Chaque JPEG porte ses propres credits de donnees. Les cartes detaillees reprennent l'attribution HYSCORES imposee, Litto3D et IGN RGE ALTI; les variantes hybrides ajoutent l'orthophoto IGN et sa campagne. La carte insulaire cite IGN RGE ALTI pour la terre et la reference GEBCO 2024 complete pour la mer. La planche ne duplique ni ces sources deja lisibles dans chaque panneau, ni l'auteur et la licence deja presents sur les vues 2D et 3D.

## Licences et droits de reutilisation

- Les scripts sont sous licence MIT.
- Les cartes derivees de HYSCORES sont sous CC BY-NC-SA 4.0 pour respecter la clause `ShareAlike` de la source. Ne pas les marquer `CC BY-NC-ND` : la clause `NoDerivatives` ajouterait une restriction incompatible avec HYSCORES.
- Les donnees tierces ne sont pas relicenciees par le projet. Le detail des licences, dates, citations et avertissements se trouve dans `THIRD-PARTY-NOTICES.md`.
- La metadonnee HYSCORES ne donne pas de numero de version de sa licence CC BY-NC-SA. Les cartes du projet sont publiees sous CC BY-NC-SA 4.0.

Les variantes orthophoto sont des sorties supplementaires. En 2D, la texture remplace le fond topographique a l'interieur du masque terrestre et, lorsqu'elle est configuree, dans la tranche marine peu profonde. En 3D, l'orthophoto pure est tournee, recadree et reechantillonnee en parallele du maillage. Une bande cotiere calculee par distance au masque terrestre est ensuite reecrite avec cette texture non contaminee avant la projection perspective. Cette etape evite que l'interpolation de la palette bathymetrique rouge produise un filet ou des pointes du cote terrestre. La mer profonde et les isobathes restent issues exclusivement du modele bathymetrique.
- Apres rotation et sur-echantillonnage du maillage 3D, le moteur reimpose aussi les domaines physiques `terre >= 0 m` et `mer <= 0 m`. Le masque binaire est tourne par interpolation bicubique puis reseuille pour rester aligne avec le littoral lisse. La correction repose sur les donnees raster et non sur un trait colore cache par-dessus le raccord.
- `coast_frame_fraction` : hauteur de la cote dans l'image 3D, de 0 en haut a 1 en bas. L'augmenter rapproche visuellement la camera de la cote en donnant moins de hauteur au large. L'Hermitage utilise `0,26`; le Cap utilise `0,54` car son relief utile est concentre pres des deux pointes et son large devient rapidement uniforme.
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
