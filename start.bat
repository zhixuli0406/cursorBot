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
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+
    echo.
    pause
    exit /b 1
)
python --version
echo.

:: ========== Create venv if needed ==========
if not exist "venv" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
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
