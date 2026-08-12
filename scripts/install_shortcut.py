#!/usr/bin/env python3
"""
Install / Update Desktop Launcher Shortcut for Folio
===================================================
Run: python scripts/install_shortcut.py
"""

import os
import shutil
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_COMMAND = os.path.join(PROJECT_DIR, "scripts", "Folio.command")
DESKTOP_PATH = os.path.expanduser("~/Desktop/folio.command")

print(f"Installing Folio Desktop shortcut from: {SRC_COMMAND}")

try:
    if os.path.exists(DESKTOP_PATH):
        os.remove(DESKTOP_PATH)
    shutil.copyfile(SRC_COMMAND, DESKTOP_PATH)
    os.chmod(DESKTOP_PATH, 0o755)
    print(f"SUCCESS: {DESKTOP_PATH} has been updated!")
except Exception as e:
    print(f"\n[NOTE] Automatic Desktop write prevented by macOS TCC permissions: {e}")
    print("\nTo update your Desktop shortcut manually, run this command in Terminal:")
    print(f"  cp '{SRC_COMMAND}' ~/Desktop/folio.command && chmod +x ~/Desktop/folio.command\n")
