# QA site-local v1.5 — Impérial du Milieu, Riou

Date de contrôle : 2026-08-15
Slug : `imperial-du-milieu-riou`
Région : `bouches-du-rhone`

## Périmètre et état de publication

Ce paquet concerne uniquement `Impérial du Milieu – Riou`. La configuration conserve `web.published=false`. Le manifeste régional de planning ne porte qu'une correction de layout pour ce slug; aucun inventaire, manifeste terrain publié ou global, route, sitemap, composant Web partagé, release, push ou déploiement n'a été modifié.

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

Paramètres exportés et reportés dans la configuration : `zoom=0.84`, `orbitAzimuthDeg=0`, `cameraElevationDeg=33.42`, `panRightM=11.33`, `panUpM=43.2`, offsets `0/0`, avec `cameraPositionM=[-11.3258,547.6336,911.8899]` et `cameraTargetM=[-11.3258,-33.1664,31.8899]`.

La calibration provient de `/Users/follm/Downloads/divetopo-camera-calibrations-2.json`, conservé hors dépôt. Schéma `divetopo-camera-calibration-collection-v1`, `exportedAt=2026-08-15T06:21:38.384Z`, SHA-256 `18269204b26988ad94ccb6decb60ff032d553492a74e3fa50a33ece70e5ae6ce`. L'entrée cible unique concorde avec la configuration; le JSON brut n'est pas copié dans Git.

Le bouton utilisé est l'export groupé `Télécharger toutes les calibrations`; aucun téléchargement JSON par site n'a été ajouté. L'interface de calibration n'est pas présente sur la route locale normale et n'est pas présente dans le viewer publié.

## Paquet produit

- Deux plans 2D canoniques : `2474 × 1712` px.
- Deux vues 3D statiques canoniques : `2474 × 1712` px, régénérées depuis les captures de la nouvelle pose initiale validée.
- Deux planches canoniques : `5400 × 4600` px.
- Locator site-local : `1864 × 1440` px, avec le marqueur exact.
- Terrain interactif canonique et Web : grille `360 × 400`, deux textures, hauteur 16 bits, masque de validité, masque d'isobathes et vecteurs; export validé, masque de validité final 100 %, payload vecteur `53,112` octets.
- Les sept artefacts canoniques du terrain (`terrain.json`, hauteurs, masques, vecteurs et deux textures) sont bit à bit identiques à l'emprise précédente : la calibration ne modifie pas la géométrie.
- Les dérivés Web pending ont été générés et QA-ables dans un overlay local réversible uniquement, puis retirés. Aucun actif pending n'est conservé sous `apps/web/public`; aucun manifeste terrain publié, route ou sitemap n'a été modifié.

Méthode : isobathes vectorielles méditerranéennes lissées et suréchantillonnées, verrouillées aux profondeurs canoniques de 5 m, avec séparation stricte des zones NoData et conservation du relief naturel.

## QA effectuée

- Inspection pleine résolution des plans 2D inchangés, des deux vues 3D statiques, des deux planches, du locator et du raster régional; nord, échelle, cartouches, traits, sources et licences restent visibles.
- Overlay local FR à `1280 × 720` et `390 × 844` : terrain prêt, bascule `Vue aérienne` → `Topographie`, réinitialisation de vue, thème clair/sombre et navigation clavier vérifiés sans erreur console.
- Route anglaise locale : titre, contenus anglais, thèmes clair/sombre, dropdown mobile et overflow `390` px vérifiés. La route propre régionale garde six repères, cinq liens publiés; le repère cible pending est un point inertiel sans lien, et la route pending cible répond `404` hors overlay.
- Le cartouche régional corrigé est maintenant compact, immédiatement à gauche du point : `side=left`, `shift_y_rem=-0.8`, `label_offset_rem=2.5`, `width_rem=6.5`, avec les lignes `Impérial du` / `Milieu – Riou`. Le connecteur réellement rendu est droit et mesure `19.73 px` du centre du point au bord du cartouche.
- Mesures navigateur à `1280 × 720`, carte `336 × 259.57 px` : aucune collision, aucun débordement et aucune intersection avec l’échelle ou le nord. Le cartouche cible est séparé de Grotte à Corail de `2.88 px` et de Pains de Sucre de `5.18 px`.
- Mesures navigateur à `390 × 844`, carte `366 × 282.74 px` : aucune collision, aucun débordement et aucune intersection réservée; marges verticales de `5.72 px` avec Grotte à Corail et `4.92 px` avec Pains de Sucre. La capture mobile confirme que le cartouche, le point et le trait sont entièrement visibles.
- Cohérence capture/dérivé Web, réduction `160 × 111` : orthophoto desktop `0.999463`, topographique desktop `0.998787`, orthophoto mobile `0.995115`, topographique mobile `0.983938`. Un second chargement stabilisé de la topographie mobile est identique au premier (`corrélation=1.000000`, MAE `0`); comparé au WebP généré par le même pipeline, il reste à `0.983938` (MAE `0.012955`). Le résidu sous le seuil historique `0.985` est donc stable et attribué à la réduction/encodage WebP, pas à une instabilité de pose.

## Défauts et incertitudes conservés

- La lacune offshore de 4.2 % est explicitement conservée; elle n'est pas interpolée dans le terrain.
- Le drapé orthophoto 3D est plus doux et étiré que la vue aérienne 2D, conformément à la projection du terrain interactif; il reste aligné avec les isobathes et la côte.
- Les trois coordonnées officielles de mouillage sont un groupe de contexte; le point principal retenu ne doit pas être interprété comme une zone d'accès ou de sécurité.
- Le seuil métrique WebP mobile reste un résidu QA à surveiller avant une éventuelle publication. La route propre laisse le pending inertiel sans cartouche ni lien, conformément au contrat de publication; aucun actif pending n'est conservé dans `apps/web/public`.
