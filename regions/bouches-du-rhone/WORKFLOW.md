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

## Sites cibles de la version 1.4

Les configurations ne sont ajoutées à `region.json` que lorsqu'elles existent
dans cette région. La publication reste `web.published: false` jusqu'à la QA
complète et une décision explicite.

| Site | Slug attendu | Secteur |
|---|---|---|
| Grotte à Corail – Maïre | `grotte-a-corail-maire` | Maïre |
| Pains de Sucre – Riou | `pains-de-sucre-riou` | Riou |
| Impérial de Terre | `imperial-de-terre` | Riou |
| Impérial du Milieu | `imperial-du-milieu` | Riou |
| Moyades | `moyades` | Riou |
| Pierre à la Bague – plateau | `pierre-a-la-bague-plateau` | Planier |
| Tiboulen du Frioul | `tiboulen-du-frioul` | Frioul |
| Pierre de Briançon – Jarre | `pierre-de-briancon-jarre` | Jarre |
| Pharillons | `pharillons` | Frioul |
| Grand Salaman | `grand-salaman` | Frioul |

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
