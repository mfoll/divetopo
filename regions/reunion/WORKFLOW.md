# Réunion topo-bathymetric workflow

This pipeline regenerates from scratch a 2D map, an oblique 3D view, and an island locator map for a coastal site on Réunion. It downloads official digital data, merges bathymetry and topography, extracts isobaths, and then produces the final JPEGs.

## Sources

- Bathymetry: Ifremer HYSCORES 2015 DTM, 0.4 m grid, supplemented by Litto3D on the outer slopes. Required attribution: `Projet HYSCORES (Ifremer, UBO, Office de l'Eau Reunion)`. Source license: CC BY-NC-SA, with no version specified in the metadata.
  - Catalog: <https://www.data.gouv.fr/datasets/mnt-bathymetrique-a-haute-resolution-des-fonds-marins-des-zones-recifales-de-la-cote-ouest-de-lile-de-la-reunion-2015>
  - Saint-Gilles: <https://sextant.ifremer.fr/sextant_data/HYSCORES/HYSCORES_02_Bathy_OUEST_REU/Saint_Gilles/>
  - Saint-Leu: <https://sextant.ifremer.fr/sextant_data/HYSCORES/HYSCORES_02_Bathy_OUEST_REU/Saint_Leu/>
  - Etang-Sale: <https://sextant.ifremer.fr/sextant_data/HYSCORES/HYSCORES_02_Bathy_OUEST_REU/Etang_sale/>
  - Saint-Pierre: <https://sextant.ifremer.fr/sextant_data/HYSCORES/HYSCORES_02_Bathy_OUEST_REU/Saint_Pierre/>
- Topography: IGN RGE ALTI, WMS layer `ELEVATION.ELEVATIONGRIDCOVERAGE.HIGHRES`, requested as 32-bit float GeoTIFF. Licence Ouverte 2.0; product updates ended in 2024.
- Optional land orthophoto: IGN WMS layer `HR.ORTHOIMAGERY.ORTHOPHOTOS` (BD ORTHO served at 20 cm), requested as GeoTIFF over the same UTM 40S extent: <https://data.geopf.fr/wms-r/wms>. The capture date is checked with `GetFeatureInfo` at each site marker and recorded in `orthophoto_capture_date`; it is not assumed to be the same across the island. The configured capture date is 22 July 2025 for Cap La Houssaye, Boucan Canot, Cap Homard, Pointe au Sel, Pont Rouge, and Plage du Cimetière, and 2 August 2025 for Passe de l'Hermitage.
- Marine relief for the island locator map: official GEBCO 2024 WMS, versioned endpoint <https://wms.gebco.net/2024/mapserv> and shaded layer `GEBCO_2024`, reprojected onto the UTM 40S grid. The pipeline does not use the mutable `GEBCO_LATEST` alias; the full citation is in `THIRD-PARTY-NOTICES.md`.
- Common coordinate reference system: WGS 84 / UTM 40S, `EPSG:32740`.

HYSCORES does not cover the entire island. For a site outside the four sectors listed above, another digital bathymetric source, such as Litto3D, must be connected before using the same rendering engine.

## Prerequisites

- Local Python `.venv` with `numpy`, `Pillow`, and the GDAL bindings. The recorded reference environment is Python 3.14, GDAL 3.13.1, NumPy 2.5.1, and Pillow 12.3.0.
- GDAL commands available in `PATH`, particularly `gdal_translate`.
- Network access to `sextant.ifremer.fr`, `data.geopf.fr`, and `wms.gebco.net` during acquisition.

Rendering alone is then reproducible offline from the GeoTIFFs cached in `.tmp/bathy-renders/`.

## Regenerating Cap La Houssaye

From the project root:

```bash
./bootstrap_macos.sh
.venv/bin/python -m cartography.regions.reunion regions/reunion/sites/cap-la-houssaye.json --refresh
```

`--refresh` forces a new download. Without this option, existing files are reused only if their provenance manifest still matches the configured sources. To render only:

```bash
.venv/bin/python -m cartography.regions.reunion regions/reunion/sites/cap-la-houssaye.json --render-only
```

The two options are mutually exclusive. Before rendering, the script validates the configuration and checks the contract of every reused raster: source URL and layer, EPSG:32740 projection, extent, resolution, band count, plausible numeric signal, and the SHA-256 recorded during acquisition. An existing file that is constant, modified, or incompatible is never accepted as a valid cache. To run these checks without downloading or rendering:

```bash
.venv/bin/python -m cartography.regions.reunion regions/reunion/sites/cap-la-houssaye.json --check
```

After a change limited to the lighting model or 3D projection,
`--render-only --relief-only` validates the cache and then regenerates only the
two 3D perspectives. The 2D maps and locator map remain unchanged.

