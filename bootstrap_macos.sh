#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$script_dir"

for required_font in \
    "/System/Library/Fonts/Supplemental/Arial.ttf" \
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf" \
    "/System/Library/Fonts/Avenir Next.ttc"
do
    if [ ! -r "$required_font" ]; then
        printf 'Required macOS font is missing: %s\n' "$required_font" >&2
        exit 1
    fi
done

brew install python@3.14 gdal
"$(brew --prefix python@3.14)/bin/python3.14" -m venv --system-site-packages .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt

printf '\nEnvironment ready. Run:\n'
printf '  .venv/bin/python -m cartography.regions.reunion regions/reunion/sites/cap-la-houssaye.json --refresh\n'
