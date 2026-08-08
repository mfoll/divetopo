# Pointe de la Causinière, Saint-Jean-Cap-Ferrat · provenance et QA v1.4

## Identité et périmètre

Le site livré est la Pointe de la Causinière. Il n’englobe ni l’Arche au large, tombant distinct décrit jusqu’à environ 65 m, ni le Plateau du Grand Hôtel / émissaire.

Le marqueur primaire provient du point R de l’arrêté maritime préfectoral : 43°40.481′ N, 007°19.860′ E, soit 43.6746833333, 7.3310000000 et EPSG:2154 `[1049180.679, 6295761.403]`. La carte officielle de Saint-Jean-Cap-Ferrat confirme l’identité de la pointe. Le contrôle local Mapcarta/GeoNames, 43.67476, 7.33106, n’est pas utilisé comme source primaire.

Sources d’identité :

- carte municipale : https://www.saint-jean-cap-ferrat.fr/wp-content/uploads/2023/12/FLYER-GUIDIGO-ADULTES-francais-web.pdf ;
- arrêté maritime préfectoral : https://www.premar-mediterranee.gouv.fr/uploads/mediterranee/arretes/303cf3590cc9de2d1316bf1259732165.pdf ;
- distinction locale Pointe / Arche / Plateau du Grand Hôtel : https://dive-sites.olivierlecorre.com/nice/site-plongee-ferrat-emissaire.html ;
- fiche ZNIEFF de la pointe Causinière : https://piece-jointe-carto.developpement-durable.gouv.fr/REG093B/pdf/fiches/znieff/93M000015.pdf.

## MNT Shom–IGN et continuité

Source : Shom–IGN Litto3D PACA 2015, paquet officiel `1045_6300.7z`, SHA-256 `2fae20c908db4f0b224e26c18ec28d3665d1e2f9924aff32941ff31f9b717633`.

URL exacte : `https://services.data.shom.fr/INSPIRE/telechargement/prepackageGroup/LITTO3D_PACA_2015_PACK_DL/prepackage/1045_6300/file/1045_6300.7z`.

Membre exact : `1045_6300/LITTO3D_FRA_1049_6296_20150529_LAMB93_RGF93_IGN69/MNT1m/LITTO3D_FRA_1049_6296_MNT_20150128_LAMB93_RGF93_IGN69.asc`.

Le MNT est métrique, RGF93 / Lambert-93 EPSG:2154, référentiel vertical IGN69. Le focus final `[1049000, 6295624, 1049264, 6295819]` mesure 264 × 195 m : 100 % des 51 480 cellules sont valides, sans bordure NoData ouverte, pour une plage brute d’environ −41,35 à +10,06 m. Le contrôle complémentaire des isobathes métriques de la Métropole Nice Côte d’Azur reste : https://www.data.gouv.fr/datasets/bathymetrie.

L’emprise interactive orientée mesure 200 × 280 m, centre `[1049180.679, 6295780]`, azimut 110°. Les 56 723 cellules source à l’intérieur sont valides à 100 %. Le paquet rééchantillonné atteint −39,78 m. `deep_edge_nodata_terrain_fill=false` : aucun trou, raccord d’isobathes ou plateau artificiel n’est créé.

## Orthophoto officielle

Flux officiel IGN : `https://data.geopf.fr/wms-r/wms`, couche `HR.ORTHOIMAGERY.ORTHOPHOTOS`, WMS 1.3.0, EPSG:2154.

Le `GetFeatureInfo` au marqueur retourne `pva=2023`, `res=20` et `date_vol=2023-07-10Z`. La date configurée est donc `2023-07-10`.

Extraits strictement nécessaires, non commités :

- focus : bbox `[1049000, 6295624, 1049264, 6295819]`, 528 × 390 px à 0,5 m, réponse brute SHA-256 `ba6ac846d598082ed80800fb95f8f89bd5368ef5df62b5fa574f3dce71e16e1c` ;
- contexte : bbox `[1049000, 6295560, 1049350, 6296000]`, 700 × 880 px à 0,5 m, réponse brute SHA-256 `1abb5679995a3fb2870c45be79d57feb724fdf359deba8aeb78491d7f12f1de2`.

Le WMS encode le nom de projection comme `EPSG:2154` dans un WKT non canonique. Les copies de travail ont uniquement reçu le WKT EPSG:2154 canonique avant validation ; aucune valeur de pixel n’a été modifiée.

## Livrables et QA visuelle

Les quatre statiques font 1600 × 1184 px : plans 2D topographique et orthophoto, perspectives 3D topographique et orthophoto. Le focus resserré supprime la bordure NoData auparavant rejetée. Les contours 3D sont drapés sur la surface, avec supersampling ×2 ; les projections obliques traversantes du brouillon précédent ont disparu.

Les deux planches font 5400 × 3250 px. Le locator site-spécifique fait 1864 × 1440 px et marque explicitement la pointe sur le relief régional existant. Les six images ont été inspectées à leur définition native : cadrage, littoral, continuité terre-mer, isobathes, étiquettes, compas, échelle, crédits et absence de substitution orthophoto ont été contrôlés.

## Terrain interactif et dérivés Web

Le paquet canonique contient `terrain.json`, `height.bin`, `valid-mask.bin`, `isobath-mask.bin`, `isobaths-vector.json`, `topographic.webp` et `orthophoto.webp`. Grille : 333 × 284 sommets, 187 912 triangles, sept polylignes vectorielles et 637 points d’isobathes. La copie Web est bit-à-bit identique au paquet canonique.

La vraie route temporaire construite depuis le code Web `e9b38a036cdad5bb0d24e26009fdefb7be7501a9` a été inspectée en topographie et orthophoto, desktop 2474 × 1712 et mobile 960 × 662. Les contrôles portent sur le chargement WebGL, les deux textures, les isobathes, le compas, l’échelle, les crédits et le cadrage initial.

Équivalence initiale, seuil contractuel 0,985 :

- orthophoto desktop WebP : corrélation 0,9990, MAE 0,0054 ;
- orthophoto desktop JPEG HD : corrélation 0,9996, MAE 0,0037 ;
- orthophoto mobile : corrélation 0,9963, MAE 0,0082 ;
- topographie desktop WebP : corrélation 0,9993, MAE 0,0046 ;
- topographie desktop JPEG HD : corrélation 0,9997, MAE 0,0033 ;
- topographie mobile : corrélation 0,9969, MAE 0,0070.

Les dérivés site-spécifiques attendus sont présents : plans Web, aperçus des deux planches, WebP 960/1600/2474, WebP mobile et JPEG HD pour les deux styles. Aucun manifeste agrégé n’est inclus.

`web.published` reste `false`. Aucun `region.json`, carte régionale, manifeste agrégé, accueil, version, release, autre site, push ou déploiement n’est modifié.
