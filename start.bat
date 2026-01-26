@echo off
chcp 65001 >nul 2>&1
title CursorBot

echo ========================================
echo         CursorBot Quick Start
echo ========================================
echo.

:: Change to script directory
cd /d "%~dp0"
echo [INFO] Working directory: %CD%
echo.

:: ========== Check Python ==========
echo [INFO] Checking Python...

:: First check if Python 3.12 is already installed
set "PY312="
py -3.12 --version >nul 2>&1
if not errorlevel 1 (
    set "PY312=py -3.12"
    for /f "tokens=2" %%i in ('py -3.12 --version 2^>^&1') do echo [OK] Python %%i (3.12 found via py launcher)
    goto :pythonok
)

:: Check default python
python --version >nul 2>&1
if errorlevel 1 (
    echo [WARN] Python not found. Will install Python 3.12...
    goto :installpython
)

:: Get Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set "PYVER=%%i"
echo [INFO] Found Python %PYVER%

:: Check if Python version is too new (3.13+)
echo %PYVER% | findstr /b "3.13 3.14 3.15" >nul
if not errorlevel 1 (
    echo.
    echo [WARN] Python %PYVER% is too new! Many packages won't work.
    echo [INFO] Will install Python 3.12 automatically...
    goto :installpython
)

:: Python version is OK
echo [OK] Python %PYVER%
goto :pythonok

:installpython
echo.
echo ============================================================
echo   Installing Python 3.12
echo ============================================================
echo.

:: Try winget first
where winget >nul 2>&1
if not errorlevel 1 (
    echo [INFO] Installing Python 3.12 via winget...
    winget install Python.Python.3.12 --accept-package-agreements --accept-source-agreements
    if not errorlevel 1 (
        echo [OK] Python 3.12 installed via winget
        echo.
        echo [INFO] Refreshing environment...
        
        :: Refresh PATH
        for /f "tokens=2*" %%a in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do set "SYSPATH=%%b"
        for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "USERPATH=%%b"
        set "PATH=%SYSPATH%;%USERPATH%"
        
        :: Try py launcher
        py -3.12 --version >nul 2>&1
        if not errorlevel 1 (
            set "PY312=py -3.12"
            echo [OK] Python 3.12 ready
            goto :pythonok
        )
        
        echo [INFO] Please restart this script to use Python 3.12
        pause
        exit /b 0
    )
    echo [WARN] winget installation failed, trying manual download...
)

:: Manual download
echo [INFO] Downloading Python 3.12 installer...
set "PY_INSTALLER=%TEMP%\python-3.12.8-amd64.exe"

powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe' -OutFile '%PY_INSTALLER%'}" 2>nul

if not exist "%PY_INSTALLER%" (
    echo [ERROR] Failed to download Python installer
    echo [INFO] Please download manually from: https://www.python.org/downloads/release/python-3128/
    pause
    exit /b 1
)

echo [INFO] Installing Python 3.12...
echo [INFO] This will open the Python installer.
"%PY_INSTALLER%" /passive InstallAllUsers=0 PrependPath=1 Include_test=0

del "%PY_INSTALLER%" 2>nul

echo.
echo [OK] Python 3.12 installation completed
echo [INFO] Please RESTART this script to use Python 3.12
echo.
pause
exit /b 0

:pythonok
:: Delete old venv if using Python 3.12 and venv was created with different version
if defined PY312 (
    if exist "venv" (
        echo.
        echo [INFO] Checking venv Python version...
        venv\Scripts\python --version 2>nul | findstr /b "3.12" >nul
        if errorlevel 1 (
            echo [WARN] venv was created with different Python version
            echo [INFO] Deleting old venv...
            rd /s /q venv
            echo [OK] Old venv deleted
        )
    )
)
echo.

:: ========== Create venv if needed ==========
if not exist "venv" (
    echo [INFO] Creating virtual environment...
    if defined PY312 (
        echo [INFO] Using Python 3.12...
        %PY312% -m venv venv
    ) else (
        python -m venv venv
    )
    if errorlevel 1 (
        echo [ERROR] Failed to create venv
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created
) else (
    echo [OK] Virtual environment exists
)
echo.

:: ========== Activate venv ==========
echo [INFO] Activating virtual environment...
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] venv\Scripts\activate.bat not found
    pause
    exit /b 1
)
call venv\Scripts\activate.bat
echo [OK] Virtual environment activated
echo.

:: ========== Upgrade pip ==========
echo [INFO] Upgrading pip...
python -m pip install --upgrade pip
echo [OK] pip upgrade complete
echo.

:: ========== Check .env ==========
echo [INFO] Checking .env file...
if not exist ".env" (
    echo [WARN] .env file not found
    if exist "env.example" (
        echo [INFO] Copying env.example to .env
        copy env.example .env >nul
        echo [INFO] Please edit .env file and save it
        notepad .env
        pause
    ) else (
        echo [ERROR] No env.example found
        pause
        exit /b 1
    )
) else (
    echo [OK] .env file exists
)
echo.

:: ========== Install dependencies ==========
echo [INFO] Checking dependencies...
pip show python-telegram-bot >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing dependencies... this may take a while
    echo.
    pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo ============================================================
        echo   ERROR: Installation failed
        echo ============================================================
        echo.
        echo   Please install Rust first:
        echo   1. Open browser: https://rustup.rs
        echo   2. Download and run rustup-init.exe
        echo   3. Restart your computer
        echo   4. Run this script again
        echo.
        echo   Press 1 to open Rust download page
        echo   Press 2 to exit
        echo.
        choice /c 12 /n /m "Your choice: "
        if errorlevel 2 goto :exitscript
        if errorlevel 1 start https://rustup.rs
        goto :exitscript
    )
    echo [OK] Dependencies installed
) else (
    echo [OK] Dependencies already installed
)
echo.

:: ========== Install Playwright (Browser tool) ==========
echo [INFO] Checking Playwright...
pip show playwright >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing Playwright...
    pip install playwright
    if errorlevel 1 (
        echo [WARN] Playwright installation failed, skipping...
    ) else (
        echo [INFO] Installing Playwright browsers... this may take a while
        playwright install chromium
        if errorlevel 1 (
            echo [WARN] Playwright browser installation failed
            echo [INFO] You can manually run: playwright install
        ) else (
            echo [OK] Playwright installed
        )
    )
) else (
    echo [OK] Playwright already installed
)
echo.

:: ========== Ready to start ==========
echo ========================================
echo   All checks passed!
echo ========================================
echo.
echo Press any key to start CursorBot...
pause >nul

:: ========== Start bot ==========
echo.
echo ========================================
echo         Starting CursorBot...
echo ========================================
echo Press Ctrl+C to stop
echo.

python -m src.main

echo.
echo [INFO] CursorBot stopped
pause
goto :eof

:exitscript
echo.
echo Please install the required tools and try again.
pause
exit /b 1