After a change limited to the 2D palette or shading,
`--render-only --plan-only` validates the cache and regenerates only the
topographic and orthophoto 2D maps. Static 3D perspectives and locator maps
remain unchanged.

The [sites/cap-la-houssaye.json](sites/cap-la-houssaye.json) file contains all
site-specific parameters and the paths of the canonical outputs.

## Executed steps

1. The script requires `hyscores_tiff_url` to pin the exact digital bathymetric GeoTIFF. The discovery function in the HYSCORES sector index remains only for reading legacy configurations outside the validated pipeline.
2. `gdal_translate` reads only `context_bbox_utm40s` from the 2.5 GB Ifremer GeoTIFF through `/vsicurl/`.
3. Negative marine elevations are converted into positive depths. Land values and nodata become `-99999`.
   Pointe au Sel then applies the optional pinned Shom S199503500 correction.
   Its archive is verified by SHA-256 and read with `bsdtar`. A robust median
   offset is fitted on the consistent 8–25 m overlap; only soundings diagnosing
   a positive error of at least 4 m inside the configured control box influence
   the raster. Gaussian weights and a smooth influence ramp retain the
   HYSCORES texture and avoid a visible source boundary.
4. The context RGE ALTI is downloaded over the larger extent at `context_topography_resolution_m` or, if unset, at `topography_resolution_m`.
5. The 2D `focus_bbox_utm40s` extent is cropped from the context when both topographic resolutions are identical. If they differ, the focus RGE ALTI is requested directly at `topography_resolution_m`, so the declared fine resolution is not silently replaced by the context resolution.
   Rebuilding a parent always invalidates its derivatives: new raw bathymetry rebuilds the positive-depth raster and then its crop, and a new context DTM rebuilds its focus crop.
6. The rasters may be rotated by quarter turns to place the sea at the top of the calculation arrays.
7. The 0 m coastline is interpolated into a continuous polygon. HYSCORES and RGE ALTI are merged without filling gaps by default. A small internal interpolation can be enabled explicitly for the static 3D mesh only; it runs after isobath extraction. A second, separate option can complete a large marine gap open to the edge in both the static and interactive terrains with a uniform plateau at maximum depth. It requires a sufficiently deep known boundary with no land contact and creates neither intermediate relief nor contours.
8. Isobaths are extracted every 5 m, from `-5 m` down to the display depth of the output, and then smoothed. The value defaults to `max_depth_m` and can be limited for the 2D map with `plan_max_depth_m`. A 20 m map therefore produces four levels, and a 30 m map produces six. All lines are drawn before labels so that no isobath or coastline can cross the text.
9. The 2D map uses the focus extent. The 3D view uses the larger context extent but retains the final framing on the site.
10. The topo-bathymetric JPEGs receive a 50 m scale bar and, in the upper left, the same circular compass rose as the interactive terrain, recalculated according to rotation.
11. The locator map reuses a 20 m island-wide RGE ALTI and the pinned GEBCO 2024 marine relief, then adds a latitude-longitude grid, a 20 km scale bar, and the site's UTM marker.
12. `cartography.plate` assembles the island map and detailed views into two high-resolution plates on a white background: one variant with the land orthophoto and one topographic variant without aerial imagery. The top banner uses a centered typographic title block and deliberately occupies the full available height. It displays exactly one canonical site name on one line, the municipality on a second line, and `La Réunion` alone on a third line. Aliases, neighboring areas, and name variants remain in `title` or in the documentation, never in `plate_site_name`. The location and coordinates in degrees, minutes, and seconds are structured only with spacing and thin rules, without a bordered title block or tinted background. Two short rules flank `La Réunion` laterally on the same line; no horizontal rule underlines it. A separate vertical rule divides the title block from the island map. The 2D and 3D views together occupy the lower row. The panels are flat, without shadows, with a discreet black rule.
13. After a validated acquisition, `<slug>-cache-manifest.json` records the normalized source contract, logical paths, and SHA-256 of each GeoTIFF. It remains with the local cache and must be regenerated with `--refresh`, never edited manually.

## Interactive 3D terrain

The interactive terrain is generated by the cartographic pipeline after cache
validation:

```bash
.venv/bin/python -m cartography.interactive
```

The canonical output is under `regions/reunion/outputs/interactive-terrain/`. All seven
configurations in `regions/reunion/sites/` are exported by default. Each site
contains `terrain.json`, `height.bin`, `valid-mask.bin`,
`isobath-mask.bin`, `topographic.webp`, and `orthophoto.webp`; the global manifest records their
sizes and SHA-256 hashes. The mesh retains physical elevations, and the
viewer then applies the vertical exaggeration declared in the metadata.
The elevation field has at most 513 vertices along its longest axis. Both
textures are derived from rasters covering the interactive extent and are
limited to `2048 px` on their longest side. All seven sites declare an
`interactive_footprint_utm40s`, a rectangle oriented like the view and
approximately parallel to the coastline. The pipeline crops its bounding
rectangle from the context rasters, then masks the mesh and textures
to the oriented rectangle without modifying the focus files.
The viewer treats both textures as sRGB images, then applies linear tone mapping
with an exposure of `1.55` before the final sRGB conversion. This exposure is
identical to that of the static perspectives: it brightens slopes without a CSS
filter and without modifying the source WebPs.

