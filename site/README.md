# Reliefs de l’Ouest

Site éditorial de l’atlas topo-bathymétrique de la côte ouest de La Réunion.
Il réunit les plans 2D, les perspectives 3D, les planches imprimables et un
explorateur de relief interactif pour Cap La Houssaye, Boucan Canot et la Passe
de l’Hermitage.

Le site reste dans le dépôt des cartes afin que les nouveaux sites, les crédits
et les rendus web dérivent des mêmes configurations.

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
Topographie / Orthophoto change uniquement la texture :

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
