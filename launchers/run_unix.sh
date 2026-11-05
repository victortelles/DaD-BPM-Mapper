#!/usr/bin/env bash
# ==============================================================================
# Dead as Disco - BPM & BeatSync Studio Unix Orchestrator
# Bilingual (Spanish/English) 4-step launcher for Linux and macOS
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$REPO_ROOT/.venv"
REQ_FILE="$REPO_ROOT/requirements.txt"
HASH_FILE="$VENV_DIR/.requirements.hash"
APP_FILE="$REPO_ROOT/app.py"

VENV_PYTHON="$VENV_DIR/bin/python3"
if [ ! -f "$VENV_PYTHON" ] && [ -f "$VENV_DIR/bin/python" ]; then
    VENV_PYTHON="$VENV_DIR/bin/python"
fi

pause_exit() {
    local code="${1:-1}"
    echo ""
    echo "Presione Enter para salir / Press Enter to exit..."
    if [ -t 0 ]; then
        read -r _ || true
    fi
    exit "$code"
}

compute_sha256() {
    local target="$1"
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$target" | awk '{print $1}'
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$target" | awk '{print $1}'
    elif [ -x "$VENV_PYTHON" ]; then
        "$VENV_PYTHON" -c "import hashlib, sys; print(hashlib.sha256(open(sys.argv[1], 'rb').read()).hexdigest())" "$target" 2>/dev/null || echo ""
    else
        echo ""
    fi
}

# ------------------------------------------------------------------------------
# [1/4] Comprobando requisitos / Checking prerequisites...
# ------------------------------------------------------------------------------
echo ""
echo "[1/4] Comprobando requisitos / Checking prerequisites..."

SELECTED_PYTHON=""
FOUND_VERSION=""
OUTDATED_VERSION=""

for cand in python3 python3.12 python3.11 python3.10 python; do
    if command -v "$cand" >/dev/null 2>&1; then
        ver=$("$cand" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" 2>/dev/null || true)
        if [ -n "$ver" ]; then
            if "$cand" -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" 2>/dev/null; then
                SELECTED_PYTHON="$cand"
                FOUND_VERSION="$ver"
                break
            elif [ -z "$OUTDATED_VERSION" ]; then
                OUTDATED_VERSION="$ver"
            fi
        fi
    fi
done

if [ -z "$SELECTED_PYTHON" ] && [ -f "$VENV_PYTHON" ]; then
    ver=$("$VENV_PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" 2>/dev/null || true)
    if [ -n "$ver" ] && "$VENV_PYTHON" -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" 2>/dev/null; then
        FOUND_VERSION="$ver"
    fi
fi

if [ -z "$FOUND_VERSION" ]; then
    echo ""
    echo "================================================================================"
    echo "  [ERROR] Python 3.10+ no encontrado / Python 3.10+ not found"
    echo "================================================================================"
    if [ -n "$OUTDATED_VERSION" ]; then
        echo "  Se detecto Python $OUTDATED_VERSION, pero se requiere version 3.10 o superior."
        echo "  Detected Python $OUTDATED_VERSION, but version 3.10 or higher is required."
    else
        echo "  No se detecto ninguna instalacion valida de Python 3.10+ en el sistema."
        echo "  No valid Python 3.10+ installation was detected on your system."
    fi
    echo ""
    echo "  Descargue e instale Python 3.10 o superior desde / Please download and install from:"
    echo "  https://www.python.org/downloads/"
    echo ""
    echo "  En distribuciones Linux Debian/Ubuntu: sudo apt install python3 python3-venv"
    echo "  On Debian/Ubuntu distributions: sudo apt install python3 python3-venv"
    echo "================================================================================"
    pause_exit 1
fi

echo "      Requisitos / Requirements: Python $FOUND_VERSION compatible detectado / detected."

# ------------------------------------------------------------------------------
# [2/4] Configurando entorno virtual / Setting up virtual environment...
# ------------------------------------------------------------------------------
echo ""
echo "[2/4] Configurando entorno virtual / Setting up virtual environment..."

if [ ! -f "$VENV_PYTHON" ]; then
    echo "      Creando entorno virtual en .venv / Creating virtual environment in .venv..."
    set +e
    if [ -n "$SELECTED_PYTHON" ]; then
        "$SELECTED_PYTHON" -m venv "$VENV_DIR"
    else
        python3 -m venv "$VENV_DIR"
    fi
    VENV_STATUS=$?
    set -e

    if [ $VENV_STATUS -ne 0 ] || [ ! -f "$VENV_PYTHON" ]; then
        echo ""
        echo "[ERROR] No se pudo crear el entorno virtual / Failed to create virtual environment (.venv)."
        echo "En distribuciones Debian/Ubuntu instale: sudo apt install python3-venv"
        echo "On Debian/Ubuntu distributions install: sudo apt install python3-venv"
        pause_exit 2
    fi
    echo "      Entorno virtual .venv creado exitosamente / Virtual environment created successfully."
else
    echo "      Entorno Virtual / Virtual Environment: .venv listo / ready."
fi

# ------------------------------------------------------------------------------
# [3/4] Instalando dependencias / Installing dependencies...
# ------------------------------------------------------------------------------
echo ""
echo "[3/4] Instalando dependencias / Installing dependencies..."

if [ ! -f "$REQ_FILE" ]; then
    echo "      [ADVERTENCIA] No se encontro requirements.txt / requirements.txt not found."
else
    CURRENT_HASH=$(compute_sha256 "$REQ_FILE")
    SAVED_HASH=""
    if [ -f "$HASH_FILE" ]; then
        SAVED_HASH=$(tr -d ' \r\n' < "$HASH_FILE" 2>/dev/null || true)
    fi

    if [ -n "$CURRENT_HASH" ] && [ "$SAVED_HASH" = "$CURRENT_HASH" ]; then
        echo "      Dependencias / Dependencies: Dependencias al dia (Cache valida) / Dependencies up to date (Cache hit)."
    else
        echo "      Instalando o actualizando dependencias / Installing or updating dependencies..."
        set +e
        "$VENV_PYTHON" -m pip install --disable-pip-version-check -r "$REQ_FILE"
        PIP_STATUS=$?
        set -e
        if [ $PIP_STATUS -ne 0 ]; then
            echo ""
            echo "[ERROR] Fallo la instalacion de dependencias con pip / pip install failed."
            pause_exit 3
        fi
        if [ -n "$CURRENT_HASH" ]; then
            printf "%s" "$CURRENT_HASH" > "$HASH_FILE"
        fi
        echo "      Dependencias / Dependencies: Sincronizadas exitosamente / Dependencies synced successfully."
    fi
fi

# ------------------------------------------------------------------------------
# [4/4] Iniciando DaD BPM Studio / Starting DaD BPM Studio...
# ------------------------------------------------------------------------------
echo ""
echo "[4/4] Iniciando DaD BPM Studio / Starting DaD BPM Studio..."
echo "      Iniciando App / Starting Studio: Abriendo interfaz en navegador / Opening studio interface..."
echo "      URL: http://localhost:8501"
echo ""

set +e
"$VENV_PYTHON" -m streamlit run "$APP_FILE" "$@"
APP_EXIT_CODE=$?
set -e

if [ $APP_EXIT_CODE -ne 0 ]; then
    echo ""
    echo "[!] La aplicacion se cerro con codigo / Studio exited with code: $APP_EXIT_CODE"
    pause_exit "$APP_EXIT_CODE"
fi

exit 0
