@echo off
echo 🏗️  DDR Generator - Setup & Run
echo ================================

REM Check for Python
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Python 3 is required. Please install Python 3.8+
    pause
    exit /b 1
)

REM Create virtual environment if not exists
if not exist "venv" (
    echo 📦 Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install dependencies
echo 📥 Installing dependencies...
pip install -r requirements.txt -q

REM Check for .env file
if not exist ".env" (
    echo ⚠️  No .env file found. Creating from .env.example...
    copy .env.example .env
    echo    Please edit .env and add your API keys.
    pause
    exit /b 1
)

REM Create directories
if not exist "input" mkdir input
if not exist "output" mkdir output
if not exist "temp" mkdir temp

echo.
echo ✅ Setup complete!
echo.
echo 📂 Place your PDFs in the 'input\' directory, or run:
echo    python main.py -i "inspection.pdf" -t "thermal.pdf"
echo.
echo 🚀 Starting DDR Generator...
echo.

REM Run with provided arguments or look in input directory
if "%~1"=="" (
    python main.py
) else (
    python main.py %*
)

pause