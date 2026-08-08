# Workflow topo-bathymétrique du Var Centre

Cette région couvre Giens, Porquerolles et Port-Cros. Elle est autonome : son
identité, son inventaire, ses configurations, ses sorties et sa future route
Web appartiennent à `var-centre`, et non à une sous-région de `paca`.

## État du contrat au commit de fondation v1.4

- La route cible est `/var-centre`. Elle est conceptuelle tant que le
  coordinateur global n'a pas généralisé les types, routes, manifestes, copies
  et builders Web partagés.
- `region.json` conserve volontairement un inventaire `sites` vide. Un site
  n'y entre qu'avec sa configuration intégrée et vérifiée; ce fichier ne doit
  pas anticiper des chemins absents.
- Le module déclaré `cartography.regions.var_centre` est le point d'entrée
  contractuel futur. Sa création relève de la généralisation partagée et ne
  fait pas partie du présent socle local.
- Aucun fichier de ce dossier n'autorise à modifier la page d'accueil globale,
  une autre région, une version, une release ou un déploiement.

## Priorisation de la première vague

La première vague est limitée à exactement cinq sites. Les deux sites déjà
publiés doivent être migrés sans régénération inutile :

- La Gabinière (`la-gabiniere-port-cros`);
- Cap des Mèdes (`cap-des-medes`).

Les trois nouveaux sites de la première vague restent des brouillons non
publiés jusqu'à QA complète et décision explicite :

- Sec de la Jeaune Garde (`sec-de-la-jeaune-garde`);
- Sec du Langoustier (`sec-du-langoustier`);
- Les Fourmigues (`les-fourmigues`).

Les sites suivants sont différés. Ne pas cherry-picker leurs commits, ne pas
les ajouter à `region.json` et ne pas produire leurs sorties dans cette vague :

- Cimentier de la Jaume Garde (`cimentier-de-la-jaume-garde`);
- Pointe Escampobariou (`pointe-escampobariou`);
- Anse du Raba (`anse-du-raba`);
- Anse au Blé (`anse-au-ble`);
- Sec des Carrières (`sec-des-carrieres`).

Un commit reçu pour l'un des cinq sites de la première vague est intégré par
`git cherry-pick` après inspection de son périmètre. Tout commit d'un site
différé est laissé de côté. Les conflits sont résolus dans la région, sans
réécrire ni absorber des changements étrangers. La propriété de publication
reste portée par `web.published` dans chaque configuration : `true` est réservé
aux deux sites déjà publiés pendant leur migration; les trois nouveaux sites
restent à `false` jusqu'à une décision explicite.

## Sources et référentiels

- Bathymétrie et élévation côtière détaillées : Shom–IGN Litto3D PACA 2015,
  grille de 1 m, projection Lambert-93 (`EPSG:2154`) et référentiel vertical
  IGN69.
- Imagerie terrestre : IGN BD ORTHO; la date de prise de vue doit être vérifiée
  et enregistrée site par site.
- Carte régionale : Litto3D près de la côte, EMODnet Bathymetry DTM 2024 au
  large, GEBCO 2024 uniquement en repli sur les cellules NoData, et relief
  terrestre compatible avec le pipeline régional global.

Les cartes montrent le relief et la couverture des données. Elles ne
démontrent ni l'accès, ni l'autorisation, ni les conditions présentes, ni la
sécurité d'une plongée. Litto3D est en IGN69; aucune sonde hydrographique ne
doit être fusionnée directement sans transformation verticale documentée.

## Configurations et sorties

Les configurations de sites vivent dans `regions/var-centre/sites/`. Les
sorties canoniques vivent dans `regions/var-centre/outputs/`; leur convention
détaillée est décrite dans [outputs/README.md](outputs/README.md).

Chaque configuration doit déclarer `"region": "var-centre"`. Les chemins
explicites hérités de PACA doivent être remplacés par leurs équivalents
`var-centre`, notamment la carte régionale. Une migration sans régénération
compare les SHA-256 avant et après déplacement de chaque artefact.

La carte régionale canonique est :

```text
regions/var-centre/outputs/var-centre-regional-relief.png
```

Son emprise finale, ses positions de marqueurs et d'étiquettes et ses dérivés
Web ne sont figés qu'après intégration de tous les sites. Les coordonnées
déclarées dans les configurations sont la source de vérité des marqueurs.

## Séquence d'intégration d'un site

1. Examiner le commit transmis et vérifier qu'il ne touche que le site et les
   contrats régionaux attendus.
2. Cherry-picker le commit, résoudre les éventuels conflits sans modifier les
   autres régions, puis valider la configuration.
3. Pour La Gabinière et Cap des Mèdes, déplacer les artefacts canoniques et les
   dérivés existants en conservant leurs octets lorsqu'aucune correction n'est
   requise; enregistrer les hashes avant/après.
4. Pour un nouveau site, inspecter les tuiles ASC, le masque et les NoData avant
   de qualifier la couverture. Un JSON valide ne vaut pas QA cartographique.
5. Produire et inspecter à pleine résolution les plans 2D, vues 3D, planches et
   terrain interactif. Garder `web.published: false`.
6. Mettre à jour l'inventaire de `region.json` seulement lorsque le chemin de
   configuration existe et que son slug concorde.

## QA régionale avant décision de publication

- Vérifier la concordance entre `region.json`, les configurations, les sorties
  canoniques, les paquets interactifs et les manifestes générés.
- Régénérer la carte régionale à partir des coordonnées déclarées; contrôler
  chaque marqueur, cartouche et connecteur à pleine résolution.
- Tester la future page régionale à `1280 × 720` (DPR 2) et `390 × 844`
  (DPR 1), zoom navigateur 100 %, selon le gate géométrique du workflow racine.
- Contrôler la navigation au clavier, le toucher, les états sélectionnés, les
  débordements, les collisions d'étiquettes et le cadrage de la carte.
- Exécuter les validations de configuration, la suite Python, le lint, les
  tests Web et le build disponibles, sans télécharger de dépendances.
- Inspecter le diff complet de zone avant le commit. Ne pas pousser, publier,
  releaser ou déployer depuis ce workflow régional.

Un nouveau site ne devient publiable qu'après réussite de ces contrôles et
décision explicite du coordinateur global.
