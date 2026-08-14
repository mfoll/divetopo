# Calibration des points de vue 3D méditerranéens

Les points de vue initiaux des 24 sites méditerranéens de la v1.4 ont été
réglés visuellement dans le terrain interactif, site par site, le 13 août 2026.
L'interface temporaire de calibration a été retirée avant publication. Le
résultat de la calibration reste versionné dans chaque configuration de site,
sous `web.interactive_initial_view`.

## Données conservées

Chaque configuration conserve deux représentations complémentaires :

- les paramètres lisibles `zoom`, `orbit_azimuth_deg`,
  `camera_elevation_deg`, `pan_right_m`, `pan_up_m` et les décalages de centre ;
- la pose exacte `camera_position_m` et `camera_target_m`, utilisée en priorité
  par le terrain interactif.

La pose exacte est l'autorité de rendu. Une succession de rotations et de
translations dans `OrbitControls` ne se décompose pas toujours sans résidu dans
les seuls paramètres sémantiques. Conserver la position et la cible évite donc
une dérive entre le cadrage approuvé, la vue interactive et les captures.

Le validateur de `cartography/config.py` exige que position et cible soient
présentes ensemble. `apps/web/scripts/regional_manifest.py` les transpose en
`cameraPositionM` et `cameraTargetM`. `TerrainViewer.tsx` applique cette paire
après les réglages sémantiques et avant d'enregistrer la vue de réinitialisation.

## Méthode utilisée en v1.4

L'outil temporaire n'était activable qu'en local. Il est conservé dans ce même
dépôt sous `tools/camera-calibration/` et se lance depuis `apps/web` avec
`npm run camera-calibration -- --host localhost --port 3010`. Le gestionnaire
restaure l'interface depuis l'historique Git uniquement pour la durée du
serveur, puis la retire automatiquement. Pour chaque site publié des
régions Bouches-du-Rhône, Var Ouest, Var Centre, Var Est et Alpes-Maritimes :

1. ouvrir le terrain 3D et régler rotation, élévation, zoom et translation ;
2. enregistrer le cadrage dans le navigateur ;
3. exporter une collection JSON unique ;
4. vérifier que les 24 slugs publiés sont présents exactement une fois ;
5. reporter les paramètres sémantiques et la position/cible diagnostiques dans
   les configurations de site ;
6. reconstruire les cinq manifestes régionaux ;
7. capturer les vues topographique et orthophoto, sur ordinateur et mobile ;
8. produire les dérivés Web, les deux JPEG 3D statiques canoniques et les deux
   planches de chaque site ;
9. contrôler les 96 captures, les 48 vues statiques et les 48 planches en pleine
   résolution, puis exécuter les tests Python/Web, le build et le lint.

Les fichiers de configuration sont désormais la source reproductible. Le JSON
brut exporté et l'interface de collecte ne sont pas nécessaires au bundle
publié. Les commits `3eff486`, `6967082` et `76a561a` conservent respectivement
l'interface initiale, son export global et son retrait réversible. Avant une
release, `npm run camera-calibration:check-release` doit confirmer que l'outil
est désactivé.

## Ordre de régénération

Après toute modification d'une pose :

1. valider la configuration ;
2. reconstruire le manifeste régional ;
3. régénérer les captures 3D dans les deux styles ;
4. reconstruire les dérivés Web et recopier les JPEG de téléchargement vers les
   sorties canoniques ;
5. recomposer les planches avec la vue 3D interactive comme source de relief ;
6. reconstruire les actifs de carte régionale si le manifeste a changé ;
7. refaire la QA visuelle desktop/mobile et plein format avant publication.

La Réunion n'a pas été recalibrée dans cette campagne.