The website never generates these files. It copies the canonical package into
its public directory with `apps/web/scripts/sync_interactive_terrain.py`. This
boundary makes it possible to change the interface or deployment without moving
responsibility for the terrain, textures, camera, or provenance outside
the pipeline. The complete format is described in
[INTERACTIVE-TERRAIN.md](../../INTERACTIVE-TERRAIN.md).

## Adding a site

Copy the existing JSON to `regions/reunion/sites/<slug>.json`, then set:

- `slug` and `title`;
- `hyscores_directory`, selected from the four official sectors, and `hyscores_tiff_url` pointing to the exact GeoTIFF;
- `focus_bbox_utm40s`: tight rectangle containing the site to be read in 2D;
- `context_bbox_utm40s`: larger rectangle fully containing the preceding extent;
- `interactive_footprint_utm40s`: rectangle specific to the Web package, defined by its UTM 40S `center`, its `width_m` along the screen axis, its `depth_m` along the viewing axis, and its `look_bearing_deg`, identical to `view_bearing_deg`; all four corners must remain within the context;
- `rotation_k`: `numpy.rot90` rotation reserved for the 3D working raster; the 2D map always remains north-up;
- `orthophoto_capture_date`, in ISO `YYYY-MM-DD` format, verified for this site rather than copied from a neighboring site;
- versioned GEBCO references and their attribution for the island locator map;
- camera parameters and, if necessary, output paths.

`rotation_k` mapping:

| Sea direction in the initial UTM raster | `rotation_k` |
|---|---:|
| north | 0 |
| east | 1 |
| south | 2 |
| west | 3 |

The 2D compass rose always shows north at the top. The compass rose in the view from offshore is automatically adapted to the camera azimuth.

For 3D, allow approximately 300 to 400 m of additional real data offshore in `context_bbox_utm40s`, 100 to 200 m on each side, and 200 to 300 m inland. This margin must be increased if the viewpoint is lowered.

### Acceptance gate for a new site

A new site is complete only when all of the following are true:

1. The task began by inspecting the current `HEAD`, the root `README.md` and
   `WORKFLOW.md`, this regional workflow,
   the rendering scripts, tests and existing site configurations. An earlier
   Codex task or remembered workflow is not authoritative.
2. The site identity, coordinates, source sector and evidence have been checked.
   If identification remains uncertain, the result is explicitly labelled as a
   prototype and the uncertainty is documented. Keep an unapproved prototype
   configuration outside `regions/reunion/sites/` and its assets outside canonical outputs.
3. Changes remain site-local by default. A shared script, test convention,
   the root `README.md` or either workflow is changed only after discussing the shared
   impact.
4. The complete canonical set exists: 2D and static 3D maps in topographic and
   aerial-imagery variants, island locator, both printable sheets, and the
   six-file interactive package plus its responsive website assets.
5. Current common graphics are preserved: `2474 × 1712 px` static maps,
   `5400 × 3250 px` sheets, one site name, a separate municipality,
   `LA RÉUNION` alone between the lateral rules, the `−1.5/−2 m`
   aerial-imagery fade, current lighting, 5 m isobaths and the current compass
   design.
6. The interactive footprint is an approximately coast-parallel rectangle of
   real data. Its initial camera contains no mesh, land or texture boundary and
   remains consistent with the validated static perspective.
7. The configuration passes
   `.venv/bin/python -m cartography.regions.reunion <config> --check`,
   the Python suite and `git diff --check`. The Web application also passes
   lint, tests and a production build.
8. Every final JPEG and sheet is inspected at full resolution. The interactive
   view is inspected on desktop and mobile in portrait and landscape, including
   its initial camera, textures, isobaths, controls and download links.
9. The hand-off lists created files, retained coordinates and sources, camera
   parameters, completed validation and unresolved choices. Commit, push and
   deployment occur only after user validation and follow
   [DEPLOYMENT.md](../../DEPLOYMENT.md).
10. Relief mapping is kept separate from any claim about access, permission,
    current conditions or safety.

### Website integration for a validated site

After the canonical maps and sheets are approved:

1. Add the municipality and neutral identifying metadata to
   `apps/web/content/site-details.json`. Do not add a visible site description
   or replace the fixed regional heading without prior validation.
