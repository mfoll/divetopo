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
sites enregistrés.

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
