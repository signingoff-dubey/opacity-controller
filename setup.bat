@echo off
:: ============================================================
::  Opacity Controller — One-click Setup & Run
::  Double-click this file. It handles everything.
:: ============================================================

:: ── Auto-elevate to Administrator ───────────────────────────
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Requesting administrator privileges...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

:: ── Move to script's own directory ──────────────────────────
cd /d "%~dp0"

color 0A
echo.
echo  =========================================
echo   Opacity Controller — Setup
echo  =========================================
echo.

:: ── Check if Python is already installed ────────────────────
python --version >nul 2>&1
if %errorLevel% == 0 (
    echo  [OK] Python already installed.
    goto :install_packages
)

echo  [..] Python not found. Downloading installer...
echo.

:: ── Download Python installer via PowerShell ────────────────
powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.4/python-3.12.4-amd64.exe' -OutFile '%TEMP%\python_installer.exe'"

if not exist "%TEMP%\python_installer.exe" (
    echo  [ERROR] Download failed. Check your internet connection.
    pause
    exit /b 1
)

echo  [..] Installing Python (this takes ~1 min)...
echo.

:: Install Python silently with PATH and pip enabled
"%TEMP%\python_installer.exe" /quiet InstallAllUsers=1 PrependPath=1 Include_pip=1 Include_launcher=1

:: Refresh PATH in this session so python works immediately
for /f "tokens=*" %%i in ('powershell -Command "[System.Environment]::GetEnvironmentVariable(\"PATH\", \"Machine\")"') do set "PATH=%%i"

:: Wait a moment for install to finish
timeout /t 3 /nobreak >nul

python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo  [ERROR] Python installation failed.
    echo          Try downloading manually from python.org
    pause
    exit /b 1
)

echo  [OK] Python installed successfully.
echo.

:install_packages
:: ── Install Python packages ──────────────────────────────────
echo  [..] Installing packages (pywin32, pystray, pillow, keyboard)...
echo.

python -m pip install --upgrade pip --quiet
python -m pip install pywin32 pystray pillow keyboard --quiet

if %errorLevel% neq 0 (
    echo  [ERROR] Package install failed. Check internet connection.
    pause
    exit /b 1
)

echo  [OK] Packages installed.
echo.

:: ── pywin32 post-install (registers DLLs) ───────────────────
echo  [..] Registering pywin32 DLLs...
python -m pywin32_postinstall -install >nul 2>&1
echo  [OK] Done.
echo.

:: ── Check main.py exists ─────────────────────────────────────
if not exist "%~dp0main.py" (
    echo  [ERROR] main.py not found in this folder.
    echo          Make sure setup.bat is in the same folder as main.py
    pause
    exit /b 1
)

:: ── All done — launch the app ────────────────────────────────
echo  =========================================
echo   All done! Launching Opacity Controller
echo  =========================================
echo.
echo  - Tray icon will appear bottom-right
echo  - Alt+T  =  toggle transparency on focused window
echo  - Right-click tray icon  =  pick any window
echo.
echo  (You can close this window now)
echo.

python "%~dp0main.py"

pause
