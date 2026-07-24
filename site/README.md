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

Les reliefs interactifs partagent une seule géométrie par site. Le bouton
Topographie / Orthophoto change uniquement la texture. La caméra orthographique
initiale reprend l’azimut et la pente visuelle de la perspective imprimable,
depuis le large vers le récif ; la rotation horizontale reste libre sur 360° :

```bash
../.venv/bin/python ../export_web_terrain.py
```

Les fichiers web générés sont versionnés sous `public/maps/` et
`public/terrain/`. Les GeoTIFF sources restent locaux et ne sont jamais publiés.

## Publication

La configuration Sites se trouve dans `.openai/hosting.json`. Le build vinext
produit une application compatible Cloudflare Workers :

```bash
npm run build
```
