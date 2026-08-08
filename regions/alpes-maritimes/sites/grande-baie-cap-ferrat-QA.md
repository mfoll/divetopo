# QA — Grande Baie, Saint-Jean-Cap-Ferrat

## Statut de livraison

Le site est livré en relief statique uniquement. `web.published` reste `false` et `plate_relief_source` vaut `static`.

Sorties produites :

- `regions/alpes-maritimes/outputs/grande-baie-cap-ferrat-topobathy-2d.jpg`
- `regions/alpes-maritimes/outputs/grande-baie-cap-ferrat-topobathy-3d.jpg`

Le paquet interactif n'est pas livré. Le générateur interactif du dépôt exige une orthophoto valide et refuse honnêtement la génération sans les deux textures orthophoto. La réponse IGN WMS reçue pendant l'essai a été rejetée par le contrôle de contenu comme image constante ; aucun fichier de remplacement n'a été fabriqué ni conservé. Aucune nouvelle acquisition n'est engagée dans cette livraison.

## Coordonnées et recoupement

La fiche locale du comité départemental FFESSM 06 recense `Grande Baie (x2)` à Saint-Jean-Cap-Ferrat et donne les deux positions WGS84 : [CD06.pdf](https://codep06.ffessm.fr/wp-content/uploads/CD06.pdf). La notation publiée mélange degrés, minutes et secondes ; elle a été normalisée comme suit, après contrôle géographique et MNT :

- mouillage ouest retenu : `43°41′10″N, 7°19′17″E` → `43.686111111, 7.321388889` → Lambert-93 `1048337.102, 6296987.064` ; profondeur Litto3D au pixel : `−34.33 m` ;
- second mouillage mentionné par la fiche : `43°41′01.797″N, 7°19′71.154″E`, normalisé pour les secondes excédentaires → `43.683832500, 7.336431667` → `1049562.348, 6296800.691`.

L'interprétation en degrés-minutes décimales placerait un des points à terre ; elle n'a donc pas été retenue. Le nom du site et son contexte sont recoupés par la [fiche officielle Côte d'Azur France](https://provence-alpes-cotedazur.com/decouvrir/espaces-naturels/patrimoine-naturel/site-de-plongee-de-la-grande-baie-saint-jean-cap-ferrat-fr-3410978/), l'étude officielle [Métropole Nice Côte d'Azur — étude plongée](https://www.dirm.mediterranee.developpement-durable.gouv.fr/IMG/pdf/mnca_2019_etudeplongee_version_finale.pdf), et la description locale [Nausicaa Plongée](https://www.nausicaa-plongee.com/sites-de-plongees). Ces sources confirment le site de plongée et le tombant, mais la coordonnée de travail vient de la fiche FFESSM.

## MNT Litto3D

Source officielle auditée : [paquet Shom–IGN Litto3D PACA 2015, dalle 1045_6300](https://services.data.shom.fr/INSPIRE/telechargement/prepackageGroup/LITTO3D_PACA_2015_PACK_DL/prepackage/1045_6300/file/1045_6300.7z).

- SHA-256 du paquet téléchargé : `2fae20c908db4f0b224e26c18ec28d3665d1e2f9924aff32941ff31f9b717633` ;
- maillage : `1 m` ; système planimétrique : `RGF93 / Lambert-93`, EPSG:2154 ; référentiel vertical : `IGN69` ; date MNT des métadonnées : `16/01/2015` ;
- membres utilisés pour l'emprise livrée : dalles `1048_6297`, `1048_6298`, `1049_6297`, `1049_6298`, toutes en `MNT1m` ;
- emprise focus : `[1048300, 6296600, 1048900, 6297100]` ; emprise contexte : `[1048200, 6296500, 1049000, 6297200]` ;
- le raster brut signé est conservé pour la topographie et la bathymétrie ; la profondeur positive est dérivée uniquement des altitudes négatives ; les NoData sont conservés ; aucune interpolation n'est appliquée.

Contrôles sur le raster focus : `85.95 %` de cellules valides, `21.34 %` de cellules marines, `9.31 %` à au moins `20 m`, `1.43 %` à au moins `40 m`, minimum `−45.60 m`. Le mouillage retenu est dans le composant marin connecté contenant `99.99 %` des cellules marines du focus. La couverture utile est donc une bande côtière source-connectée, pas un MNT continu sur toute la baie ; les 14.1 % de NoData du plan et 21.2 % du crop 3D restent visibles ou sont exclus du maillage.

## QA de rendu

Commandes exécutées dans l'environnement de build temporaire :

```text
python -m cartography.regions.alpes_maritimes regions/alpes-maritimes/sites/grande-baie-cap-ferrat.json --check
python -m cartography.regions.alpes_maritimes regions/alpes-maritimes/sites/grande-baie-cap-ferrat.json --render-only
```

Inspection plein format effectuée sur les deux JPEGs :

- plan 2D : emprise source lisible, nord et échelle présents, NoData gris non masqué abusivement, labels `−5 m`, `−20 m` et `−40 m` séparés et lisibles, attribution et licence visibles ;
- relief 3D : regard initial vers l'est (`90°`), côte et tombant cadrés, isobathes source-dérivées visibles, facettes hors couverture omises sans plateau artificiel, attribution et licence visibles ;
- la QA confirme que les sorties sont des rendus statiques de la couverture Litto3D disponible et ne doivent pas être interprétées comme une interpolation au-delà des cellules source.
