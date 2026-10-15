#!/bin/bash
# Corrector de exámenes — doble clic para arrancar (macOS). En Linux: ./iniciar.command
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  echo "Preparando el entorno por primera vez, puede tardar un par de minutos..."
  python3 -m venv .venv || { echo "Hace falta Python 3.9 o superior: https://www.python.org/downloads/"; read -r; exit 1; }
fi
source .venv/bin/activate
python -m pip install -q --disable-pip-version-check -r requirements.txt
python app.py "$@"
