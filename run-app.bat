@echo off
REM Ensure we run from the script's directory
cd /d "%~dp0"

set "NODE_ENV=development"
echo Starting Quick Cuts Desktop App...
echo.
echo Note: This requires Electron to be installed globally or locally.
echo If Electron is not installed, run: npm install -g electron
echo.

REM Prefer local Electron via npx for reliability on Windows
where npx >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Using npx to run Electron...
    npx electron .
    goto :eof
)

REM Fallback: Try global electron
where electron >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Using global Electron installation...
    electron .
    goto :eof
)

REM Fallback: Try local electron binary
if exist "node_modules\.bin\electron.cmd" (
    echo Using local Electron installation...
    node_modules\.bin\electron.cmd .
    goto :eof
)

echo ERROR: Electron not found!
echo.
echo Please install Electron using one of these commands:
echo   npm install -g electron    (global installation)
echo   npm install electron --save-dev    (local installation)
echo.
pause
exit /b 1