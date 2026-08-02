[English](README.md) · [**Français**](README.fr.md)

# DiveTopo

> [!IMPORTANT]
> Consultez les cartes, les reliefs 3D interactifs et les fichiers originaux en haute définition des collections régionales de DiveTopo sur **[divetopo.com](https://divetopo.com)**. La première collection publiée est **[La Réunion](https://divetopo.com/reunion)**.

[![Animation du relief 3D interactif du Cap La Houssaye, avec couleurs bathymétriques, vue aérienne et isobathes](.github/assets/cap-la-houssaye-interactive-3d.gif)](https://divetopo.com/reunion)

## Pourquoi ce projet existe

En préparant un voyage à La Réunion, j'ai eu beaucoup de mal à trouver des
plans détaillés de ses sites de plongée. En cherchant, je me suis rendu compte
que des données bathymétriques, topographiques et aériennes publiques
existaient, mais qu'elles n'étaient pas faciles à consulter ensemble. Cette
première collection régionale est devenue le point de départ d'un projet
réutilisable pour plusieurs régions.

J'ai donc téléchargé et assemblé ces données pour produire des plans 2D, des
perspectives 3D statiques, des reliefs interactifs et des planches imprimables
cohérents pour une petite sélection non exhaustive de sites. DiveTopo sépare
désormais le moteur cartographique et l'application Web réutilisables des
sources et configurations propres à chaque région.

> [!NOTE]
> Le code, le site et sa présentation originale ont été entièrement générés par IA, sous direction humaine, avec des itérations visuelles et une validation par rapport aux données sources. Chaque région documente ses propres sources géographiques, licences et attributions.

## Sources de données et attributions par région

Les jeux de données, la couverture, les projections, les licences et les
attributions requises sont définis par région. La collection réunionnaise
ci-dessous est un exemple régional, pas une liste de sources ni une exigence de
traitement universelle pour les autres régions.

### La Réunion

| Utilisation | Source | Rôle |
|---|---|---|
| Relief sous-marin détaillé | [Ifremer HYSCORES 2015](https://www.data.gouv.fr/datasets/mnt-bathymetrique-a-haute-resolution-des-fonds-marins-des-zones-recifales-de-la-cote-ouest-de-lile-de-la-reunion-2015) | Bathymétrie haute résolution des secteurs récifaux de la côte ouest, avec les compléments Litto3D distribués avec HYSCORES |
| Relief terrestre | [IGN RGE ALTI](https://cartes.gouv.fr/rechercher-une-donnee/dataset/IGNF_RGE-ALTI) | Modèle numérique du terrain émergé |
| Vue aérienne | [IGN BD ORTHO](https://cartes.gouv.fr/rechercher-une-donnee/dataset/IGNF_BD-ORTHO) | Imagerie géoréférencée appliquée au terrain et, lorsque configuré, aux petits fonds |
| Contexte régional | [GEBCO 2024](https://www.gebco.net/data-products-gridded-bathymetry-data/gebco2024-grid) | Relief sous-marin généralisé de la carte de localisation et de sélection |

Les traitements détaillés utilisent WGS 84 / UTM zone 40S (`EPSG:32740`).
HYSCORES ne couvre pas toute l'île : un site situé hors de ses quatre secteurs
nécessite une autre source bathymétrique numérique.

## Résultats produits

Chaque configuration de site peut produire :

- un plan 2D orienté nord ;
- une perspective 3D oblique statique ;
- des variantes topographique et vue aérienne ;
- une carte de localisation régionale ;
- deux planches imprimables en haute définition ;
- un paquet de relief 3D interactif compact pour le site Web.

Les dimensions, les seuils de transition et l'intervalle des isobathes sont
définis par région. Les sept sites réunionnais utilisent des plans statiques de `2474 × 1712 px`
et des planches de `5400 × 3250 px`. La vue aérienne reste opaque jusqu'à
`−1,5 m`, disparaît progressivement entre `−1,5 m` et `−2 m`, puis laisse
entièrement place à la palette bathymétrique. Les isobathes sont calculées tous
les 5 m.

## Inventaires régionaux

Chaque région conserve son identité, son inventaire de sites et ses sorties
canoniques sous `regions/<slug>/`. L'inventaire réunionnais ci-dessous est un
exemple concret ; les autres régions doivent être lues dans leurs propres
configurations et, lorsqu'elles existent, leurs notices régionales.

### La Réunion

| Site | Commune | Configuration |
|---|---|---|
| Cap La Houssaye | Saint-Paul | [`cap-la-houssaye.json`](regions/reunion/sites/cap-la-houssaye.json) |
| Boucan Canot | Saint-Paul | [`boucan-canot.json`](regions/reunion/sites/boucan-canot.json) |
| Passe de l'Hermitage | Saint-Paul | [`passe-hermitage.json`](regions/reunion/sites/passe-hermitage.json) |
| Cap Homard | Saint-Paul | [`cap-homard.json`](regions/reunion/sites/cap-homard.json) |
| Pointe au Sel | Saint-Leu | [`pointe-au-sel-sec-jaune.json`](regions/reunion/sites/pointe-au-sel-sec-jaune.json) |
| Pont Rouge | Saint-Leu | [`pont-rouge-la-tortue.json`](regions/reunion/sites/pont-rouge-la-tortue.json) |
| Plage du Cimetière | Saint-Leu | [`plage-cimetiere-saint-leu.json`](regions/reunion/sites/plage-cimetiere-saint-leu.json) |

## Exemple : Cap La Houssaye

| Plan 2D | Perspective 3D statique |
|---|---|
| [![Plan 2D du Cap La Houssaye en vue aérienne](apps/web/public/maps/cap-la-houssaye/2d-orthophoto-960.webp)](https://divetopo.com/reunion) | [![Perspective 3D statique du Cap La Houssaye en vue aérienne](apps/web/public/maps/cap-la-houssaye/3d-orthophoto-960.webp)](https://divetopo.com/reunion) |

### Planche imprimable

[![Planche imprimable du Cap La Houssaye](apps/web/public/maps/cap-la-houssaye/planche-orthophoto-1800.webp)](https://divetopo.com/reunion)

Ces aperçus sont allégés. Les boutons du site donnent accès aux JPEG et
planches canoniques en pleine résolution.

## Architecture du dépôt

```text
apps/web/                  application unique publiée sur divetopo.com
cartography/               moteur partagé de rendu, composition et export
cartography/regions/       acquisition et orchestration propres aux régions
regions/<slug>/region.json identité, projection, sources et inventaire régional
regions/<slug>/sites/      configurations reproductibles des sites
regions/<slug>/outputs/    résultats cartographiques canoniques
tests/                     tests partagés et contrats régionaux
```

Le site Web ne génère jamais le relief. Il copie des dérivés contrôlés depuis
les résultats régionaux canoniques. Le format interactif est documenté dans
[INTERACTIVE-TERRAIN.md](INTERACTIVE-TERRAIN.md).

## Workflows régionaux

Utilisez le workflow du répertoire de la région cible pour l'acquisition, les
paramètres de rendu et les contrôles d'acceptation propres aux sources. Les
commandes ci-dessous montrent l'implémentation réunionnaise actuelle.

```bash
./bootstrap_macos.sh

.venv/bin/python -m cartography.regions.reunion \
  regions/reunion/sites/cap-la-houssaye.json --check

.venv/bin/python -m cartography.regions.reunion \
  regions/reunion/sites/cap-la-houssaye.json --refresh

.venv/bin/python -m cartography.plate \
  regions/reunion/sites/cap-la-houssaye.json

.venv/bin/python -m cartography.interactive
```

Les règles communes sont dans [WORKFLOW.md](WORKFLOW.md). Les paramètres,
contrôles de rendu et porte d'acceptation propres à La Réunion sont dans
[regions/reunion/WORKFLOW.md](regions/reunion/WORKFLOW.md).

## Site Web et publication

`apps/web/` publie la page d'accueil générale et toutes les régions dans une
seule application. Chaque région fournit sa propre route et son inventaire de
sites. La collection réunionnaise actuelle est accessible sous `/reunion`,
avec ses routes françaises, anglaises et celles de chaque site. GitHub reste la
source canonique, mais un push ne déploie pas automatiquement le site. Le
processus est décrit dans [DEPLOYMENT.md](DEPLOYMENT.md).

## Licences et sécurité

- Logiciel original : [MIT](LICENSE).
- Cartes et figures originales : [CC BY-NC-SA 4.0](LICENSE-MAPS.md), dans la
  mesure des droits détenus par Matthieu Foll sur ces contributions originales.
- Licences régionales des jeux de données, attributions obligatoires et
  avertissements : [notices tierces](THIRD-PARTY-NOTICES.md) et toute notice
  applicable sous `regions/<slug>/`.

Le site et son contenu sont gratuits et sans publicité. Les cartes facilitent
la lecture du relief et l'orientation générale. Elles ne démontrent ni l'accès,
ni l'autorisation, ni les conditions présentes, ni la sécurité, et ne doivent
pas servir à la navigation ou de seule base à une décision de sécurité en mer.
