# Réunion Island

This directory contains the region-specific part of DiveTopo's first published
collection.

- [`region.json`](region.json) defines the regional identity, projection,
  sources and published-site inventory.
- [`sites/`](sites/) contains the seven reproducible site configurations.
- [`outputs/`](outputs/) contains the canonical maps, printable sheets and
  interactive terrain packages.
- [`WORKFLOW.md`](WORKFLOW.md) documents acquisition, rendering parameters and
  the complete acceptance gate.
- [`THIRD-PARTY-NOTICES.md`](THIRD-PARTY-NOTICES.md) records source licences
  and mandatory attributions.

Shared rendering, plate composition and terrain export belong in
[`../../cartography/`](../../cartography/). Shared website code belongs in
[`../../apps/web/`](../../apps/web/). Neither should be copied into a future
region.
