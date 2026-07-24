# Plans des sites de plongée à La Réunion

Site de partage des plans topo-bathymétriques de sites de plongée à La Réunion.
Un visualiseur unique réunit les plans 2D, les perspectives 3D et les reliefs
interactifs. Il s’ouvre sur la perspective 3D avec orthophoto ; le choix du fond
ne duplique ni la carte affichée ni la géométrie interactive.

Le site reste dans le dépôt des cartes afin que les nouveaux sites, les crédits
et les rendus web dérivent des mêmes configurations. La navigation, la carte de
situation et les téléchargements sont entièrement alimentés par le manifeste
généré.

## Développement

Prérequis : Node.js `>=22.13.0`.

```bash
npm install
npm run dev
npm test
```

## Ressources cartographiques

Les images responsives et les planches téléchargeables sont générées depuis les
sorties canoniques du dépôt :

```bash
../.venv/bin/python scripts/build_map_assets.py
```

Les reliefs interactifs sont générés par le pipeline cartographique sous
`../outputs/interactive-terrain/`. Le site ne recalcule ni leur géométrie, ni
leurs textures, ni leur caméra. Il copie le paquet canonique après vérification
des tailles et empreintes SHA-256 :

```bash
../.venv/bin/python scripts/sync_interactive_terrain.py
```

Chaque relief partage une seule géométrie entre les textures Topographie et
Orthophoto. La caméra orthographique initiale reprend l’azimut et la pente
visuelle de la perspective imprimable, depuis le large vers le récif ; la
rotation horizontale reste libre sur 360°.

Les fichiers web dérivés sont versionnés sous `public/maps/` et
`public/terrain/`. Les GeoTIFF sources restent locaux et ne sont jamais publiés.

## Publication

La configuration Sites se trouve dans `.openai/hosting.json`. Le build vinext
produit une application compatible Cloudflare Workers :

```bash
npm run build
```

Le déploiement canonique utilise l’adresse
<https://plans-sites-plongee-reunion.m-foll.chatgpt.site>. L’ancien projet
<https://reliefs-ouest-reunion.m-foll.chatgpt.site> reste en ligne séparément ;
sa configuration est conservée dans le commit `b9bca34`.
