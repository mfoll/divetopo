# Cartographic engine

This package owns DiveTopo's reusable cartographic processing:

- `config.py`: shared site validation and regional manifest resolution;
- `cache.py`: source contracts, provenance manifests and SHA-256 validation;
- `relief.py`: surface fusion, masks, palettes, isobaths and static rendering;
- `plate.py`: printable-sheet composition;
- `interactive.py`: compact interactive-terrain export;
- `regions/`: source acquisition and orchestration that cannot be shared
  without pretending different providers expose the same contract.

A regional pipeline must normalize its source rasters before calling the shared
renderer. New regions may add provider-specific acquisition code, but must not
copy `relief.py`, `plate.py` or `interactive.py`.

Run modules from the repository root, for example:

```bash
.venv/bin/python -m cartography.regions.reunion \
  regions/reunion/sites/cap-la-houssaye.json --check
.venv/bin/python -m cartography.plate \
  regions/reunion/sites/cap-la-houssaye.json
.venv/bin/python -m cartography.interactive
```
