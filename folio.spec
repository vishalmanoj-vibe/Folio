# folio.spec
# -*- mode: python ; coding: utf-8 -*-
import sys
import os
import dash_iconify
import dash_mantine_components
import dash_bootstrap_components

block_cipher = None

# Get path mappings for dash_iconify and UI packages to prevent asset resolution failures
datas = [
    ('pages', 'pages'),
    ('callbacks', 'callbacks'),
    ('components', 'components'),
    ('services', 'services'),
    ('core', 'core'),
    ('config', 'config'),
    ('assets', 'assets'),
    ('data/cache', 'data/cache'),  # Bundling cache templates only (excludes local portfolio.db)
    (dash_iconify.__path__[0], 'dash_iconify'), # Bundling dash_iconify dynamically resolved package data
    (dash_mantine_components.__path__[0], 'dash_mantine_components'),
    (dash_bootstrap_components.__path__[0], 'dash_bootstrap_components'),
]

a = Analysis(
    ['folio_app.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'dash',
        'plotly',
        'yfinance',
        'webview',
        'keyring',
        'jinja2',
        'pandas',
        'pytz',
        'google.genai',
        'prophet',
        'dash_mantine_components',
        'dash_bootstrap_components',
        'dash_iconify',
        'holidays',
        'holidays.countries',
        'holidays.registry',
        'matplotlib',
        'reportlab',
        'playwright',
        'dotenv',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['data/portfolio.db', 'portfolio.db'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Folio',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Folio',
)

app = BUNDLE(
    coll,
    name='Folio.app',
    icon='assets/icon.png',
    bundle_identifier='com.vishalmanoj.folio',
    info_plist={
        'NSPrincipalClass': 'NSApplication',
        'NSAppleScriptEnabled': False,
        'CFBundlePackageType': 'APPL',
        'LSMinimumSystemVersion': '10.13.0',
    }
)