2. Inspect the site-picker label placement and add a `SITE_LABEL_LAYOUT` entry
   in `apps/web/app/TopoReunionExperience.tsx` if the automatic position overlaps a
   neighbor.
3. Update the explicit published-slug sets and count assertions in
   `tests/test_config.py` and `apps/web/tests/rendered-html.test.mjs`.
4. Regenerate the complete interactive package without positional configs,
   then copy it and rebuild responsive map assets:

   ```bash
   .venv/bin/python -m cartography.interactive
   cd apps/web
   ../../.venv/bin/python scripts/sync_interactive_terrain.py
   ../../.venv/bin/python scripts/build_map_assets.py
   ```

5. Update the site table and published-site count in both READMEs.
6. Update the French and English regional count in
   `apps/web/content/regions.ts` and its tests. Deploy the single Web
   application after its complete route set passes.

Two commands have intentionally broad behavior:

- `apps/web/scripts/build_map_assets.py` publishes every `regions/reunion/sites/*.json`
  configuration, which is why unresolved prototypes must not live there.
- Positional configs passed to `-m cartography.interactive` define the
  complete package and atomically replace its output. Use an explicit temporary
  `--output` for an isolated prototype; production generation must run without
  positional configs so it includes every published site.

The current Web selector covers the existing west-coast UTM extent. A site
outside it requires an explicit shared interface and source-scope change, not
only a site-local configuration. The municipality currently exists both in the
site JSON plate fields and `apps/web/content/site-details.json`; keep them
consistent until that duplication is removed.

## Rendering parameters

