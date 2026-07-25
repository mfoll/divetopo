# Interactive 3D terrain package

The interactive terrain is a cartographic deliverable from the pipeline, just
like the 2D JPEGs, 3D perspectives, and printable sheets. The website consumes
it but does not generate it.

The canonical command is:

```bash
.venv/bin/python -m cartography.interactive
```

It currently rebuilds the packages for every
`regions/reunion/sites/*.json` file from valid GeoTIFFs in the local cache and
writes them to `regions/reunion/outputs/interactive-terrain/`.
The maximum depth follows `max_depth_m`, unless a configuration explicitly
documents a lower `interactive_max_depth_m` limit to exclude an unreliable
source-coverage margin. Each site declares an
`interactive_footprint_utm40s`, an oriented rectangle that must remain within
the context extent. Its width approximately follows the coastline, and its
depth follows the viewing axis from offshore toward land. The pipeline first
crops its north-up bounding rectangle, then masks the terrain to the exact
oriented footprint. This allows the Web package to cover a larger area than
the 2D map without changing that map. Pointe au Sel retains a maximum depth of
`40 m`.

Validation requires `look_bearing_deg` to match `view_bearing_deg`, the width
to exceed the initially visible width by at least 15%, and the depth to retain
at least a 20% margin based on tilt, aspect ratio, and projection scale. The
optional `interactive_view_visible_width_m` field can adjust the Web framing
alone without changing the static perspective.

A deep offshore NoData boundary can be filled explicitly with
`deep_edge_nodata_terrain_fill`. Only components that do not touch land,
are enclosed by a sufficiently long marine boundary, and are deeper than
`deep_edge_nodata_terrain_min_depth_m` become a uniform plateau at the maximum
depth. This option is disabled by default.

## Format

The format is a small package of six files per site, plus a global manifest. It
is not a single 3D file:

| File | Purpose |
|---|---|
| `terrain.json` | Metadata, extent, orientation, camera, encodings, credits, and texture filenames |
| `height.bin` | Little-endian `uint16` elevation field, in physical meters before vertical exaggeration |
| `valid-mask.bin` | Compact validity mask, one bit per vertex |
| `isobath-mask.bin` | Compact mask of vertices where contours remain strictly derived from the source |
| `topographic.webp` | Topo-bathymetric texture |
| `orthophoto.webp` | Orthophoto texture |

`manifest.json` inventories the sites and records each file's size and SHA-256
checksum. The browser loads the files, builds the triangulated mesh with
Three.js, and replaces only the texture when the user switches between
topography and orthophoto.

Schema 2 distinguishes terrain validity from isobath validity. When a deep
boundary gap is completed with a uniform plateau at the maximum depth,
`valid-mask.bin` keeps that terrain visible, while `isobath-mask.bin` excludes
the fill and all of its transition cells. The WebGL contours therefore remain
derived solely from source elevations, without inventing intermediate levels
around the plateau.

The elevation field retains its boundary vertices and has at most `513`
vertices along its longest axis. This moderate ceiling increases the geometric
detail of the enlarged interactive extents without publishing the much heavier
sub-meter grids used for the static perspectives. The other dimension
preserves the source raster's aspect ratio.

`terrain.json` also contains the initial azimuth, tilt, and framing. It records
the extent under `footprint`, including its center, dimensions, azimuth, and
four UTM 40S corners. The optional `view.horizontalCenterOffsetM` field carries
over the horizontal projection of the static center; a positive value moves
the target toward the right side of the screen. It is currently used to align
the initial views of Passe de l'Hermitage and Pont Rouge with their printable
perspectives.

The isobaths are neither a texture nor an additional vector file. The viewer
calculates them analytically from the exported elevation field, in perfectly
horizontal planes every 5 m. Visible levels run from `-5 m` to the last
multiple of 5 strictly below the maximum depth. The core uses the exact color
of the bathymetric palette at each depth, while the black edging, fixed legend,
display button, and dynamic compass rose are handled by the viewer. The
`isobath-mask.bin` mask ensures that no contour is created over an artificial
fill or its transition.

This separation is intentional:

- geometry is downloaded only once for both styles;
- textures are cached separately;
- physical elevations, provenance, and exaggeration remain explicit;
- the package can be used by a viewer other than the current website.

A single container such as GLB would be possible, but it would duplicate or
complicate texture switching and make provenance less direct. A ZIP archive
would not be directly usable by the browser without a decompression step.

## Boundary with the website

The website must never call `cartography.interactive`. Its asset step copies
and verifies the canonical package into `apps/web/public/terrain/`, just as
it already derives responsive images from the JPEGs in
`regions/reunion/outputs/`.

Responsibilities are therefore divided as follows:

1. cartographic pipeline: configurations, source data, 2D maps, static
   perspectives, printable sheets, and canonical interactive packages;
2. website: interface, navigation, Three.js viewer, responsive assets,
   canonical-package copy, and deployment.

The files in `apps/web/public/terrain/` are publication derivatives. The source
of truth remains `regions/reunion/outputs/interactive-terrain/`.
