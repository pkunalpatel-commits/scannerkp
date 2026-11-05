# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for NSE OI Scanner
# Forces collection of PySide6 + shiboken6 + loguru

import sys
from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None

# Collect everything from these packages
pyside6_datas, pyside6_binaries, pyside6_hidden = collect_all('PySide6')
shiboken_datas, shiboken_binaries, shiboken_hidden = collect_all('shiboken6')
loguru_datas, loguru_binaries, loguru_hidden = collect_all('loguru')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=pyside6_binaries + shiboken_binaries + loguru_binaries,
    datas=pyside6_datas + shiboken_datas + loguru_datas + [
        ('config', 'config'),
        ('ui', 'ui'),
        ('core', 'core'),
    ],
    hiddenimports=[
        'PySide6',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtNetwork',
        'shiboken6',
        'loguru',
        'core.logger',
        'sqlalchemy',
        'pandas',
        'numpy',
        'requests',
        'websockets',
        'plyer',
    ] + pyside6_hidden + shiboken_hidden + loguru_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='NSE_OI_Scanner',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # windowed
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
    name='NSE_OI_Scanner',
)
