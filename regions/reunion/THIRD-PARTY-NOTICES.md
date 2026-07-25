# Third-party data, licenses, and attributions

This notice describes the data incorporated into the rendered outputs. The audit conducted on July 22, 2026 concluded that the non-commercial reuse undertaken by this project is permitted, subject to the required attributions, the ShareAlike condition imposed by HYSCORES, and the warnings below.

## Detailed bathymetry: HYSCORES 2015

- Dataset: *MNT Bathymétrique à haute résolution des fonds marins des zones récifales de la côte ouest de l'île de La Réunion (2015)*.
- Authors: Pascal Mouquet, Touria Bajjouk, and Michel Ropert.
- Publisher: Ifremer - Délégation Océan Indien.
- DOI: <https://doi.org/10.12770/ee059de2-2c81-46ce-88de-0fb5517046af>
- Official metadata: <https://sextant.ifremer.fr/geonetwork/srv/api/records/ee059de2-2c81-46ce-88de-0fb5517046af>
- Stated license: Creative Commons BY-NC-SA; the metadata does not specify a version number.
- Required attribution: `Projet HYSCORES (Ifremer, UBO, Office de l'Eau Reunion)`.

Depths missing from the HYSCORES hyperspectral imagery were filled in within the distributed product using the 2009-2010 Litto3D DTM, resampled to 40 cm. The pipeline therefore does not download a second, independent Litto3D dataset: it uses the composite raster supplied by Ifremer while retaining the Litto3D credit.

The project extracts the raster, interpolates and smooths the surface, computes isobaths, and produces a new rendering. This transformation constitutes an adaptation. The ShareAlike condition therefore rules out licensing the outputs under CC BY-NC-ND and leads to the maps being published under CC BY-NC-SA 4.0.

## Topography: IGN RGE ALTI

- Product: IGN RGE ALTI, WMS layer `ELEVATION.ELEVATIONGRIDCOVERAGE.HIGHRES`.
- Service: <https://data.geopf.fr/wms-r/wms>
- Dataset page: <https://cartes.gouv.fr/rechercher-une-donnee/dataset/IGNF_RGE-ALTI>
- License: [Licence Ouverte 2.0](https://www.data.gouv.fr/pages/legal/licences/etalab-2.0).
- Attribution: `IGN RGE ALTI`.
- Temporal status: the dataset page states that product updates were discontinued in 2024; the metadata was revised on December 8, 2025.

The Licence Ouverte 2.0 permits reproduction, transformation, redistribution, and commercial use, provided that the producer and update date are cited. The project's smoothing, merging with the marine DTM, and 2D/3D renderings are therefore permitted.

## Orthophotography: IGN BD ORTHO

- Product: IGN BD ORTHO, WMS layer `HR.ORTHOIMAGERY.ORTHOPHOTOS`.
- Service: <https://data.geopf.fr/wms-r/wms>
- Dataset page: <https://cartes.gouv.fr/rechercher-une-donnee/dataset/IGNF_BD-ORTHO>
- License: Licence Ouverte 2.0.
- Attribution: `IGN BD ORTHO`.
- Imagery used: the source layer is distributed at 20 cm resolution. Working GeoTIFFs are requested at 20 cm, except for Pointe au Sel, where they are requested at 40 cm. Context textures for the static 3D perspectives are requested at 20 cm for Cap La Houssaye; 40 cm for Boucan Canot, Cap Homard, and Plage du Cimetière; 50 cm for Pointe au Sel and Pont Rouge; and 80 cm for Passe de l'Hermitage. The imagery for Cap La Houssaye, Boucan Canot, Cap Homard, Pointe au Sel, Pont Rouge, and Plage du Cimetière is dated July 22, 2025; the imagery for Passe de l'Hermitage is dated August 2, 2025. These dates come from a `GetFeatureInfo` request at each site's reference point; the product metadata was revised on July 9, 2026.

Clipping with the land mask and draping over the terrain are permitted by the Licence Ouverte 2.0, provided that the attribution and the date specific to each source image are retained.

## Island-scale seafloor relief: GEBCO 2024

- Pinned WMS layer: `GEBCO_2024`.
- Versioned service: <https://wms.gebco.net/2024/mapserv>.
- Terms: <https://www.gebco.net/data-products/gridded-bathymetry/terms-of-use>
- Required attribution: `GEBCO Compilation Group (2024) GEBCO 2024 Grid (doi:10.5285/1c44ce99-0a0d-5f4f-e063-7086abc0ea0f)`.

The versioned endpoint and layer are retained in the pipeline so that a future update to the `GEBCO_LATEST` alias cannot silently change the published maps. GEBCO places this grid in the public domain and permits copying, adaptation, and commercial use. The source must be acknowledged, no endorsement by GEBCO, the IHO, or the IOC may be implied, and the data must not be presented in a misleading manner.

**GEBCO warning: this grid must not be used for navigation or for any purpose involving safety at sea.** Its nominal resolution of 15 arc-seconds does not represent the accuracy of the underlying measurements. It is used here only for the generalized relief shown on the island location map, never for the detailed site maps.
