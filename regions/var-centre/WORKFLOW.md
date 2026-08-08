# Workflow topo-bathymétrique du Var Centre

Cette région couvre Giens, Porquerolles et Port-Cros. Elle est autonome : son
identité, son inventaire, ses configurations, ses sorties et sa future route
Web appartiennent à `var-centre`, et non à une sous-région de `paca`.

## État du contrat au commit de fondation v1.4

- La route cible est `/var-centre`. Elle est conceptuelle tant que le
  coordinateur global n'a pas généralisé les types, routes, manifestes, copies
  et builders Web partagés.
- `region.json` contient exactement les cinq configurations intégrées de la
  première vague. Les deux sites déjà publiés conservent ce statut; les trois
  nouveaux restent des brouillons non publiés.
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

Les cinq commits de la première vague ont été intégrés par `git cherry-pick`
après inspection de leur périmètre. Tout commit d'un site différé reste laissé
de côté. La propriété de publication est portée par `web.published` dans chaque
configuration : `true` reste réservé aux deux sites déjà publiés pendant leur
migration; les trois nouveaux sites restent à `false` jusqu'à une décision
explicite.

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

Le chemin réservé à la future carte régionale canonique est :

```text
regions/var-centre/outputs/var-centre-regional-relief.png
```

La carte n'est pas produite dans le commit régional intermédiaire. Son emprise,
ses positions de marqueurs et d'étiquettes doivent être calculées à partir des
cinq configurations par le builder régional partagé, sans recadrer le raster
PACA ni reprendre ses bornes. Les coordonnées déclarées dans les configurations
restent la source de vérité des marqueurs. Les dérivés Web ne sont produits
qu'après la généralisation du builder partagé.

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

## Limites du commit régional intermédiaire

La QA native vérifie l'inventaire, les statuts de publication, les fichiers
attendus, les hashes, les dimensions et les contrats internes des paquets
interactifs. Le manifeste interactif combiné n'indexe que La Gabinière et Cap
des Mèdes; les trois brouillons restent physiquement régionaux mais absents du
manifeste publiable.

Les contrôles suivants restent explicitement en attente :

- validation canonique des configurations, jusqu'à l'ajout du contrat de source
  `var-centre` dans le validateur partagé;
- production et inspection de la carte régionale, jusqu'au builder partagé et
  à son emprise propre;
- QA Web des marqueurs, cartouches, connecteurs, desktop, mobile, clavier et
  toucher, jusqu'au câblage de la route `/var-centre`.

Ces attentes interdisent de considérer les trois nouveaux sites comme
publiables, même si leurs actifs natifs passent les contrôles locaux.

### Résultats de la QA native intermédiaire du 8 août 2026

- Les cinq configurations concordent avec l'inventaire et pointent vers le
  chemin réservé de la carte Var Centre. Seuls La Gabinière et Cap des Mèdes
  ont `web.published: true`.
- Les cinq paquets interactifs sont complets : métadonnées, heightfield,
  masques, isobathes vectorielles et deux textures concordent en dimensions et
  en structure. Le manifeste combiné vérifie ses tailles et SHA-256 et ne
  contient que les deux sites déjà publiés.
- La migration conserve 20 des 22 blobs publiés contrôlés à l'identique depuis
  le commit de fondation. Les deux exceptions sont les planches de Cap des
  Mèdes, adaptées au libellé `VAR CENTRE`; leurs dimensions restent
  `5400 × 3250 px`. Les planches de La Gabinière restent octet-identiques et
  portent encore le libellé historique `CÔTE D’AZUR` en attendant la carte et
  la composition régionales partagées.
- Les trois brouillons ont des plans 2D natifs non canoniques : Les Fourmigues
  `850 × 800 px`, Sec de la Jeaune Garde `1502 × 1402 px`, Sec du Langoustier
  `1700 × 1700 px`. Les crédits sont coupés à droite sur Les Fourmigues et Sec
  de la Jeaune Garde; Sec du Langoustier montre de larges zones NoData grises
  sur les bords gauche et bas.
- Les Fourmigues et Sec de la Jeaune Garde possèdent des vues 3D statiques mais
  aucune planche. Sec du Langoustier ne possède encore ni vues 3D statiques ni
  planches. Ces absences sont acceptées uniquement pour ce commit intermédiaire
  non publiable.
- La suite Python exécute 41 tests avec succès dans l'environnement disponible.
  Quatre modules de tests restent non chargeables faute de Pillow dans le
  Python GDAL local, sans installation autorisée. Un test de manifeste PACA
  reste obsolète après le déplacement approuvé de La Gabinière et Cap des Mèdes
  et doit être corrigé dans la généralisation partagée.
