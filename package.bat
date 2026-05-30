@echo off
chcp 65001 >nul
echo ============================================
echo   张张便签 (Znote) - 打包脚本
echo ============================================
echo.

cd /d "%~dp0"

:: 优先使用项目 venv 中的 Python
if exist "venv\Scripts\python.exe" (
    set PYTHON_EXE=venv\Scripts\python.exe
) else (
    set PYTHON_EXE=python.exe
)

echo 使用 Python：%PYTHON_EXE%
echo.

:: 运行 Python 打包脚本
echo 开始打包...
echo.
"%PYTHON_EXE%" package.py

pause
