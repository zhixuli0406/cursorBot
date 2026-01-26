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
echo [INFO] Upgrading pip to latest version...
python -m pip install --upgrade pip --quiet
echo [OK] pip upgraded

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
    
    :: Install all packages using pre-built wheels only (no compilation)
    echo [INFO] Installing packages (pre-built only, no compilation)...
    pip install -r requirements.txt --only-binary :all:
    
    if !errorlevel! neq 0 (
        echo.
        echo [WARN] Some pre-built packages not available.
        echo [INFO] Trying to install with compilation support...
        echo.
        
        :: Check if build tools are available
        where rustc >nul 2>&1
        set "HAS_RUST=!errorlevel!"
        
        if "!HAS_RUST!"=="0" (
            echo [OK] Rust found, attempting source build...
            pip install -r requirements.txt
        ) else (
            echo.
            echo ============================================================
            echo   ERROR: Cannot install packages
            echo ============================================================
            echo.
            echo   Pre-built packages are not available for your Python
            echo   version. You need to install build tools:
            echo.
            echo   Option 1: Install Rust (recommended)
            echo   -----------------------------------------
            echo   1. Open browser: https://rustup.rs
            echo   2. Download and run rustup-init.exe
            echo   3. Follow the prompts (default options are fine)
            echo   4. CLOSE this window and run start.bat again
            echo.
            echo   Option 2: Install Visual Studio Build Tools
            echo   -----------------------------------------
            echo   1. Open browser: https://visualstudio.microsoft.com/visual-cpp-build-tools/
            echo   2. Download and install Build Tools
            echo   3. Select "Desktop development with C++"
            echo   4. CLOSE this window and run start.bat again
            echo.
            echo   Option 3: Use Python 3.11 or 3.12
            echo   -----------------------------------------
            echo   Pre-built packages are usually available for
            echo   Python 3.11 and 3.12.
            echo.
            echo ============================================================
            echo.
            
            :: Ask user what to do
            echo Press 1 to open Rust download page
            echo Press 2 to open VS Build Tools download page
            echo Press 3 to exit
            echo.
            choice /c 123 /n /m "Your choice: "
            
            if !errorlevel! equ 1 (
                start https://rustup.rs
            ) else if !errorlevel! equ 2 (
                start https://visualstudio.microsoft.com/visual-cpp-build-tools/
            )
            
            echo.
            echo Please install the tools, then run this script again.
            pause
            exit /b 1
        )
        
        if !errorlevel! neq 0 (
            echo [ERROR] Failed to install dependencies
            echo.
            pause
            exit /b 1
        )
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
