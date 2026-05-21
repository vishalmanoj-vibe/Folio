#!/bin/bash
# build.sh
# Build script to compile Folio into a native macOS app bundle.

set -e

echo "==========================================="
echo "        Folio App macOS Compilation        "
echo "==========================================="

# 1. Active virtual environment
if [ -d "venv" ]; then
    echo "[INFO] Activating virtual environment..."
    source venv/bin/activate
else
    echo "[ERROR] Virtual environment 'venv' not found in workspace."
    exit 1
fi

# 2. Ensure dependencies are met
# echo "[INFO] Verifying packages..."
# pip install --upgrade pip
# pip install -r requirements.txt

# if ! command -v pyinstaller &> /dev/null; then
#     echo "[INFO] Installing PyInstaller..."
#     pip install pyinstaller
# fi

# 3. Clean prior compilations
echo "[INFO] Cleaning previous builds..."
rm -rf build dist

# 4. Run PyInstaller
echo "[INFO] Compiling native macOS App Bundle..."
export PYINSTALLER_CACHE_DIR="$PWD/.pyinstaller_cache"
pyinstaller --noconfirm folio.spec

# 5. Verify compilation
if [ -d "dist/Folio.app" ]; then
    echo "==========================================="
    echo "   ✓ SUCCESS: Folio.app Compiled!         "
    echo "   Location: dist/Folio.app               "
    echo "==========================================="
else
    echo "[ERROR] Compilation failed: dist/Folio.app not found."
    exit 1
fi
