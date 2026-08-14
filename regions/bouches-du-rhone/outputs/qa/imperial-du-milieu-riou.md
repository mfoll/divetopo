# QA site-local v1.5 — Impérial du Milieu, Riou

Date de contrôle : 2026-08-14
Slug : `imperial-du-milieu-riou`
Région : `bouches-du-rhone`

## Périmètre et état de publication

Ce paquet concerne uniquement `Impérial du Milieu – Riou`. La configuration conserve `web.published=false`. Aucun inventaire régional, manifeste régional ou global, sitemap, composant Web partagé, release, push ou déploiement n'a été modifié.

La QA Web a utilisé une copie locale éphémère contenant uniquement ce site et ses actifs. La route réelle du dépôt n'a pas été rendue disponible par modification du manifeste publié.

## Identité, position et voisinage

- Point principal retenu d'après l'arrêté officiel Premar Méditerranée : `43°10.324′ N, 05°23.614′ E`, soit `43.17206667, 5.39356667`.
- Les deux autres mouillages officiels du même ensemble sont conservés comme contexte, mais ne sont pas fusionnés avec le point principal : `43°10.293′ N, 05°23.662′ E` et `43°10.270′ N, 05°23.626′ E`.
- Position de calcul en RGF93 / Lambert-93 : `[894738.371, 6233266.500]`.
- L'Impérial de Terre voisin reste distinct, à environ 97 m dans le contrôle de proximité. Le site Pains de Sucre n'est pas inclus dans l'emprise ni dans le paquet.
- Cette identité et ces coordonnées ne constituent pas une preuve d'accès, de mouillage autorisé ou de sécurité nautique.

Source officielle d'identité : [arrêté Premar Méditerranée sur les mouillages de Riou](https://www.premar-mediterranee.gouv.fr/uploads/mediterranee/arretes/8900192c4c47e1461671981c1f410d78.pdf).

## Source et référentiels

- Bathymétrie et topographie : archives Shom–IGN Litto3D PACA 2015, dalles MNT 1 m des prépaquets `0890_6235` et `0895_6235`.
- Référentiel horizontal : RGF93 / Lambert-93, EPSG:2154.
- Référentiel vertical : IGN69.
- Orthophoto : IGN BD ORTHO, couche `HR.ORTHOIMAGERY.ORTHOPHOTOS`, date contrôlée `2023-06-24`.
- NoData terrain conservé à `-99999`; aucun remplissage artificiel n'a été ajouté.

Sources produit : [Shom–IGN Litto3D PACA 2015](https://diffusion.shom.fr/donnees/litto3d-paca-2015.html), [spécification Litto3D](https://diffusion.shom.fr/media/wysiwyg/pdf/DC_Litto3D.pdf) et [IGN BD ORTHO](https://cartes.gouv.fr/rechercher-une-donnee/dataset/IGNF_BD-ORTHO).

## Couverture et emprises

Contrôle des fenêtres carrées sur les MNT bruts, avec le dénominateur de surface complet :

- 50 m : 100.0 % valide.
- 150 m : 90.8 % valide, contre 90.7 % dans le tableau de départ.
- 300 m : 63.8 % valide, contre 63.3 % dans le tableau de départ. L'écart résiduel est conservé comme différence de masque/dénominateur entre le contrôle brut actuel et le tableau de départ.

Mesures complémentaires :

- Contexte `[894400, 6233200, 895000, 6233800]` : 600 × 600 m, 94.8619 % valide, valeurs `-46.93` à `+187.71` m.
- Focus `[894450, 6233200, 894950, 6233700]` : 500 × 500 m, 95.912 % valide, valeurs `-46.40` à `+182.97` m.
- Empreinte interactive `[894520, 6233200, 894880, 6233600]` : 360 × 400 m, masque final 100 % valide.
- Profondeur brute au point principal : environ `-25.80` m.
- Le paquet verrouille `45` m comme profondeur maximale de plan et d'interactif; les métadonnées source atteignent environ `-47.38` m et `+190.83` m.

Une lacune offshore de 4.2 % de l'emprise 2D ne contient ni bathymétrie ni altitude. Elle est affichée avec la couleur de profondeur maximale, mais reste exclue des isobathes et du terrain. Cette limite est visible et documentée, sans fabrication de relief.

## Pose 3D validée localement

Le gestionnaire prévu `tools/camera-calibration/manage.py` a réactivé l'interface uniquement dans la copie de développement locale, puis l'a retirée du worktree (`camera-calibration:check-release` doit rester désactivé pour le produit livré). La caméra a été déplacée et zoomée, le cadrage a été enregistré, puis exporté dans une collection JSON unique contenant exactement le slug demandé.

Paramètres exportés et reportés dans la configuration : `zoom=0.65`, `orbitAzimuthDeg=0`, `cameraElevationDeg=33.42`, `panRightM=3.56`, `panUpM=10.36`, avec `cameraPositionM=[-3.5627,575.0452,893.7982]` et `cameraTargetM=[-3.5627,-5.7548,13.7982]`.

Le bouton utilisé est l'export groupé `Télécharger toutes les calibrations`; aucun téléchargement JSON par site n'a été ajouté. L'interface de calibration n'est pas présente sur la route locale normale et n'est pas présente dans le viewer publié.

## Paquet produit

- Deux plans 2D canoniques : `2474 × 1712` px.
- Deux vues 3D statiques canoniques : `2474 × 1712` px, recopiées depuis les captures de la pose initiale validée.
- Deux planches canoniques : `5400 × 4600` px.
- Locator site-local : `1864 × 1440` px, avec le marqueur exact.
- Terrain interactif canonique et Web : grille `360 × 400`, deux textures, hauteur 16 bits, masque de validité, masque d'isobathes et vecteurs; export validé, masque de validité final 100 %, payload vecteur `53,112` octets.
- Dérivés Web : 2D topographique/orthophoto, captures 3D topographique/orthophoto en `960`, `1600` et `2474` px, variantes mobiles `960` px, téléchargements JPEG pleine taille et aperçus de planches `1800 × 1533` px.

Méthode : isobathes vectorielles méditerranéennes lissées et suréchantillonnées, verrouillées aux profondeurs canoniques de 5 m, avec séparation stricte des zones NoData et conservation du relief naturel.

## QA effectuée

- Inspection pleine résolution des plans, des deux vues 3D statiques, des deux planches, du locator, des deux textures interactives et de tous les dérivés Web représentatifs desktop/mobile.
- Route française locale : identité, absence d'écran blanc, absence d'overlay framework, terrain prêt, bascule `Vue aérienne` → `Topographie` vérifiée par changement d'état.
- Route anglaise locale : titre et contenus anglais vérifiés.
- Desktop et mobile vérifiés pour les routes FR et EN; le panneau de calibration reste absent sur les routes normales.
- Vérification de cohérence des captures : corrélations `0.9985 / 0.9993` orthophoto desktop, `0.9946` orthophoto mobile, `0.9980 / 0.9990` topographique desktop, `0.9894` topographique mobile; toutes les comparaisons passent.

## Défauts et incertitudes conservés

- La lacune offshore de 4.2 % est explicitement conservée; elle n'est pas interpolée dans le terrain.
- Le drapé orthophoto 3D est plus doux et étiré que la vue aérienne 2D, conformément à la projection du terrain interactif; il reste aligné avec les isobathes et la côte.
- Les trois coordonnées officielles de mouillage sont un groupe de contexte; le point principal retenu ne doit pas être interprété comme une zone d'accès ou de sécurité.
