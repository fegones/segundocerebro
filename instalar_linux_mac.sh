#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
PYTHON="${PYTHON:-python3}"
"$PYTHON" -c 'import sys; assert (3,11) <= sys.version_info[:2] <= (3,13), "Se requiere Python 3.11-3.13"'
"$PYTHON" -m venv .venv
. .venv/bin/activate
python -m pip install --prefer-binary --only-binary=:all: -e .
python -m notebook_conexion.selftest
printf '\nLa instalación está lista. Inicie: .venv/bin/python -m notebook_conexion.desktop\n'