- `max_depth_m`: maximum depth shown by the palette and static terrain. Isobaths are generated automatically every 5 m down to this value; Boucan uses 30 m.
- `plan_max_depth_m` and `interactive_max_depth_m`: optional limits, less than or equal to `max_depth_m`, specific to the 2D maps and the interactive package respectively. They are reserved for a documented source-coverage limitation, not for aesthetic cropping. Pointe au Sel uses `plan_max_depth_m: 30` and retains `max_depth_m: 40` for the static and interactive terrains. Its static view uses the validated framing at `60°` over `1200 × 1400 m`, with a visible width of `900 m` and a center shifted `50 m` north.
- `relief_mesh_gap_fill_max_area_m2`: optional physical threshold, disabled by default, for interpolating only very small enclosed marine gaps in the static 3D mesh. A component touching an edge, land, or exceeding this threshold remains invalid. Pointe au Sel sets `64 m²`; the current rendering first fills 30 cells, or `19.2 m²`, from their valid boundary. The same check is applied again after rotation and cropping to close only micro-gaps that the transformation can reveal; it currently adds 2 cells, or `1.3 m²`. Both passes run after contour extraction, so isobaths and all other outputs remain faithful to the source.
- `interactive_shallow_basin_correction_bbox_utm40s` and `interactive_shallow_basin_max_boundary_depth_m`: site-local visual correction for a documented shallow source anomaly in the interactive 3D mesh. The projected rectangle is interpolated only when its complete boundary is valid and remains shallower than the configured limit. Souris Chaude uses `[318798.0, 7663960.8, 318856.8, 7663996.8]` with a `2.5 m` boundary limit to preserve the shallow surface already validated in v1.2.1. The correction is excluded from source-derived isobaths and does not modify source rasters or 2D maps.
- `deep_edge_nodata_terrain_fill` and `deep_edge_nodata_terrain_min_depth_m`: optional completion, disabled by default, of deep boundaries in the 3D terrains. A component must touch the outer edge, touch no known land, have a sufficiently long marine boundary, and encounter no boundary depth shallower than the threshold. Pointe au Sel uses `20 m`; qualifying components become a uniform plateau at `-40 m`, with no reconstructed slope. Static and interactive isobaths are masked over the fill and its transition.
- `interactive_footprint_utm40s`: oriented rectangle of the interactive package, cropped from the context rasters and required to remain within `context_bbox_utm40s`. Its width follows the coastline approximately, and its depth follows the viewing axis from offshore toward land. Validation requires at least a 15% lateral margin and a 20% depth margin relative to the canonical initial framing. Pointe au Sel uses a `1040 × 1545 m` rectangle centered on `[321581.5, 7654180.4]` and oriented at `60°`.
- `interactive_view_visible_width_m`: optional visible width specific to the initial Web framing. It replaces `view_visible_width_m` only in the interactive metadata without modifying the static perspective. Cap Homard uses `540 m` to keep its entire initial view within the available data.
- `interactive_match_static_horizontal_center`: reuses the horizontal projection of the static view's center in the Web metadata. The exported `view.horizontalCenterOffsetM` field is positive toward the right of the screen. The option is enabled for Passe de l'Hermitage and Pont Rouge.
- `max_land_elevation_m`: maximum land elevation represented in the relief and palette. The reference value is `55 m`; making it explicit prevents silent clipping from being mistaken for source topography.
- `topography_resolution_m` and `context_topography_resolution_m`: respective resolutions of the focus DTM and the larger 3D extent. When the values differ, the focus raster is acquired separately rather than cropped from the context. L'Hermitage therefore retains `0.5 m` on its 2D map and uses `0.8 m` over its enlarged context.
- `coast_mode`: `profile` retains the original simple coastline, described by one land/water crossing per column; `mask` extracts a two-dimensional land mask for bays, islets, headlands, and natural pools. Use `mask` when the coastline is not monotonic in the selected orientation. In `mask` mode, the land fill and the 0 m line are derived from the same smoothed continuous surface: the line follows its 0.5 isoline exactly, and no land pixel can extend into the sea.
- `view_bearing_deg`: viewing azimuth of the 3D camera, in clockwise degrees from north. If absent, the camera looks toward the bottom of the oriented raster; `135` corresponds to southeast. The mesh, its textures, and its vectors are rotated by interpolation before projection, rather than as a simple image after rendering.
- `view_crop_width_m` and `view_crop_depth_m`: metric extent retained after arbitrary rotation of the mesh. Extracting a context larger than this frame keeps the GeoTIFF edges and truncated isobaths outside the field of view without unnecessarily increasing the number of rendered facets. Coastline and isobath polylines are geometrically clipped to this frame before projection; they cannot re-enter from a portion of the raster that has already been excluded.
- `relief_hemisphere_intensity`, `relief_key_light_intensity`, `relief_key_light_bearing_deg`, `relief_key_light_elevation_deg`, `relief_normal_sample_spacing_m`, and `relief_exposure`: lighting model for the static perspectives, calibrated against the WebGL terrain. Static normals are computed with the real metric spacing and displayed vertical exaggeration, then smoothed at 2 m by default to stabilize microrelief. The interactive terrain follows a different constraint: its longest axis is capped at 513 vertices, retaining more detail over enlarged extents while remaining more generalized than the static rendering. A cool hemispheric light preserves detail on shaded slopes, and a warm directional light from the northeast shapes sea and land in linear color space. The shared default exposure of `1.55` multiplies linear radiance before its sRGB conversion; it restores brightness without post-processing the JPEG. These parameters are shared by the topographic and orthophoto textures; coastline strokes, isobaths, and annotations are drawn afterward and are not recolored.
- The 3D projection automatically calculates its cross-view zoom from the width of `focus_bbox_utm40s`. The 2D and 3D views therefore have a similar scale, and an identical scale along the 50 m scale-bar axis when `view_visible_width_m` is not overridden. This equality is not an absolute goal: `view_visible_width_m` frames the perspective on the useful relief without modifying the 2D extent. Boucan uses `580 m`, and l'Hermitage uses `650 m`.
- `camera_tilt`: apparent angle of the grid. A lower value lowers the viewpoint.
- `along_view_projection_scale`: cartographic amplification along the 3D viewing axis, applied after the azimuth. This name remains valid for all camera orientations.
- `view_left_crop_fraction` and `view_right_crop_fraction`: fractions removed independently from the left and right edges of the projected image. These directions are screen directions, not cardinal directions. The 2D map continues to be defined solely by `focus_bbox_utm40s`.
- `view_top_crop_fraction`: fraction removed from the top of the projected image, regardless of camera azimuth.
- A uniform band, vertical wall, or stretched pixels at the top of a 3D view first indicate the boundary of the mesh or GeoTIFF. Enlarge `context_bbox_utm40s`, then `view_crop_depth_m`, to project real data beyond the frame. Do not hide this defect with `view_top_crop_fraction` or `horizon_cleanup_fraction`.
- `output_scale`: native rendering factor for vectors, text, and annotations. The raster background is interpolated before they are drawn, without adding spatial detail beyond the resolution of the source DTMs.
- `plan_output_scale` and `relief_output_scale`: separate optional factors for producing a high-resolution intermediate rendering despite the different 2D and 3D engines.
- `map_style_scale`: shared graphical factor expressed in final output space. The engine automatically compensates for intermediate resolutions and final resampling to retain the same isobath thicknesses, label sizes, compass roses, scale bars, sources, and licenses across all sites and 2D and 3D views. Use the same value, currently `2.0`, in all configurations. The length of the 50 m scale bar remains determined by the metric scale of the framing.
- `final_output_size_px`: exact final dimensions shared by the 2D and 3D maps. All seven published sites use `2474 x 1712 px`, after Lanczos resampling.
- To translate the 2D map, translate `focus_bbox_utm40s` without changing its width or height, then regenerate the three `focus_*` rasters. To change the format as well, recalculate width and height with the desired final aspect ratio before regenerating the rasters.
- `relief_suppressed_label_levels`: isobath labels to hide only in the 3D view, without removing the lines or data. At Boucan, `-30 m` is hidden because its line is outside the perspective framing. At l'Hermitage, the label remains visible now that the framing clearly includes this line.
- 3D label placement measures the actual text rectangle including its halo and a safety margin. A position is rejected if this rectangle approaches an isobath of another level or an already placed label; the engine then searches another segment of the same line. This rule is shared across all sites and should be preferred over local offsets.
- `land_sieve_threshold_px`: minimum size, in source DTM pixels, of disconnected land components retained by the two-dimensional mask. Increase it only to remove visually confirmed artefactual micro-islands; Passe de l'Hermitage uses `10000`.
- `imagery_sea_full_depth_m` and `imagery_sea_max_depth_m`: explicit bounds of the optional orthophoto extension into a shallow lagoon. The shared standard is `1.5 m` then `2 m`: the image remains opaque down to the first depth and fades gradually until becoming transparent at the second. `imagery_sea_depth_m` and `imagery_sea_feather_m` remain accepted for legacy configurations.
- `imagery_sea_smoothing_m`: spatial pre-smoothing applied only to the depth that drives the visual mask; it modifies neither the relief nor the isobaths. Across all seven published sites, the image remains complete down to `-1.5 m`, disappears at `-2 m`, and the mask is pre-smoothed over 5 m. When a marine extension is enabled, this continuous depth mask replaces the combination of land/sea masks and avoids rectangles around pools, beaches, or structures located at 0 m.
- The bathymetric palette consistently uses `-2 m` as its red chromatic zero, matching the end of the orthophoto fade. It is then rescaled down to `max_depth_m` to retain the historical deep color at each map boundary. The first fully bathymetric background therefore remains red instead of starting directly in orange.
- `view_center_offset_east_m` and `view_center_offset_north_m`: geographic offset of the center of the 3D crop before projection. Positive values point east and north. L'Hermitage uses `140` and `240` respectively to move the framing closer to the pass and remove unnecessary deep foreground without changing camera orientation. Boucan uses `200` and `-200` to keep shallow cells outside the foreground boundary of its view rotated to `135°`. Its projected mesh covers 1600 m along the viewing-depth axis within a `1900 x 1700 m` source context. L'Hermitage's mesh covers 3200 m along that axis within a `3300 x 3600 m` source context.
- `coastline_visible` and `orthophoto_coastline_visible`: display of the 0 m vector line on all variants or only on the orthophoto variant. The mask and framing continue to use the coastline even if its line is not drawn. By default, the line is retained on topographic variants and hidden on all orthophotos; `orthophoto_coastline_visible: true` would allow an explicit exception.
- `clip_rotated_outside`: invalidates corners lying outside the raster after an arbitrary rotation. Enable it when the source context is large enough to contain the entire rotated extent; this prevents edge pixels from being extended artificially at the horizon.
- `horizon_cleanup_fraction`: last-resort mask for a residual horizon fringe. Prefer a larger context and `clip_rotated_outside` first; leave it at `0` when these measures are sufficient.
- `view_canvas_width_px` and `view_canvas_height_px`: logical dimensions of the 3D canvas before `relief_output_scale`. Choose them with the same width-to-height ratio as `focus_bbox_utm40s`, accounting for cropping, so the panels have the same shape without distortion.
- The ratio of the canvas remaining after `view_left_crop_fraction`, `view_right_crop_fraction`, and `view_top_crop_fraction` must match `final_output_size_px`. Final resizing always retains a uniform factor and crops only a possible minimal excess; it never stretches the X and Y axes separately. L'Hermitage uses a `1237 x 1069 px` canvas, which becomes `1237 x 856 px` after a 20% top crop, exactly matching the `2474/1712` ratio.
- `plan_open_label_offsets_px`: optional local corrections to the main labels, indexed by depth. The `[dx, dy]` values are expressed in pixels before `output_scale`. Use them only after automatic placement, to move a label out of a crowded area. At Cap La Houssaye, the `-10 m` label is shifted left and offshore.
- `orthophoto_enabled`: generates a second hybrid 2D map without modifying the original topographic map.
- `orthophoto_layer`, `orthophoto_resolution_m`, and `orthophoto_capture_date`: IGN WMS layer, working resolution, and ISO date of the georeferenced orthophoto. The default `HR.ORTHOIMAGERY.ORTHOPHOTOS` layer is served at 20 cm. The focus raster is requested at 20 cm for six sites and at 40 cm for Pointe au Sel. The date is site-specific and must be checked with `GetFeatureInfo` when adding or refreshing a site.
- `orthophoto_3d_resolution_m`: resolution of the context texture draped over the static 3D view's mesh. Current values are 20 cm at Cap La Houssaye; 40 cm at Boucan Canot, Cap Homard, and Plage du Cimetière; 50 cm at Pointe au Sel and Pont Rouge; 80 cm at Passe de l'Hermitage. They are selected explicitly according to extent and computational cost without changing the source's nominal resolution. Requests exceeding 4096 pixels on one axis are automatically split into tiles and then assembled without changing the requested resolution.
- `relief_texture_triangle_min_area_px`: minimum area of a projected facet, on the internal antialiased canvas, above which its two triangles receive barycentric interpolation of the lit colors. The default value of `12` targets slopes and cliffs and lets sub-pixel facets use their average, which is faster and visually equivalent.

