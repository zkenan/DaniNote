#!/usr/bin/env python3
"""PyInstaller spec file for the Sticky Notes application."""

import os
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Application info
APP_NAME = "桌面便签"
APP_VERSION = "1.0.0"
APP_AUTHOR = "Sticky Notes Team"

# Paths
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
MAIN_FILE = os.path.join(PROJECT_ROOT, "main.py")
ICON_FILE = os.path.join(PROJECT_ROOT, "resources", "icon.ico")

# Build configuration
BUILD_DIR = os.path.join(PROJECT_ROOT, "build")
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")


def create_app():
    """Create the PyInstaller Analysis and EXE objects."""
    a = Analysis(
        [MAIN_FILE],
        pathex=[PROJECT_ROOT, SRC_DIR],
        binaries=[],
        datas=[
            (SRC_DIR, "src"),  # Include src directory
            (os.path.join(PROJECT_ROOT, "resources"), "resources"),  # Include resources
        ],
        hiddenimports=[
            "PySide6.QtCore",
            "PySide6.QtGui",
            "PySide6.QtWidgets",
            "PySide6.QtPrintSupport",
            "sqlite3",
            "json",
            "os",
            "sys",
            "ctypes",
            "shutil",
            "uuid",
            "datetime",
        ],
        hookspath=[],
        hooksconfig={},
        runtime_hooks=[],
        excludes=[
            "tkinter",
            "matplotlib",
            "numpy",
            "pandas",
            "scipy",
            "PIL",
        ],
        win_no_prefer_redirects=False,
        win_private_assemblies=False,
        cipher=None,  # Remove None for encryption
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
        name="桌面便签",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=ICON_FILE if os.path.exists(ICON_FILE) else None,
    )

    return exe


if __name__ == "__main__":
    # When running with PyInstaller, these objects are available in scope
    from PyInstaller.__main__ import run

    # Run PyInstaller directly
    args = [
        MAIN_FILE,
        "--name=桌面便签",
        "--onefile",
        "--windowed",
        "--add-data",
        f"{SRC_DIR}:src",
        "--hidden-import",
        "PySide6.QtCore",
        "--hidden-import",
        "PySide6.QtGui",
        "--hidden-import",
        "PySide6.QtWidgets",
        "--hidden-import",
        "sqlite3",
    ]

    if os.path.exists(ICON_FILE):
        args.extend(["--icon", ICON_FILE])

    run()