# DiveTopo Web

This is the single public DiveTopo application deployed at
<https://divetopo.com>. It contains the general regional homepage and the
Réunion map viewer, while consuming cartographic assets generated elsewhere in
the repository.

## Routes

- `/fr` and `/en`: general DiveTopo homepage.
- `/reunion`: language-negotiated Réunion entry point.
- `/reunion/fr` and `/reunion/en`: Réunion site selection and map viewer.
- `/reunion/<language>/sites/<slug>`: indexable URL opening one selected site.

Language follows the saved preference and then the weighted
`Accept-Language` header. The theme offers Light, Dark and Auto, with Auto as
the default. The PWA manifest is scoped to `/`, so either the homepage or a
Réunion route can be added to a device home screen under the DiveTopo name.

## Development

Node.js `>=22.13.0` is required.

```bash
npm install
npm run dev
npm test
npm run lint
```

## Cartographic assets

Responsive maps, regional manifests and original downloads are built from the
canonical regional outputs:

```bash
../../.venv/bin/python scripts/build_map_assets.py
../../.venv/bin/python scripts/build_paca_map_assets.py
../../.venv/bin/python scripts/build_interactive_terrain_manifest.py paca
../../.venv/bin/python scripts/sync_interactive_terrain.py
```

Each published site declares `web.published`, its regional-label layout and any
initial camera override in its own JSON. The builders follow each
`regions/<slug>/region.json` inventory, verify the source artifacts, and publish
self-contained copies under `public/maps/` and `public/terrain/`. The terrain
synchronizer merges every canonical regional package and rejects duplicate
slugs or files. The website never recalculates terrain geometry, textures or
camera parameters.

## Publishing

`.openai/hosting.json` identifies the existing primary DiveTopo Sites project.
Build and deployment therefore publish this unified application to
`divetopo.com`.