### 3D orthophoto sharpness

The WebGL view appeared sharper because it used the `focus` orthophoto
and interpolated its texture on the GPU, whereas the static perspective
first reduced the context orthophoto onto the relief grid.
JPEG compression at quality 98 was not the relevant cause.

The static pipeline now retains the context texture, at the site's own
resolution, separately from the geometry until the final resampling.
Because its camera is orthographic, barycentric interpolation in the two
triangles of each large facet is sufficient: no additional perspective
correction is required. Sub-pixel facets retain their average color. The
relief, lighting model, isobaths, coastline, annotations, and JPEG encoding
remain unchanged.

This method is enabled in all seven configurations. Cap La Houssaye retains
the 20 cm texture used for the initial calibration; the other sites use 40,
50, or 80 cm according to their extent. Retaining the separate texture
produces most of the improvement on roads, rocks, and vegetation; triangular
interpolation more modestly improves slopes projected over several pixels.
- `bridge_decks`: opt-in local correction for a bridge missing from the bare-earth terrain model. Each deck is defined by `start_utm40s`, `end_utm40s`, `half_width_m`, and `feather_m`. Cap La Houssaye contains one for the bridge over Ravine Patent Slip. Never copy this correction to another site: leave the parameter absent unless an anomaly is visually confirmed and corrected case by case.
- `locator_map_enabled`, `locator_bbox_utm40s`, `locator_marker_utm40s`, and `locator_label`: enable the island locator map and place the site's marker. The 20 m RGE ALTI background is shared and reusable between sites.
- `locator_bathymetry_enabled`, `locator_gebco_wms_url`, `locator_gebco_layer`, `locator_gebco_attribution`, `locator_gebco_request_width_px`, and `locator_gebco_blur_px`: add only at sea the generalized shaded relief from GEBCO 2024 and smooth its 15 arc-second grid at display scale. The endpoint, layer, and attribution are explicit in each configuration. This island-scale layer serves for location and never replaces HYSCORES in detailed maps or for navigation.
- `plate_site_name` and `plate_city`: respectively define the single public name printed for the site and its municipality. Both fields are required. `plate_site_name` must contain no alias, second site, municipality, or `La Réunion`; `plate_city` contains only the municipality. The composer itself adds `La Réunion` on a separate line.
- `plate_author`, `copyright_year`, and `map_license`: discreetly sign the original 2D and 3D outputs so that attribution and license survive cropping of a detailed map. The plate does not repeat them in its top banner.
- `paths.output_plate` and `paths.output_plate_topography`: respective outputs of the orthophoto and topographic plates. The composition command generates both by default; `--land-style` limits regeneration to one variant.
- `plate_canvas_width_px` and `plate_canvas_height_px`: plate dimensions. All seven published plates use `5400 x 3250 px`. The current layout is calibrated for a fixed width of `5400 px`, which validation does not allow to be changed; the height can be increased for a future nearly square 2D map that must remain the same width as the 3D view without overlapping the title block.

