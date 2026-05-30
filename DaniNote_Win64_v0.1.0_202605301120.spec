# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = ['PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets', 'PySide6.QtPrintSupport', 'sqlite3', 'ctypes', 'ctypes.wintypes', 'json', 'datetime', 'version', 'src', 'src.utils', 'src.utils.notifier', 'src.models', 'src.views', 'src.views.main_window', 'src.views.note_editor', 'src.views.settings_panel', 'src.image_manager']
hiddenimports += collect_submodules('src.utils')
hiddenimports += collect_submodules('src.views')
hiddenimports += collect_submodules('src.models')


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('src', 'src'), ('assets', 'assets'), ('version.py', '.')],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'pandas'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='DaniNote_Win64_v0.1.0_202605301120',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets\\app.ico'],
)
