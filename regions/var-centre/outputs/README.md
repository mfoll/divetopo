# Sorties canoniques du Var Centre

Ce dossier est la racine canonique des rendus et paquets de la région. Les
dérivés Web restent des copies de publication et ne deviennent jamais la source
de vérité.

## Carte régionale

```text
var-centre-regional-relief.png
var-centre-regional-relief.json
```

Ces deux fichiers sont réservés mais absents du commit régional intermédiaire.
Ils seront produits par le builder régional partagé avec une emprise propre au
Var Centre; le raster PACA et ses bornes ne doivent pas servir de substitut. Le
PNG servira de source à la fiche de la page d'accueil et à la future page
régionale. Le JSON associé conservera au minimum les dimensions, l'emprise, les
sources, les couches, les paramètres de rendu et les hashes des entrées.

## Sorties par site

Pour un slug `<site>`, les noms canoniques sont :

```text
<site>-topobathy-2d.jpg
<site>-topobathy-2d-ortho.jpg
<site>-topobathy-3d.jpg
<site>-topobathy-3d-ortho.jpg
<site>-locator-var-centre.jpg
<site>-planche.jpg
<site>-planche-topographique.jpg
interactive-terrain/<site>/
```

Les deux sites déjà publiés sont déplacés octet pour octet lorsque leur QA ne
requiert aucune correction. Les SHA-256 avant/après font partie de la preuve de
migration. Aucun nouveau site ni artefact de brouillon ne rejoint un manifeste
public sans QA complète et décision explicite.
