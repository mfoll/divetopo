# DiveTopo workflow

DiveTopo has one shared cartographic engine, one Web application, and one
configuration directory per region. The repository is the source of truth for
code and generated artifacts; the public interface is
[divetopo.com](https://divetopo.com).

## Start every mapping task from the live repository

Before changing or adding a site:

1. inspect the current Git `HEAD`, this file, `README.md`, the selected region's
   workflow, the cartographic modules, tests, region manifest, and existing site
   configurations;
2. do not rely on an earlier Codex task or remembered version of the workflow;
3. keep unrelated changes untouched and keep a new site region-local unless a
   shared change has been discussed;
4. leave generated work uncommitted and undeployed until its visual result has
   been validated.

For La Réunion, continue with
[regions/reunion/WORKFLOW.md](regions/reunion/WORKFLOW.md).

## Repository boundaries

```text
apps/web/                  one public application and deployment
cartography/               shared rendering and packaging engine
cartography/regions/       region-specific acquisition/orchestration modules
regions/<slug>/region.json regional identity, CRS, sources and site inventory
regions/<slug>/sites/      reproducible site configurations
regions/<slug>/outputs/    canonical generated maps and interactive packages
tests/                     shared and region-contract tests
```

The Web application consumes publication derivatives. It must never calculate
terrain, alter camera metadata, or become the canonical owner of maps and
interactive packages.

## Adding a region

A new region must provide:

- `regions/<slug>/region.json`, following the existing schema;
- one acquisition/orchestration module under `cartography/regions/`;
- source adapters or source-specific functions that normalize bathymetry,
  topography and imagery before invoking the shared renderer;
- a region-specific workflow documenting source coverage, projection,
  licences, attribution and acceptance constraints;
- site configurations under `regions/<slug>/sites/`;
- tests proving that the manifest, configurations, outputs and Web inventory
  agree.

Do not copy the React application, relief renderer, plate composer or
interactive exporter. A provider-specific adapter may be added when another
region uses different public data.

## Adding a site

Use the target region's workflow. At minimum, every published site must have:

- validated identity, coordinates, sources and source coverage;
- 2D and static 3D maps in topographic and aerial-imagery variants;
- a locator map and both printable sheets;
- a canonical interactive terrain package;
- responsive Web derivatives and downloads;
- configuration, provenance and automated checks;
- full-resolution visual inspection and desktop/mobile interactive inspection.

Relief mapping never demonstrates access, authorization, present conditions or
safety. Document uncertainty instead of turning it into a geographic claim.

## Releasing

1. Run the affected region's configuration checks.
2. Run the complete Python suite.
3. If generated artifacts moved without regeneration, compare their SHA-256
   hashes before and after the move.
4. Run the unified Web application's lint, tests and production build.
5. Inspect the affected routes and interactions on desktop and mobile.
6. Review the complete task-scoped diff.
7. Commit and push the reviewed state to GitHub.
8. Publish the exact `apps/web/` tree through Sites and verify production.

The exact hosting invariant and release sequence are in
[DEPLOYMENT.md](DEPLOYMENT.md).
