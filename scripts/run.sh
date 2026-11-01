#!/usr/bin/env bash
# Lanza la app derivados-101 en macOS / Linux.
# Idempotente: crea .venv solo si no existe y reinstala dependencias solo si
# requirements.txt cambió. Argumentos extra se pasan a `streamlit run`
# (ej.: scripts/run.sh --server.headless true --server.port 8599).
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

MIN_MAJOR=3
MIN_MINOR=10

# 1) Buscar un Python >= 3.10
PYTHON_BIN=""
for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
        if "$candidate" -c "import sys; sys.exit(0 if sys.version_info >= ($MIN_MAJOR, $MIN_MINOR) else 1)" 2>/dev/null; then
            PYTHON_BIN="$candidate"
            break
        fi
    fi
done

if [[ -z "$PYTHON_BIN" ]]; then
    echo "ERROR: se necesita Python ${MIN_MAJOR}.${MIN_MINOR} o superior y no se encontró." >&2
    if command -v python3 >/dev/null 2>&1; then
        echo "       Versión detectada: $(python3 --version 2>&1)" >&2
    fi
    echo "       Descárgalo desde https://www.python.org/downloads/ y vuelve a ejecutar este script." >&2
    exit 1
fi

# 2) Crear el entorno virtual si no existe
if [[ ! -x ".venv/bin/python" ]]; then
    echo "==> Creando entorno virtual en .venv (solo la primera vez)..."
    "$PYTHON_BIN" -m venv .venv
fi

VENV_PY=".venv/bin/python"

# 3) Instalar dependencias solo si requirements.txt cambió desde la última vez
STAMP=".venv/.requirements.stamp"
CURRENT_HASH="$("$VENV_PY" -c "import hashlib,sys; print(hashlib.sha256(open('requirements.txt','rb').read()).hexdigest())")"
if [[ ! -f "$STAMP" ]] || [[ "$(cat "$STAMP")" != "$CURRENT_HASH" ]]; then
    echo "==> Instalando dependencias (puede tardar un par de minutos la primera vez)..."
    # Un .venv creado con `uv venv` no trae pip: lo agregamos con ensurepip.
    if ! "$VENV_PY" -m pip --version >/dev/null 2>&1; then
        "$VENV_PY" -m ensurepip --upgrade >/dev/null
    fi
    "$VENV_PY" -m pip install --upgrade pip --quiet
    "$VENV_PY" -m pip install -r requirements.txt --quiet
    echo "$CURRENT_HASH" > "$STAMP"
else
    echo "==> Dependencias al día."
fi

# 4) Lanzar la app
echo "==> Abriendo la app en el navegador (Ctrl+C para cerrar)..."
exec "$VENV_PY" -m streamlit run app.py "$@"
