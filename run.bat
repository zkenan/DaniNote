@echo off
chcp 65001 >nul
echo 正在启动张张便签 (Znote)...

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo 正在创建虚拟环境...
    python -m venv venv
    if errorlevel 1 (
        echo 创建虚拟环境失败，请检查Python安装
        pause
        exit /b 1
    )
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install dependencies if needed
if not exist "venv\Lib\site-packages\PySide6" (
    echo 正在安装依赖...
    pip install -r requirements.txt
)

REM Run the application
echo 启动程序...
python main.py

REM Keep window open if error
if errorlevel 1 (
    echo 程序异常退出，错误代码: %errorlevel%
    pause
)