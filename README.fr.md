[English](README.md) · [**Français**](README.fr.md)

# Plans topo-bathymétriques de sites de plongée à La Réunion

> [!IMPORTANT]
> Pour consulter les cartes, explorer les reliefs 3D interactifs et télécharger les plans originaux en haute définition ou les planches imprimables, utilisez **[Topo Réunion](https://reunion.divetopo.com)**.

[![Animation du relief 3D interactif du Cap La Houssaye, avec couleurs bathymétriques, vue aérienne et isobathes](.github/assets/cap-la-houssaye-interactive-3d.gif)](https://reunion.divetopo.com)

## Pourquoi ce projet existe

En préparant un voyage à La Réunion, j'ai trouvé étonnamment difficile de
trouver des plans détaillés de ses sites de plongée. En poursuivant mes
recherches, je me suis rendu compte que des données bathymétriques,
topographiques et aériennes publiques existaient déjà, mais qu'elles n'étaient
pas faciles à consulter ensemble.

J'ai donc téléchargé et assemblé ces jeux de données pour produire des plans
2D, des perspectives 3D statiques, des reliefs interactifs et des planches
imprimables cohérents pour une petite sélection non exhaustive de sites. Ce
dépôt constitue la référence technique de ce travail : il contient le code
source, les configurations par site, la documentation du workflow et les
sorties canoniques générées. Le site web est l'interface publique pour consulter
et télécharger les cartes.

> [!NOTE]
> Le code et les sites DiveTopo ont été entièrement générés par IA, sous direction humaine, avec des itérations de contrôle visuel et une validation par rapport aux données sources. Les données géographiques elles-mêmes proviennent des sources institutionnelles publiques indiquées ci-dessous.

## Sources des données

| Utilisation | Source | Rôle dans ce projet |
|---|---|---|
| Relief détaillé des fonds marins | [Ifremer HYSCORES 2015](https://www.data.gouv.fr/datasets/mnt-bathymetrique-a-haute-resolution-des-fonds-marins-des-zones-recifales-de-la-cote-ouest-de-lile-de-la-reunion-2015) | Bathymétrie haute résolution des secteurs récifaux de la côte ouest, y compris les compléments Litto3D distribués dans le produit HYSCORES |
| Altitude terrestre | [IGN RGE ALTI](https://cartes.gouv.fr/rechercher-une-donnee/dataset/IGNF_RGE-ALTI) | Modèle numérique de terrain de la partie terrestre |
| Imagerie aérienne | [IGN BD ORTHO](https://cartes.gouv.fr/rechercher-une-donnee/dataset/IGNF_BD-ORTHO) | Imagerie haute résolution géoréférencée drapée sur la terre et, lorsque cela est configuré, sur les faibles profondeurs |
| Contexte régional | [GEBCO 2024](https://www.gebco.net/data-products-gridded-bathymetry-data/gebco2024-grid) | Relief régional des fonds marins pour la carte insulaire et la sélection des sites de la côte ouest |

Tous les traitements détaillés utilisent WGS 84 / UTM zone 40S
(`EPSG:32740`). HYSCORES ne couvre pas toute l'île : étendre le projet au-delà
de ses quatre secteurs sources nécessite donc une autre source bathymétrique
numérique.

## Ce que produit le pipeline

Chaque site est défini par une configuration JSON indépendante et produit :

- un plan 2D nord en haut ;
- une perspective 3D oblique statique ;
- des variantes topographique et en vue aérienne ;
- une carte de localisation insulaire ;
- deux planches imprimables en haute définition ;
- un paquet compact de relief 3D interactif consommé par le site web.

Les sept sites actuels utilisent les mêmes dimensions pour les cartes statiques
(`2474 × 1712 px`), ainsi que les mêmes épaisseurs apparentes de traits et la
même échelle d'étiquettes. Les planches imprimables mesurent
`5400 × 3250 px`. Dans la variante en vue aérienne, l'image reste opaque
jusqu'à `−1,5 m`, s'efface progressivement jusqu'à `−2 m`, puis laisse place à
la palette bathymétrique. La variante topographique conserve le trait de côte à
0 m.

Le moteur fusionne les modèles d'altitude marin et terrestre, interpole le trait
de côte à 0 m, lisse le bruit de cellule et extrait les isobathes tous les 5 m.
Les lacunes raster restent non comblées par défaut. Une limite marine profonde
documentée peut être complétée localement par un plateau uniforme à la
profondeur maximale configurée, sans inventer de relief ni de courbes
intermédiaires.

## Sites actuellement inclus

| Site | Commune | Configuration |
|---|---|---|
| Cap La Houssaye | Saint-Paul | [`cap-la-houssaye.json`](sites/cap-la-houssaye.json) |
| Boucan Canot | Saint-Paul | [`boucan-canot.json`](sites/boucan-canot.json) |
| Passe de l'Hermitage | Saint-Paul | [`passe-hermitage.json`](sites/passe-hermitage.json) |
| Cap Homard | Saint-Paul | [`cap-homard.json`](sites/cap-homard.json) |
| Pointe au Sel | Saint-Leu | [`pointe-au-sel-sec-jaune.json`](sites/pointe-au-sel-sec-jaune.json) |
| Pont Rouge | Saint-Leu | [`pont-rouge-la-tortue.json`](sites/pont-rouge-la-tortue.json) |
| Plage du Cimetière | Saint-Leu | [`plage-cimetiere-saint-leu.json`](sites/plage-cimetiere-saint-leu.json) |

## Exemple représentatif : Cap La Houssaye

Le Cap La Houssaye utilise la transition commune `−1,5/−2 m` pour la vue
aérienne, tout en conservant une correction locale du pont dans le modèle 3D.
Sa vue oblique statique utilise une inclinaison de `0,29`, une amplification
dans l'axe de vue de `1,35` et place le trait de côte à 54 % de la hauteur de
l'image. Ce cadrage montre les deux pointes sans consacrer trop d'espace au fond
comparativement uniforme du large.

| Plan 2D | Perspective 3D statique |
|---|---|
| [![Plan 2D du Cap La Houssaye en vue aérienne](site/public/maps/cap-la-houssaye/2d-orthophoto-960.webp)](https://reunion.divetopo.com) | [![Perspective 3D oblique statique du Cap La Houssaye en vue aérienne](site/public/maps/cap-la-houssaye/3d-orthophoto-960.webp)](https://reunion.divetopo.com) |

### Planche imprimable

[![Planche imprimable en haute définition du Cap La Houssaye](site/public/maps/cap-la-houssaye/planche-orthophoto-1800.webp)](https://reunion.divetopo.com)

Les images ci-dessus sont des aperçus légers. Les boutons de téléchargement de
Topo Réunion fournissent les JPEG statiques originaux et les planches
`5400 × 3250 px`.

## Relief interactif et architecture du site

Le relief interactif appartient au pipeline cartographique et non au générateur
du site web. La commande canonique est :

```bash
.venv/bin/python generate_interactive_terrain.py
```

Chaque paquet de site contient un champ d'altitude 16 bits, un masque de
validité, un masque de provenance des isobathes, deux textures et des
métadonnées. Le format et la frontière entre le pipeline cartographique et le
site sont documentés dans
[INTERACTIVE-TERRAIN.md](INTERACTIVE-TERRAIN.md).

Le site se trouve sous `site/`. Il consomme le paquet canonique sans recalculer
sa géométrie, ses textures ni sa caméra. Une géométrie unique est partagée entre
les variantes Topographie et Vue aérienne ; changer de fond ne remplace que la
texture. La caméra initiale suit la vue 3D statique, depuis le large vers la
côte, tandis que la rotation horizontale reste libre sur 360 degrés.

Les deux sites publics proposent des adresses stables en français et en anglais
sous `/fr` et `/en`. Topo Réunion propose également une adresse indexable pour
chaque site publié, par exemple `/fr/sites/cap-la-houssaye` et
`/en/sites/cap-la-houssaye`. Ces pages réutilisent les mêmes cartes
responsives, téléchargements et paquets de terrain interactif ; elles ne
dupliquent ni ne recalculent les ressources cartographiques. Les adresses
racines sélectionnent la langue enregistrée ou préférée, puis redirigent vers
sa route canonique.

Le champ d'altitude utilise au maximum `513` sommets sur son axe le plus long.
Les textures WebGL utilisent au maximum `2048 px` sur leur plus grand côté. Les
isobathes sont calculées dans des plans parfaitement horizontaux tous les 5 m,
reprennent la couleur correspondante de la palette bathymétrique et peuvent être
masquées dans le visualiseur.

Les ressources responsives du site sont des dérivés reproductibles des sorties
canoniques :

```bash
cd site
../.venv/bin/python scripts/build_map_assets.py
../.venv/bin/python scripts/sync_interactive_terrain.py
npm test
```

Les données GeoTIFF sources restent dans le cache local et ne sont jamais
publiées.

Les deux applications Web sont déployées indépendamment. GitHub reste la source
canonique, mais un push ne met pas automatiquement à jour les sites hébergés.
La séquence exacte de publication et le contrôle d'équivalence des arbres sont
documentés en anglais dans [DEPLOYMENT.md](DEPLOYMENT.md).

## Installation sur macOS

Homebrew est requis. Le script d'installation installe Python et GDAL, puis crée
l'environnement local :

```bash
./bootstrap_macos.sh
```

L'environnement de référence enregistré pour les sept sites actuels est
Python 3.14, GDAL 3.13.1, NumPy 2.5.1 et Pillow 12.3.0. NumPy et Pillow sont
épinglés dans `requirements.txt` ; Python et GDAL proviennent de Homebrew. Le
contrôle préalable exige également les polices macOS Arial, Arial Bold et
Avenir Next utilisées dans les cartes et les planches.

## Reproduire les cartes

Télécharger ou actualiser les données sources et régénérer un site complet :

```bash
.venv/bin/python generate_reunion_topobathy.py sites/cap-la-houssaye.json --refresh
```

Réutiliser le cache validé et régénérer uniquement les images :

```bash
.venv/bin/python generate_reunion_topobathy.py sites/cap-la-houssaye.json --render-only
```

Valider la configuration, les sources déclarées et le cache sans produire
d'image :

```bash
.venv/bin/python generate_reunion_topobathy.py sites/cap-la-houssaye.json --check
```

Recalculer uniquement les deux perspectives 3D statiques :

```bash
.venv/bin/python generate_reunion_topobathy.py sites/cap-la-houssaye.json --render-only --relief-only
```

Assembler les deux planches imprimables :

```bash
.venv/bin/python compose_site_plate.py sites/cap-la-houssaye.json
```

`--refresh`, `--render-only` et `--check` sont mutuellement exclusifs. Utilisez
`--land-style orthophoto` ou `--land-style topography` pour ne produire qu'un
style de terrain. Les données sources, les extraits reproductibles et chaque
`<slug>-cache-manifest.json` restent sous `.tmp/bathy-renders/` et ne sont pas
versionnés.

Les perspectives 3D statiques utilisent des normales métriques avec
exagération verticale, une lumière hémisphérique froide et une lumière
directionnelle chaude venant du nord-est. L'éclairage est calculé dans un espace
colorimétrique linéaire avec une exposition commune de `1,55`, avant le dessin
des isobathes, du trait de côte et des annotations.

## Réutiliser le pipeline pour un autre site

Copiez une configuration de `sites/`, puis remplacez le raster HYSCORES exact,
les emprises UTM 40S, les résolutions, la date de prise de vue aérienne, le
traitement du trait de côte et les paramètres de caméra. Ne recopiez pas une
date source ou une correction locale depuis un autre site sans la vérifier. Le
plan 2D reste nord en haut ; la vue 3D peut utiliser n'importe quel azimut et
recalcule automatiquement son compas.

La procédure de production complète, chaque paramètre et les contrôles qualité
sont documentés dans [WORKFLOW.md](WORKFLOW.md). Le déploiement des ressources
Web obtenues suit [DEPLOYMENT.md](DEPLOYMENT.md).

## Licences et sécurité

- Code Python et scripts : [MIT](LICENSE).
- Cartes et figures sous `outputs/` : [CC BY-NC-SA 4.0](LICENSE-MAPS.md), sous
  réserve des droits attachés aux données sources.
- Licences des sources, attributions obligatoires, versions des jeux de données
  et avertissements : [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).

Les cartes aident à lire le relief et à s'orienter de manière générale. Elles
n'établissent ni l'accès, ni l'autorisation, ni les conditions présentes, ni la
sécurité. Elles ne doivent pas être utilisées pour la navigation ou comme seule
base d'une décision engageant la sécurité en mer.
