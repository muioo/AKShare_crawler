@echo off
chcp 65001 >nul
echo =============================================
echo          Creating Virtual Environment
echo =============================================

cd /d "%~dp0%"

if not exist "stock_env\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv stock_env

    echo Installing dependencies...
    stock_env\Scripts\pip.exe install -r requirements.txt
) else (
    echo Checking dependencies...
    stock_env\Scripts\python.exe -c "import pandas" 2>nul
    if errorlevel 1 (
        echo Dependencies not found, installing...
        stock_env\Scripts\pip.exe install -r requirements.txt
    )
)

echo Starting program...
stock_env\Scripts\python.exe run_gui.py

pause