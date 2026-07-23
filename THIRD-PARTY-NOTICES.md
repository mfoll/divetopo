# Donnees tierces, licences et attributions

Cette notice decrit les donnees incorporees aux rendus. L'audit du 22 juillet 2026 conclut que la reutilisation non commerciale realisee par ce projet est permise sous reserve des attributions, du partage a l'identique impose par HYSCORES et des avertissements ci-dessous.

## Bathymetrie detaillee : HYSCORES 2015

- Jeu de donnees : *MNT Bathymetrique a haute resolution des fonds marins des zones recifales de la cote ouest de l'ile de La Reunion (2015)*.
- Auteurs : Pascal Mouquet, Touria Bajjouk et Michel Ropert.
- Editeur : Ifremer - Delegation Ocean Indien.
- DOI : <https://doi.org/10.12770/ee059de2-2c81-46ce-88de-0fb5517046af>
- Metadonnee officielle : <https://sextant.ifremer.fr/geonetwork/srv/api/records/ee059de2-2c81-46ce-88de-0fb5517046af>
- Licence indiquee : Creative Commons BY-NC-SA; la metadonnee ne precise pas le numero de version.
- Attribution imposee : `Projet HYSCORES (Ifremer, UBO, Office de l'Eau Reunion)`.

Les profondeurs absentes des images hyperspectrales HYSCORES ont ete completees dans le produit diffuse par le MNT Litto3D 2009-2010, reechantillonne a 40 cm. Le pipeline ne telecharge donc pas un second jeu Litto3D independant : il utilise le raster composite fourni par l'Ifremer, tout en conservant la mention Litto3D dans les credits.

Le projet extrait le raster, interpole et lisse la surface, calcule des isobathes et produit un nouveau rendu. Cette transformation constitue une adaptation. La clause ShareAlike exclut donc une licence de sortie CC BY-NC-ND et conduit a publier les cartes sous CC BY-NC-SA 4.0.

## Topographie : IGN RGE ALTI

- Produit : IGN RGE ALTI, couche WMS `ELEVATION.ELEVATIONGRIDCOVERAGE.HIGHRES`.
- Service : <https://data.geopf.fr/wms-r/wms>
- Fiche : <https://cartes.gouv.fr/rechercher-une-donnee/dataset/IGNF_RGE-ALTI>
- Licence : [Licence Ouverte 2.0](https://www.etalab.gouv.fr/licence-ouverte-open-licence/).
- Attribution : `IGN RGE ALTI`.
- Etat temporel : la fiche indique que la mise a jour du produit a ete arretee en 2024; metadonnee revisee le 8 decembre 2025.

La Licence Ouverte 2.0 autorise la reproduction, la transformation, la redistribution et les usages commerciaux sous reserve de citer le producteur et la date de mise a jour. Le lissage, la fusion avec le MNT marin et les rendus 2D/3D du projet sont donc permis.

## Orthophoto : IGN BD ORTHO

- Produit : IGN BD ORTHO, couche WMS `HR.ORTHOIMAGERY.ORTHOPHOTOS`.
- Service : <https://data.geopf.fr/wms-r/wms>
- Fiche : <https://cartes.gouv.fr/rechercher-une-donnee/dataset/IGNF_BD-ORTHO>
- Licence : Licence Ouverte 2.0.
- Attribution : `IGN BD ORTHO`.
- Images utilisees : resolution 20 cm; prises de vue du 22 juillet 2025 au Cap La Houssaye et a Boucan Canot, et du 2 aout 2025 a la Passe de l'Hermitage. Ces dates proviennent d'une requete `GetFeatureInfo` au repere de chaque site; la metadonnee du produit a ete revisee le 9 juillet 2026.

Le decoupage au masque terrestre et le drapage sur le relief sont autorises par la Licence Ouverte 2.0, avec conservation de l'attribution et de la date propre a chaque image source.

## Relief marin insulaire : GEBCO 2024

- Couche WMS epinglee : `GEBCO_2024`.
- Service versionne : <https://wms.gebco.net/2024/mapserv>.
- Conditions : <https://www.gebco.net/data-products/gridded-bathymetry/terms-of-use>
- Attribution requise : `GEBCO Compilation Group (2024) GEBCO 2024 Grid (doi:10.5285/1c44ce99-0a0d-5f4f-e063-7086abc0ea0f)`.

L'endpoint et la couche versionnes sont conserves dans le pipeline afin qu'une future mise a jour de l'alias `GEBCO_LATEST` ne change pas silencieusement les cartes publiees. GEBCO place cette grille dans le domaine public et autorise la copie, l'adaptation et l'exploitation commerciale. La source doit etre reconnue, aucune approbation de GEBCO, de l'OHI ou de la COI ne doit etre suggeree, et les donnees ne doivent pas etre presentees de maniere trompeuse.

**Avertissement GEBCO : cette grille ne doit pas etre utilisee pour la navigation ni pour une finalite impliquant la securite en mer.** Sa resolution nominale de 15 secondes d'arc ne represente pas la precision des mesures sous-jacentes. Elle n'est utilisee ici que pour le relief generalise de la carte de localisation de l'ile, jamais pour les plans detailles du site.
