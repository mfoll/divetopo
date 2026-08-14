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
- Pointe de la Cride et Les Magnons complètent la première vague. Le secteur
  auparavant publié séparément comme La Merveilleuse est inclus dans l'emprise
  élargie des Magnons ; il n'apparaît plus comme une fiche autonome.
- Plate aux Mérous est regroupé dans l'emprise élargie des Magnons : son paquet
  v1.5 reste archivé sous `regions/var-ouest/` avec `web.published: false`, mais
  il est absent de l'inventaire et du planning visibles. Pierre du Jas, Basses
  Moulinières et Sèche Guenaud restent différés et hors de l'inventaire actif.
- Les quatre configurations actives ont `web.published: true`. La configuration
  historique de La Merveilleuse est conservée hors inventaire avec
  `web.published: false` afin de préserver la provenance des anciens rendus.
  Toute extension ultérieure reste soumise au même contrat d'actifs complets et
  de QA.

## État intégré de la vague 1

| Site | Publication | Actifs reçus | Verdict de QA native |
|---|---|---|---|
| Pointe de Portissol | Publié | Plans 2D, vues 3D, planches, paquet interactif et 14 dérivés Web | Migration bit à bit validée ; les planches historiques restent inchangées. |
| Les Deux Frères | Publié | Plans 2D, vues 3D, planches, paquet interactif et 14 dérivés Web | Migration bit à bit validée ; les planches historiques restent inchangées. |
| Pointe de la Cride | Publié | Plans 2D topographique/orthophoto, vues 3D, deux planches, paquet interactif et 14 dérivés Web | Actifs natifs inspectés à pleine résolution ; fiche et terrain chargés en QA Web. |
| Les Magnons | Publié | Plans 2D topographique/orthophoto, vues 3D, deux planches, paquet interactif et 14 dérivés Web | Emprise élargie pour inclure le relief auparavant présenté comme La Merveilleuse et Plate aux Mérous ; crédits, cadrages et terrain réinspectés. |

Le manifeste `outputs/interactive-terrain/manifest.json` indexe exactement les
quatre paquets. Le builder régional partagé produit quatre entrées Web complètes et
le synchroniseur cumulatif conserve `35` paquets canoniques provenant de sept
régions, sans écraser ceux de Bouches-du-Rhône ou Var Centre. Aucun générateur
propre à Var Ouest n'a été créé.

### Correctif de regroupement Plate aux Mérous — 2026-08-14

Le point Plate aux Mérous (`924162.654, 6224032.917`) est maintenant couvert
par l’emprise unique de Les Magnons, sans second marqueur ni fiche : focus
`[924000, 6223320, 925200, 6224150]` (`1200 × 830 m`), contexte et terrain
`[924000, 6223320, 925200, 6224300]` (`1200 × 980 m`), footprint interactif
`980 × 1200 m` orienté à `90°`. Les sources Litto3D comprennent les cellules
`0924_6224`, `0924_6225`, `0925_6224` et `0925_6225` nécessaires à cette
emprise. Le MNT brut présente `95,8565 %` de cellules finies dans le contexte
(`95,4133 %` après masque bathymétrique positif) ; autour du point Plate, la
couverture marine finie ≤ 40 m est `100,0 / 93,605 / 70,497 %` à `50 / 150 /
300 m`. Le point reste dans les quatre marges de l’emprise et du paquet
terrain.

Les quatre cartes canoniques `2474 × 1712`, les deux planches `5400 × 3250`,
les deux textures et le paquet interactif de Magnons ont été régénérés et
inspectés à pleine résolution. Le paquet contient `513 × 419` sommets, `75`
polylignes vectorielles d’isobathes et un résidu maximal de reprojection de
`0,002691 m`, dans la tolérance. La carte régionale raster reste inchangée
(SHA-256 `da3fda2d64f67b52b3f5c80e6df1eaff4b23118fc4740e5c21d90a68506f1460`) :
le regroupement est porté par l’inventaire et le manifeste, qui comptent
désormais `sites=4` et `plannedSites=5` avec Pierre du Jas comme seul pending.
Le build/lint Web post-correction n’a pas pu être relancé dans ce worktree,
car `apps/web/node_modules` et `apps/web/dist/server/index.js` sont absents ;
aucune dépendance n’a été installée.

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
Elle comporte les quatre marqueurs de l'inventaire publié et des cartouches
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

Le manifeste Web contient exactement quatre marqueurs projetés depuis les
coordonnées WGS84 : Portissol `44.85903 %, 40.06602 %`, Deux Frères
`64.15702 %, 60.69149 %`, Cride `39.55658 %, 39.30851 %`, Magnons
`38.174 %, 51.07256 %`. Les déports verticaux et latéraux ont été réglés après
capture réelle ; les quatre cartouches
et connecteurs sont lisibles, contenus dans la carte et non ambigus sur desktop
et mobile. Les `56` actifs Web locaux ont été vérifiés par les builders et les
tests ; les quatre paquets interactifs régionaux sont indexés.

La QA Web locale a été exécutée dans Chrome sur `1280 × 720` et dans un viewport
réel `390 × 844`, en clair et sombre. Les quatre cartouches ouvrent les bons slugs,
les quatre liens répondent à Entrée, le sélecteur ouvre les quatre fiches et les
points superposés testés restent inertes. Les quatre terrains chargent leurs
crédits complets. Sur le terrain réel de Pointe de la Cride à largeur mobile,
l'échelle est visuellement séparée des crédits source et copyright ; le contrôle
exact `390 px` confirme `scrollWidth = 390` et aucun débordement horizontal.
Aucune route ni fiche n'expose d'état provisoire.

## Gate de QA régionale

La zone n'est prête pour son commit final que si :

1. l'inventaire, les configurations, les sorties et les manifestes concordent ;
2. les deux migrations publiées ont des hashes identiques aux artefacts
   antérieurs ;
3. les quatre sites publiés possèdent chacun leurs actifs statiques, planches,
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
