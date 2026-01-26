@echo off
chcp 65001 >nul
title CursorBot

echo ========================================
echo         CursorBot 快速啟動
echo ========================================
echo.

:: Check Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

:: Check/Install Rust (required for pydantic-core compilation)
echo [INFO] Checking Rust installation...
where rustc >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARN] Rust not found. Attempting to install...
    echo [INFO] Downloading rustup-init.exe...
    
    :: Download rustup-init.exe using PowerShell
    powershell -Command "Invoke-WebRequest -Uri 'https://win.rustup.rs/x86_64' -OutFile 'rustup-init.exe'"
    
    if exist "rustup-init.exe" (
        echo [INFO] Installing Rust (this may take a few minutes)...
        rustup-init.exe -y --default-toolchain stable
        del rustup-init.exe
        
        :: Add Rust to current PATH
        set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"
        
        echo [OK] Rust installed successfully
        echo [INFO] Please restart this script to ensure Rust is properly loaded
        pause
        exit /b 0
    ) else (
        echo [WARN] Could not download Rust installer
        echo [INFO] You can manually install from: https://rustup.rs
        echo [INFO] Continuing with pre-built packages...
    )
) else (
    for /f "tokens=*" %%i in ('rustc --version') do echo [OK] %%i
)

:: Check if venv exists
if not exist "venv" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create venv
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created
)

:: Activate venv
echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat

:: Upgrade pip first (important for pre-built wheels)
echo [INFO] Upgrading pip...
python -m pip install --upgrade pip >nul 2>&1
echo [OK] pip upgraded

:: Check .env file
if not exist ".env" (
    echo [WARN] .env file not found
    if exist "env.example" (
        echo [INFO] Copying env.example to .env
        copy env.example .env >nul
        echo [INFO] Please edit .env file with your settings
        notepad .env
        pause
    ) else (
        echo [ERROR] No env.example found
        pause
        exit /b 1
    )
)

:: Install dependencies
echo [INFO] Checking dependencies...
pip show python-telegram-bot >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Installing dependencies...
    
    :: Try pre-built packages first (avoid compilation)
    echo [INFO] Attempting to install pydantic with pre-built packages...
    pip install pydantic pydantic-core --only-binary :all: >nul 2>&1
    if %errorlevel% neq 0 (
        echo [WARN] Pre-built packages not available, trying source build...
        pip install pydantic pydantic-core
    )
    
    :: Install remaining dependencies
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
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
