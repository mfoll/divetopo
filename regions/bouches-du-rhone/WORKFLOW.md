# Workflow Bouches-du-Rhône

Cette collection est une région DiveTopo autonome. Elle couvre Frioul,
Planier, Riou et les Calanques. Elle n'est ni une sous-région de PACA ni une
vue filtrée de la route `/paca`.

## Contrat régional

- Identifiant : `bouches-du-rhone`.
- Route conceptuelle : `/bouches-du-rhone`, avec les variantes localisées
  `/bouches-du-rhone/fr` et `/bouches-du-rhone/en`.
- Configurations : `regions/bouches-du-rhone/sites/<slug>.json`.
- Sorties canoniques : `regions/bouches-du-rhone/outputs/`.
- Reliefs interactifs canoniques :
  `regions/bouches-du-rhone/outputs/interactive-terrain/<slug>/`.
- Carte régionale canonique :
  `regions/bouches-du-rhone/outputs/bouches-du-rhone-regional-relief.png`.
- Dérivés Web prévus : `apps/web/public/maps/bouches-du-rhone/`.
- Manifeste Web prévu :
  `apps/web/content/bouches-du-rhone-map-manifest.json`.

La page d'accueil globale, le routeur partagé et les manifestes Web ne sont
modifiés qu'au moment de l'intégration globale. Leur évolution doit être
coordonnée avant toute modification partagée.

## Sources et référentiels

- Projection de travail : RGF93 v1 / Lambert-93 (`EPSG:2154`).
- Bathymétrie et terrain côtier détaillés : Shom–IGN Litto3D PACA 2015,
  grille de 1 m, référentiel vertical IGN69.
- Orthophotographie : IGN BD ORTHO.
- Relief régional marin : EMODnet Bathymetry DTM 2024.
- Contexte de secours uniquement en l'absence de données EMODnet valides :
  GEBCO 2024.
- Trait de côte : limite terre-mer officielle Shom–IGN, suivant le même
  principe de masque que la carte méditerranéenne existante.

Les membres d'archives Litto3D et leur couverture doivent être vérifiés site
par site. Une carte ne prouve ni l'accès, ni l'autorisation, ni la sécurité,
ni les conditions présentes.

## Première vague de la version 1.4

Les configurations ne sont ajoutées à `region.json` que lorsqu'elles existent
dans cette région. La publication reste `web.published: false` jusqu'à la QA
complète et une décision explicite.

| Site | Slug canonique | Secteur | État intégré |
|---|---|---|---|
| Grotte à Corail – Maïre | `grotte-a-corail-maire` | Maïre | Configuration et terrain interactif présents ; jeu statique incomplet ; non publié |
| Pains de Sucre – Riou | `pains-de-sucre-riou` | Riou | Configuration seulement ; actifs bloqués par le runtime GDAL/Pillow ; non publié |
| Impérial de Terre – Riou | `imperial-de-terre-riou` | Riou | Configuration, cartes et terrain interactif présents ; QA visuelle en échec ; non publié |
| Pierre à la Bague – plateau | `pierre-a-la-bague-plateau` | Planier | Configuration, cartes et terrain interactif présents ; QA visuelle en échec ; non publié |
| Tiboulen du Frioul | `tiboulen-du-frioul` | Frioul | Configuration, cartes et terrain interactif présents ; QA visuelle en échec ; non publié |

Les sites suivants sont explicitement différés après la première vague et ne
doivent pas être cherry-pickés dans ce chantier : Impérial du Milieu, Moyades,
Pierre de Briançon – Jarre, Pharillons et Grand Salaman.

Le manifeste interactif régional indexe uniquement les quatre paquets complets.
Pains de Sucre reste dans l'inventaire de travail avec `web.published: false`,
mais n'entre dans aucun manifeste d'actifs tant que ses sorties n'existent pas.

## État de QA intermédiaire

L'intégration de la première vague ne constitue pas une validation de
publication. Les contrôles structurels confirment cinq configurations de draft,
quatre paquets interactifs complets et vérifiables par taille et SHA-256, et
l'absence volontaire de tout actif Pains de Sucre.

L'inspection directe des JPEG et textures WebP à leur résolution native relève
les défauts bloquants suivants :

- Grotte à Corail – Maïre : plans limités à `800 × 800 px`, zones NoData grises
  importantes, chevauchements de libellés en 3D et absence de la variante 3D
  orthophoto ;
- Impérial de Terre – Riou : rideaux verticaux et déformations de terrain très
  marqués dans les vues 3D, avec texte de pied proche du bord ;
- Pierre à la Bague – plateau : pic de terrain majeur dans la 3D orthophoto,
  isobathes confuses sur la côte et éléments de boussole, libellés ou pied de
  carte coupés dans plusieurs rendus ;
- Tiboulen du Frioul : éléments de boussole, libellés profonds et attribution
  coupés au bord dans plusieurs rendus statiques.

Le validateur partagé refuse encore le slug régional avec
`Region 'bouches-du-rhone' has no configured source validation contract`.
Cette correction appartient à la généralisation globale et ne doit pas être
contournée dans le commit régional. Les routes Web, la géométrie desktop/mobile
des marqueurs et les interactions ne sont pas testables avant cette intégration.

