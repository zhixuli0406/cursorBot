@echo off
setlocal enabledelayedexpansion

:: Set UTF-8 encoding (ignore errors)
chcp 65001 >nul 2>&1

title CursorBot

echo ========================================
echo         CursorBot Quick Start
echo ========================================
echo.

:: Get script directory and change to it
cd /d "%~dp0"
echo [INFO] Working directory: %CD%
echo.

:: Check Python
echo [INFO] Checking Python...
where python >nul 2>&1
if !errorlevel! neq 0 (
    echo [ERROR] Python not found. Please install Python 3.10+
    echo.
    pause
    exit /b 1
)

:: Show Python version
for /f "tokens=*" %%i in ('python --version 2^>^&1') do echo [OK] %%i

:: Check/Install Rust (required for pydantic-core compilation)
echo.
echo [INFO] Checking Rust installation...
where rustc >nul 2>&1
if !errorlevel! neq 0 (
    echo [WARN] Rust not found.
    echo [INFO] Will try to use pre-built packages first.
    echo [INFO] If that fails, install Rust from: https://rustup.rs
    set "RUST_INSTALLED=0"
) else (
    for /f "tokens=*" %%i in ('rustc --version 2^>^&1') do echo [OK] %%i
    set "RUST_INSTALLED=1"
)

:: Check if venv exists
echo.
if not exist "venv" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to create venv
        echo.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created
) else (
    echo [OK] Virtual environment exists
)

:: Activate venv
echo.
echo [INFO] Activating virtual environment...
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    echo [OK] Virtual environment activated
) else (
    echo [ERROR] venv\Scripts\activate.bat not found
    echo.
    pause
    exit /b 1
)

:: Upgrade pip first (important for pre-built wheels)
echo.
echo [INFO] Upgrading pip...
python -m pip install --upgrade pip
if !errorlevel! neq 0 (
    echo [WARN] Failed to upgrade pip, continuing anyway...
) else (
    echo [OK] pip upgraded
)

:: Check .env file
echo.
if not exist ".env" (
    echo [WARN] .env file not found
    if exist "env.example" (
        echo [INFO] Copying env.example to .env
        copy env.example .env >nul
        echo [INFO] Please edit .env file with your settings
        notepad .env
        echo.
        pause
    ) else (
        echo [ERROR] No env.example found
        echo.
        pause
        exit /b 1
    )
) else (
    echo [OK] .env file exists
)

:: Install dependencies
echo.
echo [INFO] Checking dependencies...
pip show python-telegram-bot >nul 2>&1
if !errorlevel! neq 0 (
    echo [INFO] Installing dependencies...
    echo.
    
    :: Try pre-built packages first (avoid compilation)
    echo [INFO] Step 1: Installing pydantic with pre-built packages...
    pip install pydantic pydantic-core --only-binary :all:
    if !errorlevel! neq 0 (
        echo [WARN] Pre-built packages not available, trying source build...
        pip install pydantic pydantic-core
        if !errorlevel! neq 0 (
            echo.
            echo [ERROR] Failed to install pydantic-core
            echo.
            echo ============================================
            echo   Please install Rust manually:
            echo   1. Visit: https://rustup.rs
            echo   2. Download and run rustup-init.exe
            echo   3. Restart this script
            echo ============================================
            echo.
            pause
            exit /b 1
        )
    )
    
    :: Install remaining dependencies
    echo.
    echo [INFO] Step 2: Installing remaining dependencies...
    pip install -r requirements.txt
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to install dependencies
        echo.
        echo Possible solutions:
        echo 1. Install Visual Studio Build Tools: https://visualstudio.microsoft.com/visual-cpp-build-tools/
        echo 2. Make sure Rust is installed: https://rustup.rs
        echo 3. Use Python 3.11 or 3.12 for better pre-built support
        echo.
        pause
        exit /b 1
    )
    echo [OK] Dependencies installed
) else (
    echo [OK] Dependencies already installed
)

:: Start bot
echo.
echo ========================================
echo         Starting CursorBot...
echo ========================================
echo.
echo Press Ctrl+C to stop
echo.

python -m src.main

:: If exited
echo.
echo [INFO] CursorBot stopped
pause
