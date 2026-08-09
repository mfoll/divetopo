# Workflow topo-bathymétrique du Var Est

Var Est couvre l’Estérel, Saint-Raphaël, Le Dramont, Anthéor et Le Trayas.
Cette région est autonome : ses configurations, sorties, manifestes et sa route
`/var-est` n’appartiennent pas à PACA.

## Périmètre v1.4

La première vague contient exactement cinq sites publiés : Les Pyramides, Sec
de l’Île d’Or, Arche du Dramont, Cathédrale du Trayas et Le Village. Leurs
configurations portent `region: var-est` et `web.published: true`; les
manifestes régional et interactif contiennent ces cinq sites, sans entrée « en
préparation ».

Sec des Suisses / Cigales, La Vitrine, Péniches d’Anthéor et Lion de Mer restent
différés et sont absents de cette livraison.

## Sources, sorties et construction

- CRS : RGF93 v1 / Lambert-93 (`EPSG:2154`).
- Bathymétrie et élévation : Shom–IGN Litto3D PACA 2015, MNT 1 m, IGN69.
- Imagerie : IGN BD ORTHO, date déclarée dans chaque configuration.
- Carte régionale : EMODnet Bathymetry DTM 2024, Litto3D près du littoral,
  GEBCO 2024 en repli NoData, RGE ALTI à terre et masque terre-mer officiel.

Les configurations vivent dans `regions/var-est/sites/`, les sorties
canoniques dans `regions/var-est/outputs/`, les paquets interactifs dans
`regions/var-est/outputs/interactive-terrain/` et les dérivés publiables dans
`apps/web/public/maps/var-est/`.

Chaque site fournit les six actifs natifs attendus : deux plans 2D, deux vues
3D statiques et deux planches 5400 × 3250, ainsi qu’un paquet interactif de
sept fichiers et ses dérivés Web. Les vues dynamiques sont capturées depuis la
fiche réelle, puis indexées avec tailles et SHA-256.

Commandes reproductibles, avec le runtime local approuvé :

```text
/Users/follm/home-projects/divetopo/.venv/bin/python apps/web/scripts/build_interactive_terrain_manifest.py var-est
/Users/follm/home-projects/divetopo/.venv/bin/python apps/web/scripts/build_regional_map_assets.py var-est
/Users/follm/home-projects/divetopo/.venv/bin/python apps/web/scripts/sync_interactive_terrain.py
```

Les points géographiques proches restent non interactifs. Les cartouches
nominatifs, le clavier et le sélecteur sont les cibles d’ouverture afin de ne
jamais associer silencieusement un clic au mauvais site.

## Gate de livraison

Avant commit, inspecter les six actifs de chaque site et la carte régionale en
pleine définition, mesurer les cartouches à 1280 × 720 et 390 × 844, vérifier
les thèmes clair/sombre, les routes, le sélecteur et les terrains, puis lancer
le build, les suites Python/Web et le lint. Le commit reste local : aucun push,
release ou déploiement n’est autorisé par ce workflow.