Each JPEG carries its own data credits. The detailed maps include the required HYSCORES attribution, Litto3D, and IGN RGE ALTI; the hybrid variants add the IGN orthophoto and its campaign. The island map cites IGN RGE ALTI for land and the complete GEBCO 2024 reference for the sea. The plate duplicates neither these sources, already legible in each panel, nor the author and license already present on the 2D and 3D views.

## Licenses and reuse rights

- The scripts are licensed under MIT.
- Maps derived from HYSCORES are licensed under CC BY-NC-SA 4.0 to comply with the source's `ShareAlike` clause. Do not mark them `CC BY-NC-ND`: the `NoDerivatives` clause would add a restriction incompatible with HYSCORES.
- Third-party data are not relicensed by the project. License details, dates, citations, and warnings are in `THIRD-PARTY-NOTICES.md`.
- The HYSCORES metadata do not specify the version number of its CC BY-NC-SA license. The project's maps are published under CC BY-NC-SA 4.0.

These maps are aids for reading the relief and general orientation. They prove neither access, permission to dive, nor the current practicability or safety of a site. They do not replace local information, weather conditions, sea state, instructions from authorities, or a professional assessment.

The orthophoto variants are additional outputs. In 2D, the texture replaces the topographic background within the land mask and, when configured, within the shallow marine depth band. In 3D, the orthophoto and its georeferenced alpha mask are aligned with the DTM, then rotated, cropped, and resampled in parallel with the mesh. The alpha mask becomes zero when the control depth reaches `imagery_sea_max_depth_m`; a band calculated only from distance to the coastline therefore cannot extend the image into deep water. By default, raster gaps remain invalid and receive a neutral background. Four visual exceptions are distinct: a deep marine edge gap may receive only the maximum-depth color in 2D; a small internal gap may be interpolated in the static mesh alone through `relief_mesh_gap_fill_max_area_m2`; a bounded, documented shallow anomaly may be interpolated in the interactive mesh through `interactive_shallow_basin_correction_bbox_utm40s`; a documented deep boundary may be completed in the static and interactive terrains by a uniform plateau through `deep_edge_nodata_terrain_fill`.

