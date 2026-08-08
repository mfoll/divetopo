# Workflow Bouches-du-Rhône

Cette collection est une région DiveTopo autonome couvrant Frioul, Planier,
Riou et les Calanques. Elle n'est ni une sous-région de PACA ni une vue filtrée
de la route `/paca`.

## Contrat régional

- Identifiant : `bouches-du-rhone`.
- Routes : `/bouches-du-rhone`, `/bouches-du-rhone/fr` et
  `/bouches-du-rhone/en`.
- Configurations : `regions/bouches-du-rhone/sites/<slug>.json`.
- Sorties canoniques : `regions/bouches-du-rhone/outputs/`.
- Reliefs interactifs :
  `regions/bouches-du-rhone/outputs/interactive-terrain/<slug>/`.
- Carte régionale :
  `regions/bouches-du-rhone/outputs/bouches-du-rhone-regional-relief.png`.
- Dérivés Web : `apps/web/public/maps/bouches-du-rhone/`.
- Manifeste Web :
  `apps/web/content/bouches-du-rhone-map-manifest.json`.

La page d'accueil globale, les versions, releases et déploiements restent hors
du périmètre régional.

## Sources et référentiels

- Projection de travail : RGF93 v1 / Lambert-93 (`EPSG:2154`).
- Bathymétrie et terrain côtier : Shom–IGN Litto3D PACA 2015, grille de
  1 m, référentiel vertical IGN69.
- Orthophotographie : IGN BD ORTHO.
- Relief régional marin : EMODnet Bathymetry DTM 2024, avec GEBCO 2024 comme
  contexte de secours uniquement.
- Trait de côte : polygones officiels Shom–IGN Limite terre-mer.

Une carte ne prouve ni l'accès, ni l'autorisation, ni la sécurité, ni les
conditions présentes.

## Première vague publiée de la version 1.4

La région livre exactement cinq sites. Chaque configuration porte
`web.published: true`. Chaque paquet possède ses plans 2D topographique et
orthophoto, ses vues 3D statiques, ses planches et dérivés Web, ainsi qu'un
terrain interactif indexé dans les manifestes régional et public.

| Site | Slug canonique | Secteur | État final |
|---|---|---|---|
| Grotte à Corail – Maïre | `grotte-a-corail-maire` | Maïre | Publié, paquet complet |
| Pains de Sucre – Riou | `pains-de-sucre-riou` | Riou | Publié, paquet complet |
| Impérial de Terre – Riou | `imperial-de-terre-riou` | Riou | Publié, paquet complet |
| Pierre à la Bague – plateau | `pierre-a-la-bague-plateau` | Planier | Publié, paquet complet |
| Tiboulen du Frioul | `tiboulen-du-frioul` | Frioul | Publié, paquet complet |

Impérial du Milieu, Moyades, Pierre de Briançon – Jarre, Pharillons et Grand
Salaman restent différés et absents de cette livraison.

## Carte régionale

La carte a été produite par le builder partagé, sans builder dédié ni bornes
PACA. Les copies régionale et Web sont identiques :

- dimensions : `1864 × 1440 px` ;
- bornes WGS84 : `5.10386667, 43.07038317, 5.51986667, 43.38238317` ;
- SHA-256 :
  `af6808941b63026dbff0f4e87561b6d6961310fe0ffa440e935050f892d19057`.

Le masque terre-mer rasterise les polygones terrestres officiels. L'inspection
pleine résolution confirme un trait de côte continu : bassins portuaires, rade
et baies restent ouverts ; îles et îlots ne présentent ni fermeture anguleuse,
ni triangle, diagonale parasite, damier, raccord de tuile, zone grise/NoData ou
fragmentation en blocs.

| Site | Longitude | Latitude | Position dans la carte |
|---|---:|---:|---:|
| Grotte à Corail – Maïre | 5.33183333 | 43.21033333 | 54.79968 %, 55.14418 % |
| Pains de Sucre – Riou | 5.39711667 | 43.17558333 | 70.49279 %, 66.28200 % |
| Impérial de Terre – Riou | 5.39300000 | 43.17283300 | 69.50320 %, 67.16351 % |
| Pierre à la Bague – plateau | 5.22661667 | 43.19711667 | 29.50721 %, 59.38029 % |
| Tiboulen du Frioul | 5.28500000 | 43.27993333 | 43.54167 %, 32.83649 % |

Les cinq positions sont dans les bornes et correspondent aux secteurs attendus.

## QA finale de la version 1.4

- Les manifestes Web, régional et interactif contiennent exactement les cinq
  slugs publiés, sans entrée différée ni mention « en préparation ».
- Le PNG régional a été inspecté à sa résolution native `1864 × 1440 px`.
- Les cinq marqueurs et noms sont visibles. Les deux sites proches de Riou ont
  des connecteurs divergents et des libellés déportés de part et d'autre. Les
  points géographiques superposés restent neutres ; les cartouches, le clavier
  et le sélecteur sont les cibles d'ouverture.
- La page régionale a été contrôlée à `1280 × 720` et `390 × 844`, en thèmes
  clair et sombre, sans collision, coupure, débordement horizontal ou carte
  disproportionnée.
- Contraste clair : libellés blancs sur `rgb(6, 28, 36)`. Contraste sombre :
  libellés non sélectionnés `rgb(8, 33, 42)` sur fond clair, sélection blanche
  sur `rgb(3, 21, 27)`.
- Chaque libellé de carte ouvre le slug attendu et le sélecteur mobile contient
  exactement les cinq options. Un clic réel sur les points superposés de Riou
  laisse la route régionale inchangée.
- Terrain interactif mobile vérifié à `390 × 844` : échelle visible, aucune
  collision avec la source ou le copyright, aucun débordement horizontal.
- Les JSON, l'accord entre inventaire, configurations, actifs et manifestes,
  les tests Python, le lint, les tests et le build Web sont contrôlés avant le
  commit final.

La publication reste locale aux configurations et manifestes. Aucun push,
déploiement, changement de version ou release n'est effectué ici.
