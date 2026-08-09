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

- Pointe de Portissol et Les Deux Frères sont les deux sites publiés migrés sans
  régénération.
- Pointe de la Cride, Les Magnons et La Merveilleuse complètent la première
  vague. Leurs paquets complets ont passé la QA native et Web ; ils sont publiés.
- Plate aux Mérous, Pierre du Jas, Basses Moulinières et Sèche Guenaud sont
  différés. Ils restent hors de l'inventaire actif et aucun de leurs commits ne
  doit être cherry-pické pendant cette vague.
- Les cinq configurations actives ont `web.published: true`. Toute extension
  ultérieure reste soumise au même contrat d'actifs complets et de QA.

## État intégré de la vague 1

| Site | Publication | Actifs reçus | Verdict de QA native |
|---|---|---|---|
| Pointe de Portissol | Publié | Plans 2D, vues 3D, planches, paquet interactif et 14 dérivés Web | Migration bit à bit validée ; les planches historiques restent inchangées. |
| Les Deux Frères | Publié | Plans 2D, vues 3D, planches, paquet interactif et 14 dérivés Web | Migration bit à bit validée ; les planches historiques restent inchangées. |
| Pointe de la Cride | Publié | Plans 2D topographique/orthophoto, vues 3D, deux planches, paquet interactif et 14 dérivés Web | Actifs natifs inspectés à pleine résolution ; fiche et terrain chargés en QA Web. |
| Les Magnons | Publié | Plans 2D topographique/orthophoto, vues 3D, deux planches, paquet interactif et 14 dérivés Web | Crédits orthophoto corrigés puis réinspectés à pleine résolution ; fiche et terrain chargés. |
| La Merveilleuse | Publié | Plans 2D topographique/orthophoto, vues 3D, deux planches, paquet interactif et 14 dérivés Web | Crédits, masques, vues statiques et terrain inspectés ; fiche et terrain chargés. |

Le manifeste `outputs/interactive-terrain/manifest.json` indexe exactement les
cinq paquets. Le builder régional partagé produit cinq entrées Web complètes et
le synchroniseur cumulatif conserve `26` paquets canoniques provenant de six
régions, sans écraser ceux de Bouches-du-Rhône ou Var Centre. Aucun générateur
propre à Var Ouest n'a été créé.

## Intégration des commits de sites

1. Vérifier que le worktree est toujours fondé sur le commit v1.4 attendu et
   que le diff en cours est compris.
2. Inspecter le commit transmis avec `git show --stat` et `git show` avant le
   cherry-pick. Refuser ou faire corriger tout changement hors du site annoncé.
3. Cherry-picker un site à la fois et résoudre les chemins vers
   `regions/var-ouest/`. Ne pas absorber une modification de PACA, Réunion, de
   l'accueil global, des versions ou du déploiement.
4. Vérifier que l'état `web.published` correspond à la décision régionale et
   qu'aucun site incomplet n'entre dans les manifestes.
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
Elle comporte les cinq marqueurs de l'inventaire publié et des cartouches
lisibles sur desktop et mobile. Les coordonnées réelles ne sont jamais déplacées :
les points superposés restent des repères inertes, tandis que les cartouches,
le clavier et le sélecteur ouvrent les fiches sans ambiguïté.

Avant validation, contrôler à pleine résolution :

- cohérence du trait de côte, des reliefs terrestre et marin et absence de
  raccord ou NoData trompeur ;
- position géographique de chaque marqueur ;
- absence de chevauchement entre points, connecteurs et étiquettes ;
- orthographe et rattachement communal ;
- crédits et sources correspondant réellement aux couches rendues.

### Résultat de QA de la carte v1.4

La carte `1864 × 1440 px` a été inspectée à sa résolution native. Le masque de
terre rasterise directement la couche polygonale officielle Shom–IGN
`LIMTM_2154_WFS:limite_terre_mer_france_metropolitaine_polygones` : `863`
features, `880196` sommets, fraction terrestre `0.384` et écart `0.004` avec le
garde-fou Natural Earth. Les anciens triangles de fermeture, raccords diagonaux
et blocs côtiers trompeurs ne sont plus présents. Le SHA-256 du PNG canonique et
de son dérivé Web est
`da3fda2d64f67b52b3f5c80e6df1eaff4b23118fc4740e5c21d90a68506f1460`.

Le manifeste Web contient exactement cinq marqueurs projetés depuis les
coordonnées WGS84 : Portissol `44.85903 %, 40.06602 %`, Deux Frères
`64.15702 %, 60.69149 %`, Cride `39.55658 %, 39.30851 %`, Magnons
`38.174 %, 51.07256 %` et Merveilleuse `35.84298 %, 52.42615 %`. Les déports
verticaux et latéraux ont été réglés après capture réelle ; les cinq cartouches
et connecteurs sont lisibles, contenus dans la carte et non ambigus sur desktop
et mobile. Les `70` actifs Web locaux ont été vérifiés par les builders et les
tests ; les cinq paquets interactifs régionaux sont indexés.

La QA Web locale a été exécutée dans Chrome sur `1280 × 720` et dans un viewport
réel `390 × 844`, en clair et sombre. Les cinq cartouches ouvrent les bons slugs,
les cinq liens répondent à Entrée, le sélecteur ouvre les cinq fiches et les
points superposés testés restent inertes. Les cinq terrains chargent leurs
crédits complets. Sur le terrain réel de Pointe de la Cride à largeur mobile,
l'échelle est visuellement séparée des crédits source et copyright ; le contrôle
exact `390 px` confirme `scrollWidth = 390` et aucun débordement horizontal.
Aucune route ni fiche n'expose d'état provisoire.

## Gate de QA régionale

La zone n'est prête pour son commit final que si :

1. l'inventaire, les configurations, les sorties et les manifestes concordent ;
2. les deux migrations publiées ont des hashes identiques aux artefacts
   antérieurs ;
3. les cinq sites publiés possèdent chacun leurs actifs statiques, planches,
   dérivés Web et paquet interactif complets ;
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