- `coast_frame_fraction`: height of the coastline in the 3D image, from 0 at the top to 1 at the bottom. Increasing it visually moves the camera closer to the coast by giving less height to the offshore area. L'Hermitage uses `0.26`; Cap La Houssaye uses `0.54` because its useful relief is concentrated near the two headlands and its offshore area quickly becomes uniform.
- `vertical_exaggeration`: dimensionless ratio between the vertical and horizontal scales of the rendering. Its meaning remains stable when raster resolution, canvas, or visible width changes. The shared standard for all seven published sites and future sites is `3.9935327405`, or approximately `4×`, to make the underwater relief sufficiently readable while retaining the 2D map as the metric reference.
- `topography_resolution_m`: resolution requested from the IGN WMS. The request is refused beyond 5,000 pixels on one axis.

When `along_view_projection_scale` differs from `1`, the depth axis of the perspective is intentionally amplified. The 2D map remains the metric reference in every direction.

## Mandatory quality control

Before accepting a figure:

1. Run `.venv/bin/python -m cartography.regions.reunion <site.json> --check` and correct any configuration or cache incompatibility before rendering.
2. Verify that the black coastline follows the land-sea boundary without steps or fill polygons.
3. Verify that isobaths do not stop in the middle of the visible surface. If they touch the source raster edge, enlarge the context instead of extending them graphically. An area without data remains neutral by default. Any opt-in deep completion must be a plateau exactly equal to the maximum depth, touch neither land nor a shallow area, and remain excluded from isobaths together with its transition.
4. Verify that the edge of the context DTM is outside the 3D image. A band, mirrored spikes, or a false sky indicates an insufficient margin.
5. Compare the compass rose with an orthophoto or another reliable geographic reference.
6. Verify the 50 m scale bar from the GeoTIFF pixel size.
7. Inspect the final rendering at full resolution, particularly drop-offs, labels, the orthophoto-bathymetry transition, and the bottom of the image. Confirm that the orthophoto disappears at the configured depth.
8. Verify that labels are above all lines and that no isobath, coastline, or annotation crosses their text. Use a local offset only if automatic placement remains crowded.
9. On the locator map, verify that the marker falls on the correct coastline segment and that coordinates do not overlap.
10. Verify the site-specific capture date and that each output retains its signature, license, and credits for the data actually visible.
11. In the Web viewer, verify that isobaths remain perfectly horizontal during rotation, that their core uses the bathymetric color of the corresponding depth, that this color matches the legend, that the compass rose follows orientation, and that the initial framing matches the static view when this correspondence is configured.
12. Inspect each site's initial interactive view at desktop and mobile sizes, including full-screen portrait and landscape. No mesh edge or neutral background may appear in the initial frame. The extent must remain a rectangle approximately parallel to the coastline, with real data on land and underwater; enlarge the source context rather than cosmetically hiding an undocumented gap.
13. Verify all four map-download combinations: 2D maps and 3D views, in topographic and aerial view. Each button must target the canonical full-resolution JPEG currently displayed.

## Pipeline files

- `cartography/regions/reunion.py`: acquisition, cache, cropping, and regional orchestration.
- `cartography/cache.py`: source identity, SHA-256 hashes, and cache provenance validation.
- `cartography/config.py`: shared defaults, region manifests and early configuration validation.
- `cartography/relief.py`: merging, smoothing, isobaths, and 2D/3D rendering.
- `regions/reunion/sites/*.json`: reproducible parameters for each site.
- `cartography/plate.py`: reproducible composition of the three maps and conversion of the UTM marker into a GPS subtitle.
- `.tmp/bathy-renders/`: regenerable sources and extracts, not intended for version control.
- `regions/reunion/outputs/`: final figures.
