# Workflow topo-bathymétrique du Var Centre

Var Centre couvre Giens, Porquerolles et Port-Cros. La région est autonome :
son inventaire, ses configurations, ses sorties, ses manifestes et sa route
`/var-centre` n'appartiennent pas à la région PACA.

## Périmètre v1.4

La région contient désormais quatre sites publiés :

- Les Fourmigues (`les-fourmigues`);
- Sec de la Jeaune Garde (`sec-de-la-jeaune-garde`), dont l'emprise élargie
  couvre aussi l'ancien secteur publié comme Sec du Langoustier;
- Cap des Mèdes (`cap-des-medes`);
- La Gabinière (`la-gabiniere-port-cros`).

Les quatre configurations actives portent `region: var-centre` et
`web.published: true`. Le paquet historique `sec-du-langoustier` a été retiré;
ses anciennes routes FR et EN redirigent définitivement vers
`sec-de-la-jeaune-garde`.

Les sites suivants restent différés et sont absents de l'inventaire et des
sorties de cette vague : Cimentier de la Jaume Garde, Pointe Escampobariou,
Anse du Raba, Anse au Blé et Sec des Carrières.

## Sources et référentiels

- Bathymétrie et élévation côtière détaillées : Shom–IGN Litto3D PACA 2015,
  grille de 1 m, Lambert-93 (`EPSG:2154`), référentiel vertical IGN69.
- Imagerie : IGN BD ORTHO, avec la prise de vue déclarée par site.
- Relief régional : EMODnet Bathymetry DTM 2024 au large et GEBCO 2024 en
  repli NoData, avec le masque terre-mer officiel utilisé par le builder
  régional partagé.

Les cartes décrivent le relief et la couverture des données. Elles ne
démontrent ni l'accès, ni l'autorisation, ni les conditions présentes, ni la
sécurité d'une plongée.

## Configurations et sorties

Les configurations vivent dans `regions/var-centre/sites/`. Les sorties
canoniques vivent dans `regions/var-centre/outputs/`; leur convention complète
est décrite dans [outputs/README.md](outputs/README.md).

Chaque site publié fournit les six actifs natifs attendus : plans 2D
topographique et orthophoto, vues 3D statiques topographique et orthophoto,
planches topographique et orthophoto. Ses quatorze dérivés Web et son paquet de
terrain interactif à sept fichiers sont présents. Les manifestes interactifs
régional et combiné enregistrent tailles et SHA-256.

La carte régionale canonique est :

```text
regions/var-centre/outputs/var-centre-regional-relief.png
```

Elle mesure `1864 × 1440 px`, couvre l'emprise WGS84
`[6.00, 42.86, 6.46, 43.10]` et porte le SHA-256
`044aa08d3b0715ae690003f3c37b74707e241d73a90de233bf73c218172d2a96`.
La copie Web est octet-identique.

## Construction reproductible

Avec le runtime local canonique, sans téléchargement de dépendance :

```text
/Users/follm/home-projects/divetopo/.venv/bin/python apps/web/scripts/build_regional_relief.py var-centre
/Users/follm/home-projects/divetopo/.venv/bin/python apps/web/scripts/build_interactive_terrain_manifest.py var-centre
/Users/follm/home-projects/divetopo/.venv/bin/python apps/web/scripts/build_regional_map_assets.py var-centre
/Users/follm/home-projects/divetopo/.venv/bin/python apps/web/scripts/sync_interactive_terrain.py
```

Les coordonnées des configurations sont la source de vérité des marqueurs. Les
points géographiques ne sont pas des cibles interactives : les cartouches
nominatifs, le clavier et le sélecteur ouvrent les fiches. Cette distinction
évite qu'une paire de points très proches ouvre silencieusement le mauvais
site.

## QA v1.5 — consolidation Jeaune Garde / Langoustier

### Actifs natifs et interactifs

- Les quatre configurations concordent avec `region.json`, les manifestes et les
  répertoires publics. Chaque fiche expose ses plans 2D, vues 3D statiques,
  planches et terrain interactif.
- Les deux points historiques sont distants de `383,327 m`. L'ancien contexte,
  focus et footprint du Langoustier sont couverts à `100 %` par le contexte
  Jeaune Garde de `1 000 × 1 000 m`; les cellules source correspondantes sont
  toutes valides. Le focus Jeaune Garde est porté à `802 × 708 m` et son terrain
  à `1 000 × 800 m`, sans interpolation de données absentes.
- Les six sorties canoniques Jeaune Garde, ses quatorze dérivés Web et son
  terrain interactif ont été régénérés puis inspectés en pleine définition.
  Les paquets Fourmigues, Cap des Mèdes, Gabinière et Escampobariou ont été
  conservés octet pour octet.

### Carte régionale plein format

- Giens, Porquerolles, Port-Cros, les ports, baies et îlots sont continus. Aucun
  triangle, diagonale, damier, raccord de tuile, zone grise ou trou NoData n'a
  été observé. Les transitions tonales bathymétriques au large restent des
  variations douces du relief source, sans couture géométrique.
- Les quatre coordonnées publiées et le repère Escampobariou en préparation
  tombent au bon endroit. Les cartouches et connecteurs publiés sont associés
  sans ambiguïté aux quatre fiches.
- À `1280 × 720`, les quatre cartouches publiés sont dans la carte et sans
  chevauchement.
- À `390 × 844`, la carte mesure environ `347 × 268 px`; les cinq noms restent
  entiers, sans chevauchement, collision avec les bords, la rose, l'échelle ou
  les crédits. Aucun débordement horizontal n'est mesuré.
- Les thèmes clair et sombre conservent un contraste lisible pour les quatre
  cartouches et leur état sélectionné.

### Navigation et terrains Web

- Chaque cartouche visible ouvre la bonne route; chaque lien focalisé et activé
  par `Entrée` conserve la bonne route; chacune des quatre options du sélecteur
  ouvre la bonne fiche et le bon titre.
- Les anciennes routes Langoustier FR et EN répondent par une redirection
  permanente vers Jeaune Garde.
- Sur les quatre fiches, les bascules Plan 2D/Vue 3D et
  orthophoto/topographie, la commande d'isobathes et la remise à zéro du terrain
  répondent correctement.
- À `390 × 844`, les quatre terrains sont prêts. Pour chacun,
  `sourceScaleOverlap=false`, `copyrightScaleOverlap=false` et
  `horizontalOverflow=false`; l'échelle est au-dessus de l'attribution.
- La console ne contient aucune erreur ni aucun avertissement applicatif.

## Garde-fous

Inspecter le diff complet avant tout commit régional. Ne pas modifier une autre
région, la page d'accueil globale, les versions ou les releases. Ne pas pousser,
publier ou déployer depuis ce workflow régional.
