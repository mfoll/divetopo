# Workflow topo-bathymétrique du Var Ouest

Cette région DiveTopo autonome couvre Sanary-sur-Mer, Le Brusc, les Embiez et
le cap Sicié. Elle n'est ni une sous-région de PACA, ni une vue filtrée de la
route `/paca`. Sa route conceptuelle est `/var-ouest` et tous ses artefacts
canoniques appartiennent à `regions/var-ouest/`.

## Périmètre et sources

- Projection commune : RGF93 v1 / Lambert-93, `EPSG:2154`.
- Bathymétrie et topographie côtières : Shom–IGN Litto3D PACA 2015, MNT
  maillé à 1 m, référentiel vertical IGN69.
- Imagerie terrestre optionnelle : IGN BD ORTHO, avec une date de prise de vue
  vérifiée et enregistrée site par site.
- Carte régionale : Litto3D autour des sites et du littoral, EMODnet
  Bathymetry DTM 2024 au large, GEBCO 2024 uniquement en repli de contexte,
  relief terrestre officiel et limite terre-mer Shom–IGN.

Les URLs, membres d'archives et attributions exacts restent dans les
configurations et les manifestes. La carte ne prouve ni l'accès, ni
l'autorisation, ni les conditions présentes, ni la sécurité d'une plongée.

## Arborescence canonique

```text
regions/var-ouest/region.json
regions/var-ouest/sites/<slug>.json
regions/var-ouest/outputs/<slug>-topobathy-2d.jpg
regions/var-ouest/outputs/<slug>-topobathy-2d-ortho.jpg
regions/var-ouest/outputs/<slug>-planche.jpg
regions/var-ouest/outputs/<slug>-planche-topographique.jpg
regions/var-ouest/outputs/interactive-terrain/<slug>/
regions/var-ouest/outputs/interactive-terrain/manifest.json
apps/web/public/maps/var-ouest/
apps/web/content/var-ouest-map-manifest.json
```

La carte régionale propre est
`apps/web/public/maps/var-ouest/var-ouest-regional-relief.png`. Elle doit être
utilisable à la fois comme image de fiche sur la page d'accueil et comme carte
de sélection sur `/var-ouest`, sans dépendre d'un fichier PACA.

## États de publication

`region.json` décrit l'intention régionale. La publication Web reste régie par
le champ explicite `web.published` de chaque configuration et par la présence
du jeu d'artefacts complet dans le manifeste Web généré.

- Pointe de Portissol et Les Deux Frères sont les deux sites publiés à migrer.
- Pointe de la Cride, Les Magnons et La Merveilleuse complètent la première
  vague de cinq sites et restent des brouillons.
- Plate aux Mérous, Pierre du Jas, Basses Moulinières et Sèche Guenaud sont
  différés. Ils restent hors de l'inventaire actif et aucun de leurs commits ne
  doit être cherry-pické pendant cette vague.
- Un cherry-pick, une configuration valide ou la présence d'images ne suffit
  jamais à publier un brouillon.
- Le passage de `web.published: false` à `true` exige la QA puis une décision
  explicite. Il ne fait pas partie de l'intégration technique initiale.

## Intégration des commits de sites

1. Vérifier que le worktree est toujours fondé sur le commit v1.4 attendu et
   que le diff en cours est compris.
2. Inspecter le commit transmis avec `git show --stat` et `git show` avant le
   cherry-pick. Refuser ou faire corriger tout changement hors du site annoncé.
3. Cherry-picker un site à la fois et résoudre les chemins vers
   `regions/var-ouest/`. Ne pas absorber une modification de PACA, Réunion, de
   l'accueil global, des versions ou du déploiement.
4. Vérifier que tout nouveau site conserve `web.published: false`.
5. Exécuter les contrôles de configuration disponibles sans téléchargement,
   puis inspecter les sorties à pleine résolution.

## Migration des deux sites publiés

Pointe de Portissol et Les Deux Frères doivent être migrés, pas régénérés.

1. Reprendre leurs configurations et artefacts canoniques déjà publiés.
2. Changer uniquement l'identité régionale et les chemins régionaux requis.
3. Copier les cartes, planches et paquets interactifs dans les sorties Var
   Ouest, puis comparer le SHA-256 de chaque fichier source et destination.
4. Reconstruire les manifestes à partir de ces fichiers inchangés. Ne relancer
   aucun rendu cartographique si le contrat et les hashes sont cohérents.
5. Conserver les sources PACA tant que le coordinateur global n'a pas autorisé
   leur retrait dans une tâche séparée. Cette zone ne modifie pas les autres
   régions.

## Carte régionale

La carte doit couvrir uniquement l'emprise utile Sanary, Le Brusc, les Embiez
et cap Sicié, tout en laissant assez de contexte marin pour lire les positions.
Elle comporte les marqueurs de l'inventaire intégré et des cartouches lisibles
sur desktop et mobile. Les brouillons peuvent apparaître sur la carte régionale
de QA locale, mais ils ne doivent pas être exposés sur une route publique avant
la décision de publication.

Avant validation, contrôler à pleine résolution :

- cohérence du trait de côte, des reliefs terrestre et marin et absence de
  raccord ou NoData trompeur ;
- position géographique de chaque marqueur ;
- absence de chevauchement entre points, connecteurs et étiquettes ;
- orthographe et rattachement communal ;
- crédits et sources correspondant réellement aux couches rendues.

## Gate de QA régionale

La zone n'est prête pour son commit final que si :

1. l'inventaire, les configurations, les sorties et les manifestes concordent ;
2. les deux migrations publiées ont des hashes identiques aux artefacts
   antérieurs ;
3. chaque nouveau site reste non publié ;
4. toutes les images sont inspectées à pleine résolution ;
5. `/var-ouest` est inspectée en desktop `1280 × 720` DPR 2 et mobile
   `390 × 844` DPR 1, en français et en anglais ;
6. les points, connecteurs, cartouches, sélecteurs, contrôles, téléchargements
   et reliefs interactifs sont testés au clavier et au toucher ;
7. les tests Python concernés, le lint, les tests Web, le build de production
   et `git diff --check` passent sans dépendance téléchargée pour la tâche ;
8. le diff final ne touche ni une autre région, ni l'accueil global, ni les
   versions, releases ou fichiers de déploiement.

Le commit final est local et limité à la zone. Aucun push ni déploiement ne fait
partie de ce workflow.
