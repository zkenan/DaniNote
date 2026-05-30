# ============================================
#   张张便签 (Znote) - PyInstaller 打包脚本 (PowerShell)
# ============================================

$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "   张张便签 (Znote) v0.1.0 - 打包脚本" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

Set-Location $PSScriptRoot

# ── 获取时间戳 ──
$timestamp = Get-Date -Format "yyyyMMddHHmm"
$exeName = "Znote_Win64_v0.1.0_$timestamp"

# ── 自动检测 Python 环境：优先使用项目 venv ──
$venvPython = Join-Path $PSScriptRoot "venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $pythonExe = $venvPython
} else {
    $pythonExe = "python.exe"
}

Write-Host "使用 Python: $pythonExe" -ForegroundColor Gray
Write-Host ""

# ── 清理旧构建 ──
Write-Host "[1/3] 清理旧构建文件..." -ForegroundColor Yellow
if (Test-Path "build") { Remove-Item "build" -Recurse -Force }
if (Test-Path "dist") { Remove-Item "dist" -Recurse -Force }
Get-ChildItem "*.spec" | Remove-Item -Force
Write-Host "       完成" -ForegroundColor Green
Write-Host ""

# ── 打包 ──
Write-Host "[2/3] 开始打包 -> $exeName.exe（约 5~15 分钟，请耐心等待）..." -ForegroundColor Yellow
Write-Host ""

$pyinstallerArgs = @(
    "-m", "PyInstaller",
    "--onefile",
    "--windowed",
    "--name=$exeName",
    "--icon=assets\app.ico",
    "--add-data=src;src",
    "--add-data=assets;assets",
    "--add-data=version.py;.",
    "--hidden-import=PySide6.QtCore",
    "--hidden-import=PySide6.QtGui",
    "--hidden-import=PySide6.QtWidgets",
    "--hidden-import=PySide6.QtPrintSupport",
    "--hidden-import=sqlite3",
    "--hidden-import=ctypes",
    "--hidden-import=ctypes.wintypes",
    "--hidden-import=json",
    "--hidden-import=datetime",
    "--hidden-import=version",
    "--hidden-import=src",
    "--hidden-import=src.utils",
    "--hidden-import=src.utils.notifier",
    "--hidden-import=src.models",
    "--hidden-import=src.views",
    "--hidden-import=src.views.main_window",
    "--hidden-import=src.views.note_editor",
    "--hidden-import=src.views.settings_panel",
    "--hidden-import=src.image_manager",
    "--collect-submodules=src.utils",
    "--collect-submodules=src.views",
    "--collect-submodules=src.models",
    "--exclude-module=tkinter",
    "--exclude-module=matplotlib",
    "--exclude-module=numpy",
    "--exclude-module=pandas",
    "--clean",
    "main.py"
)

& $pythonExe @pyinstallerArgs

# ── 结果检查 ──
Write-Host ""
if ($LASTEXITCODE -eq 0) {
    $exePath = "dist\$exeName.exe"
    if (Test-Path $exePath) {
        $sizeMB = [math]::Round((Get-Item $exePath).Length / 1MB, 1)
        Write-Host "[3/3] 打包成功！" -ForegroundColor Green
        Write-Host "       文件: $exePath" -ForegroundColor White
        Write-Host "       大小: $sizeMB MB" -ForegroundColor White
    } else {
        Write-Host "[3/3] 打包完成但未找到 EXE 文件" -ForegroundColor Red
    }
} else {
    Write-Host "[3/3] 打包失败，请检查上方错误信息" -ForegroundColor Red
}

Write-Host ""
Read-Host "按 Enter 退出"
