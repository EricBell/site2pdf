# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from PyInstaller.utils.hooks import collect_data_files

# Get the project root directory
project_root = os.path.dirname(os.path.abspath(SPEC))

# Add src directory to Python path
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Collect data files for weasyprint and other dependencies
datas = []

# Include config files
if os.path.exists(os.path.join(project_root, 'config.yaml')):
    datas.append((os.path.join(project_root, 'config.yaml'), '.'))

# Collect weasyprint data files (CSS, fonts, etc.)
try:
    weasyprint_datas = collect_data_files('weasyprint')
    datas.extend(weasyprint_datas)
except ImportError:
    pass

# Collect other package data files
try:
    pillow_datas = collect_data_files('PIL')
    datas.extend(pillow_datas)
except ImportError:
    pass

# Hidden imports that PyInstaller might miss
hiddenimports = [
    'weasyprint',
    'weasyprint.css',
    'weasyprint.css.targets',
    'weasyprint.html',
    'weasyprint.pdf',
    'cairocffi',
    'cffi',
    'cssselect2',
    'tinycss2',
    'fonttools',
    'PIL._tkinter_finder',
    'reportlab.pdfgen',
    'reportlab.lib',
    'yaml',
    'click',
    'requests',
    'bs4',
    'lxml',
    'urllib3',
    'dotenv',
    'tqdm',
]

a = Analysis(
    [os.path.join(project_root, 'run.py')],
    pathex=[src_path, project_root],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='site2pdf',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)