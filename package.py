"""
张张便签 (DaniNote) - PyInstaller 打包脚本
用法：双击 package.bat，或直接运行 python package.py
"""
import os
import shutil
import subprocess
import sys
from datetime import datetime

# 自动检测 Python 环境：优先使用项目 venv，其次使用系统 Python
def _find_python():
    project_root = os.path.dirname(os.path.abspath(__file__))
    venv_python = os.path.join(project_root, "venv", "Scripts", "python.exe")
    if os.path.exists(venv_python):
        return venv_python
    # fallback: 使用当前 Python
    return sys.executable

PYTHON_EXE = _find_python()
APP_VERSION = "0.1.0"


def main():
    project_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_root)

    # 生成时间戳
    timestamp = datetime.now().strftime("%Y%m%d%H%M")
    exe_name = f"DaniNote_Win64_v{APP_VERSION}_{timestamp}"

    print("=" * 44)
    print(f"   张张便签 DaniNote v{APP_VERSION} - PyInstaller 打包")
    print("=" * 44)
    print()

    # 1. 清理旧构建
    print("[1/3] 清理旧构建文件...")
    for path in ["build", "dist"]:
        if os.path.exists(path):
            shutil.rmtree(path)
    for f in os.listdir("."):
        if f.endswith(".spec"):
            os.remove(f)
    print("       完成")
    print()

    # 2. 打包参数
    cmd = [
        PYTHON_EXE, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", exe_name,
        "--icon", "assets/app.ico",
        "--add-data", f"src{os.pathsep}src",
        "--add-data", f"assets{os.pathsep}assets",
        "--add-data", f"version.py{os.pathsep}.",
        "--hidden-import", "PySide6.QtCore",
        "--hidden-import", "PySide6.QtGui",
        "--hidden-import", "PySide6.QtWidgets",
        "--hidden-import", "PySide6.QtPrintSupport",
        "--hidden-import", "sqlite3",
        "--hidden-import", "ctypes",
        "--hidden-import", "ctypes.wintypes",
        "--hidden-import", "json",
        "--hidden-import", "datetime",
        "--hidden-import", "version",
        "--hidden-import", "src",
        "--hidden-import", "src.utils",
        "--hidden-import", "src.utils.notifier",
        "--hidden-import", "src.models",
        "--hidden-import", "src.views",
        "--hidden-import", "src.views.main_window",
        "--hidden-import", "src.views.note_editor",
        "--hidden-import", "src.views.settings_panel",
        "--hidden-import", "src.image_manager",
        "--collect-submodules", "src.utils",
        "--collect-submodules", "src.views",
        "--collect-submodules", "src.models",
        "--exclude-module", "tkinter",
        "--exclude-module", "matplotlib",
        "--exclude-module", "numpy",
        "--exclude-module", "pandas",
        "--clean",
        "main.py",
    ]

    print(f"[2/3] 开始打包 -> {exe_name}.exe（约 5~15 分钟，请耐心等待）...")
    print()

    result = subprocess.run(cmd, cwd=project_root)

    # 3. 结果
    print()
    if result.returncode == 0:
        exe_path = os.path.join(project_root, "dist", f"{exe_name}.exe")
        if os.path.exists(exe_path):
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            print("[3/3] [成功] 打包成功！")
            print(f"       文件: {exe_path}")
            print(f"       大小: {size_mb:.1f} MB")
        else:
            print("[3/3] [失败] 打包完成但未找到 EXE 文件")
            sys.exit(1)
    else:
        print("[3/3] [失败] 打包失败，请检查上方错误信息")
        sys.exit(1)

    print()
    try:
        input("按 Enter 退出...")
    except (EOFError, KeyboardInterrupt):
        pass


if __name__ == "__main__":
    main()