La carte régionale a été produite avec le builder partagé, sans builder
Bouches-du-Rhône dédié et sans réutiliser les bornes de la carte PACA. Les
deux copies canoniques sont identiques :

- dimensions : `1864 × 1440 px` ;
- bornes WGS84 : `5.10386667, 43.07038317, 5.51986667, 43.38238317` ;
- SHA-256 :
  `af6808941b63026dbff0f4e87561b6d6961310fe0ffa440e935050f892d19057` ;
- sortie régionale :
  `regions/bouches-du-rhone/outputs/bouches-du-rhone-regional-relief.png` ;
- dérivé Web :
  `apps/web/public/maps/bouches-du-rhone/bouches-du-rhone-regional-relief.png`.

Le masque terre-mer final rasterise les polygones terrestres officiels Shom–IGN
Limite terre-mer, sans reconstruire la topologie depuis les entités linéaires.
L'inspection pleine résolution confirme une emprise cohérente couvrant
Marseille, Frioul, Planier, Maïre, Riou et les Calanques, un trait de côte
continu et un relief terrestre lisible. Les bassins portuaires et la rade
restent ouverts ; les îles et îlots ne présentent ni fermeture anguleuse ni
fragmentation en blocs. Par rapport au rendu précédemment validé, 52 470 pixels
sur 2 684 160 diffèrent (`1,9548 %`), avec un delta absolu moyen de `0,831907`
par canal et un delta maximal de `131`. Les positions projetées dans le cadre
sont :

| Site | Longitude | Latitude | Position dans la carte |
|---|---:|---:|---:|
| Grotte à Corail – Maïre | 5.33183333 | 43.21033333 | 54.79968 %, 55.14418 % |
| Pains de Sucre – Riou | 5.39711667 | 43.17558333 | 70.49279 %, 66.28200 % |
| Impérial de Terre – Riou | 5.39300000 | 43.17283300 | 69.50320 %, 67.16351 % |
| Pierre à la Bague – plateau | 5.22661667 | 43.19711667 | 29.50721 %, 59.38029 % |
| Tiboulen du Frioul | 5.28500000 | 43.27993333 | 43.54167 %, 32.83649 % |

Ces positions se trouvent toutes dans les bornes et correspondent visuellement
aux secteurs attendus. Le manifeste Web conserve volontairement `sites: []` :
aucun draft n'est publié et aucun marqueur de brouillon n'est exposé.

Les sites déjà publiés qui appartiennent à cette zone doivent être migrés par
copie contrôlée de leurs configurations et actifs canoniques, sans
régénération si les fichiers restent valides. Comparer les SHA-256 avant et
après migration. Aucun déplacement ne doit supprimer un actif encore consommé
par la version publique courante avant l'intégration globale.

## Intégration des commits de site

Pour chaque commit transmis par le coordinateur global :

1. inspecter son diff et confirmer qu'il ne touche qu'au site annoncé ;
2. vérifier que `region` vaut `bouches-du-rhone`, que tous les chemins pointent
   vers cette région et que `web.published` vaut `false` ;
3. intégrer le commit par `git cherry-pick <sha>` ;
4. ajouter l'entrée correspondante à l'inventaire `sites` de `region.json` ;
5. exécuter les contrôles de configuration et vérifier les sorties existantes ;
6. préserver les modifications étrangères et ne jamais publier le brouillon.

Un conflit dans un fichier partagé n'est pas résolu silencieusement : il est
signalé au coordinateur global avant reprise.

## Carte régionale

La carte doit cadrer uniquement la collection Bouches-du-Rhône, avec une marge
suffisante pour Frioul, Planier, Riou, Jarre, Maïre et les Calanques. Les bornes
de la carte PACA actuelle ne conviennent pas : elles excluent toute cette zone.

La carte finale doit :

- être construite depuis les sources régionales documentées, sans géométrie
  côtière dessinée à la main ;
- conserver une emprise, des dimensions et un hash dans son manifeste ;
- afficher exactement un marqueur par site intégré à la carte régionale ;
- rester lisible comme vignette de page d'accueil et comme carte principale de
  la page régionale ;
- être contrôlée à sa pleine résolution avant acceptation.

## QA avant décision de publication

1. Valider tous les JSON et l'accord entre inventaire, configurations,
   manifeste, actifs et terrain interactif.
2. Confirmer que les sites en chantier restent non publiés.
3. Comparer les hashes des actifs migrés sans régénération.
4. Inspecter la carte régionale à pleine résolution : côte, relief, marqueurs,
   libellés, traits de liaison et attribution.
5. Exécuter le contrôle géométrique des marqueurs défini dans le workflow
   racine à `1280 × 720` et `390 × 844`, puis conserver captures et mesures.
6. Vérifier les routes régionales et chaque site au clavier, à la souris et au
   toucher, en français et en anglais.
7. Exécuter les tests Python concernés, puis lint, tests et build Web sans
   installer de dépendances absentes.
8. Inspecter le diff complet de la zone et confirmer qu'aucune autre région,
   version, release ou configuration de déploiement n'a changé.

La QA réussie ne publie rien. La bascule de `web.published`, l'exposition sur
la page d'accueil, la release et le déploiement exigent une décision explicite
et sont hors du commit de zone.
