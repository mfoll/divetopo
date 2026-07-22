#!/bin/sh
set -eu

brew install python@3.14 gdal
"$(brew --prefix python@3.14)/bin/python3.14" -m venv --system-site-packages .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt

printf '\nEnvironment ready. Run:\n'
printf '  .venv/bin/python generate_reunion_topobathy.py sites/cap-la-houssaye.json --refresh\n'
