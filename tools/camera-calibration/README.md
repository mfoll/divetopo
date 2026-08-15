# Outil de calibration des caméras 3D

Cet outil restaure temporairement, dans le même dépôt, l'interface utilisée
pour régler les points de vue 3D de la v1.4. Son code n'est pas présent dans le
bundle Web normal : il est conservé dans l'historique Git et réappliqué
uniquement pendant une session de développement.

## Utilisation normale

Depuis `apps/web` :

```sh
npm run camera-calibration -- --host localhost --port 3010
```

Ouvrir ensuite une fiche avec `?camera-calibration`, déplacer la caméra et
cliquer sur `Enregistrer ce cadrage`. Les cadrages sont conservés dans le
stockage local du navigateur. Le bouton `Télécharger toutes les calibrations`
produit un seul fichier `divetopo-camera-calibrations.json` pour l'ensemble des
sites enregistrés. Le panneau de contrôle temporaire reste visible en haut à
droite de la fenêtre pour éviter qu'il soit masqué sous le viewer.

Pour vérifier aussi les sites encore en préparation, sans les publier, ajouter
`--pending-sites` à la commande. Le gestionnaire expose alors temporairement
les paquets pending locaux et restaure les manifestes, assets et statuts à
`Ctrl-C` :

```sh
npm run camera-calibration -- --pending-sites --host localhost --port 3010
```

Les quatre paquets pending de la v1.5 deviennent ainsi accessibles dans leur
route locale de vérification. Plate aux Mérous et Pierre du Jas ne sont pas
exposés séparément : ils ont été regroupés dans l'emprise de Les Magnons. Les
paquets pending restent
`web.published: false`, absents du terrain public, du sitemap et du build de
release. L'overlay réutilise les dérivés de page locaux archivés, mais copie
toujours le terrain interactif depuis le paquet régional courant afin que les
emprises, masques et poses calibrées les plus récents soient effectivement
affichés.

À l'arrêt du serveur avec `Ctrl-C`, le gestionnaire retire automatiquement
l'interface du working tree. Vérifier avant une release :

```sh
npm run camera-calibration:status
npm run camera-calibration:check-release
```

## Commandes de secours

Le gestionnaire peut être appelé directement depuis la racine du dépôt :

```sh
python3 tools/camera-calibration/manage.py enable
python3 tools/camera-calibration/manage.py disable
python3 tools/camera-calibration/manage.py status
```

`enable` et `disable` refusent d'écraser des modifications concurrentes dans
`TerrainViewer.tsx` ou `globals.css`. Si une évolution de ces fichiers rend le
patch incompatible, mettre à jour l'outil explicitement plutôt que de forcer
son application.

Le contrôle de release reste explicite afin que le build Web demeure autonome
lorsque seul `apps/web` est publié. La suite de tests vérifie également que les
marqueurs propres à l'interface de calibration sont absents du viewer livré.

## Provenance versionnée

- `3eff486` introduit l'interface locale et l'enregistrement par site ;
- `6967082` ajoute l'export d'une collection JSON unique ;
- `76a561a` retire l'interface du produit et constitue le patch réversible
  utilisé par `manage.py`.

Les données finales ne dépendent pas de cet outil : chaque configuration de
site conserve ses paramètres lisibles et sa pose exacte
`camera_position_m` / `camera_target_m`. La méthode de conversion et l'ordre de
régénération sont détaillés dans
[`cartography/CAMERA-CALIBRATION.md`](../../cartography/CAMERA-CALIBRATION.md).
