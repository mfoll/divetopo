# Pointe de la Causinière, Saint-Jean-Cap-Ferrat · provenance et QA

## Décision de périmètre

Le site livré est la pointe elle-même, pas l’ensemble des appellations de plongée voisines. La source locale distingue :

- la Pointe de la Causinière, tombant côtier d’environ 30–45 m ;
- l’Arche au large, tombant séparé documenté jusqu’à environ 65 m ;
- le Plateau du Grand Hôtel / émissaire, secteur distinct souvent confondu avec la pointe.

La pointe est identifiée par la carte officielle de Saint-Jean-Cap-Ferrat et par le point R de l’arrêté maritime préfectoral, 43°40.481′ N, 007°19.860′ E, soit 43.6746833333, 7.3310000000 et EPSG:2154 [1049180.679, 6295761.403]. Le contrôle local Mapcarta/GeoNames donne 43.67476, 7.33106, à quelques mètres ; il n’est pas utilisé comme source primaire du marqueur.

## Sources

- Carte municipale : https://www.saint-jean-cap-ferrat.fr/wp-content/uploads/2023/12/FLYER-GUIDIGO-ADULTES-francais-web.pdf
- Arrêté maritime préfectoral : https://www.premar-mediterranee.gouv.fr/uploads/mediterranee/arretes/303cf3590cc9de2d1316bf1259732165.pdf
- Distinction locale Pointe / Arche / Plateau du Grand Hôtel : https://dive-sites.olivierlecorre.com/nice/site-plongee-ferrat-emissaire.html
- Fiche ZNIEFF de la pointe Causinière : https://piece-jointe-carto.developpement-durable.gouv.fr/REG093B/pdf/fiches/znieff/93M000015.pdf
- Contrôle métrique d’isobathes Métropole Nice Côte d’Azur : https://www.data.gouv.fr/datasets/bathymetrie
- MNT source Shom–IGN Litto3D PACA 2015 : https://diffusion.shom.fr/donnees/litto3d-paca-2015.html

## MNT et continuité

Le paquet local `1045_6300.7z` a été contrôlé sans téléchargement supplémentaire. La provenance exacte configurée est :

`https://services.data.shom.fr/INSPIRE/telechargement/prepackageGroup/LITTO3D_PACA_2015_PACK_DL/prepackage/1045_6300/file/1045_6300.7z`

Membre utilisé : `1045_6300/LITTO3D_FRA_1049_6296_20150529_LAMB93_RGF93_IGN69/MNT1m/LITTO3D_FRA_1049_6296_MNT_20150128_LAMB93_RGF93_IGN69.asc`.

La dalle est métrique, en RGF93 / Lambert-93 EPSG:2154, référentiel vertical IGN69. Dans le focus 300 × 222 m livré, environ 97 % des pixels bruts sont valides ; le composant bathymétrique principal atteint localement environ −40 m. Les NoData restent des NoData ; aucun raccord entre fragments d’isobathes n’est transformé en MNT. L’Arche au large, à environ −65 m dans la source locale, est donc volontairement exclue de ce site.

## Sorties statiques

- 2D : `../outputs/pointe-causiniere-cap-ferrat-topobathy-2d.jpg`
- 3D : `../outputs/pointe-causiniere-cap-ferrat-topobathy-3d.jpg`
- Résolution de sortie : 1600 × 1184 px.
- QA visuelle plein format : coastline, transitions terre-mer, isobathes disponibles et cadrage vérifiés ; les NoData de la limite sud restent visibles, et le cadrage 3D utilise un crop explicite 200 × 260 m pour supprimer la bordure tournée NoData, sans remplissage de terrain.
- Le pied de carte 3D est volontairement abrégé ; la provenance complète et la dalle exacte sont conservées dans le JSON ci-joint.

## Interactif Web

**Bloqué / incomplet, non livré dans ce commit.** Le générateur interactif actuel exige une orthophoto IGN BD ORTHO locale pour produire le paquet `terrain.json`, les textures et leurs métadonnées. La métadonnée WMS officielle accessible indique une couverture 2023-07-10, mais l’image n’était pas déjà disponible localement et n’a pas été téléchargée pour cette clôture. Aucun fichier topographique n’est dupliqué ou présenté comme orthophoto. La géométrie MNT seule reste suffisante pour les sorties statiques limitées à la Pointe et −40 m, mais ne justifie pas à elle seule un paquet Web complet selon le contrat actuel.

`web.published` reste `false` dans le JSON. Aucun manifeste régional ou global n’est modifié.
