# QA finale Var Est, v1.4

Statut : **accepté pour intégration régionale locale**. Les cinq sites de la
vague 1 sont complets et portent `web.published: true`.

## Actifs et carte régionale

- Pour chacun des cinq sites, les plans 2D topographique/orthophoto, vues 3D
  statiques topographique/orthophoto et deux planches ont été inspectés en
  pleine définition. Les cartes mesurent 2474 × 1712 et les planches
  5400 × 3250. Aucun bord de maillage, wedge, diagonale, couture, damier ou
  NoData n’est visible dans les actifs acceptés.
- Les cinq paquets interactifs comportent chacun sept fichiers validés par
  taille et SHA-256. Le manifeste combiné contient 28 paquets sur cinq régions,
  dont exactement les cinq Var Est.
- La carte régionale mesure 1864 × 1440 et conserve le SHA-256
  `0f03a6ccac5581749ad92af1e00f2088028dc6b67880ba80247d4bb8ea3c8e57`.
  Le littoral, les ports, baies, îlots et les îles de Lérins sont continus,
  sans triangle, raccord de tuile, zone grise ni trou NoData.
- Les cinq marqueurs proviennent des coordonnées déclarées et tombent sur les
  positions attendues : cluster du Dramont pour Pyramides, Sec et Arche,
  Le Village à l’est du cluster, Cathédrale au nord-est vers Le Trayas.

## QA Web réelle

- À 1280 × 720, la carte mesure 272 × 210 px. Les cinq cartouches restent dans
  la carte, sans chevauchement entre eux ni collision avec rose, échelle ou
  bord. `scrollWidth=1280`.
- À 390 × 844, la carte mesure environ 347 × 268 px. Les cinq cartouches restent
  entiers, sans collision ni débordement; `scrollWidth=390` et le masthead se
  termine exactement à `right=390`.
- Les thèmes clair et sombre ont été inspectés : cartouches, connecteurs et
  sélection restent lisibles et contrastés.
- Les cinq cartouches, les liens au clavier et les cinq options du sélecteur
  ouvrent la bonne fiche. Les points superposés restent non interactifs et
  n’ouvrent aucune mauvaise route. Aucune mention « en préparation » ne reste.
- Les cinq terrains sont prêts sur desktop/mobile; les bascules 2D/3D,
  topographie/orthophoto, isobathes et remise à zéro répondent. Sur mobile,
  l’échelle reste au-dessus de l’attribution et aucun débordement horizontal
  n’est observé.

## Suites finales

- Build Web : réussi.
- Tests Python : 124/124 réussis.
- Tests Web : 37/37 réussis.
- Lint Web : 0 erreur, 11 avertissements préexistants.
- Aucun changement de contenu d’une autre région, de homepage, version,
  release ou déploiement; aucun push ni déploiement.
