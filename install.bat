@echo off
setlocal enabledelayedexpansion

echo Quick Cuts Installer (Windows)
echo ==============================
echo.

:: Check for Python 3.8+
echo Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYTHON_VERSION=%%v
echo [OK] Python %PYTHON_VERSION% found

:: Check for Tesseract
echo.
echo Checking Tesseract OCR...
tesseract --version >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Tesseract not found.
    echo.
    echo Please install Tesseract OCR manually:
    echo   1. Download from: https://github.com/UB-Mannheim/tesseract/wiki
    echo   2. Run the installer
    echo   3. Add Tesseract to your PATH (usually C:\Program Files\Tesseract-OCR)
    echo.
    echo After installing Tesseract, run this script again.
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('tesseract --version 2^>^&1 ^| findstr /r "^tesseract"') do set TESS_VERSION=%%v
echo [OK] Tesseract %TESS_VERSION% found

:: Install Python package
echo.
echo Installing Quick Cuts...

:: Get script directory
set "SCRIPT_DIR=%~dp0"

:: Install with pip
pip install -e "%SCRIPT_DIR%" --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install Quick Cuts
    pause
    exit /b 1
)

echo [OK] Quick Cuts installed

:: Check if quick-cuts is accessible
echo.
where quick-cuts >nul 2>&1
if errorlevel 1 (
    echo [WARNING] quick-cuts not found in PATH
    echo.
    echo You may need to add Python Scripts to your PATH:
    for /f "delims=" %%p in ('python -c "import site; print(site.USER_SITE.replace('site-packages', 'Scripts'))"') do set SCRIPTS_PATH=%%p
    echo   !SCRIPTS_PATH!
    echo.
    echo Or try running: python -m quick_cuts.cli
)

echo.
echo ==============================
echo [OK] Installation complete!
echo ==============================
echo.
echo Usage:
echo   quick-cuts                              # Interactive mode
echo   quick-cuts fetch "keyword" -n 10        # Download images
echo   quick-cuts align input/ -w "word"       # Align images
echo.

pause
