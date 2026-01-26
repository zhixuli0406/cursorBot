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

:: ========================================
:: Check/Install Visual Studio Build Tools
:: ========================================
echo.
echo [INFO] Checking Visual Studio Build Tools...

:: Check if MSVC compiler exists
set "VS_INSTALLED=0"
where cl.exe >nul 2>&1
if !errorlevel! equ 0 (
    set "VS_INSTALLED=1"
    echo [OK] Visual Studio Build Tools found
) else (
    :: Check common VS paths
    if exist "C:\Program Files\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC" (
        set "VS_INSTALLED=1"
        echo [OK] Visual Studio Build Tools 2022 found
    ) else if exist "C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Tools\MSVC" (
        set "VS_INSTALLED=1"
        echo [OK] Visual Studio Build Tools 2019 found
    )
)

if "!VS_INSTALLED!"=="0" (
    echo [WARN] Visual Studio Build Tools not found.
    echo.
    
    :: Try winget first
    where winget >nul 2>&1
    if !errorlevel! equ 0 (
        echo [INFO] Attempting to install via winget...
        echo [INFO] This requires administrator privileges.
        echo.
        
        :: Install VS Build Tools with C++ workload
        winget install Microsoft.VisualStudio.2022.BuildTools --override "--wait --passive --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"
        
        if !errorlevel! equ 0 (
            echo [OK] Visual Studio Build Tools installed successfully
            echo [INFO] Please restart this script to use the new tools.
            pause
            exit /b 0
        ) else (
            echo [WARN] winget installation failed, trying manual download...
        )
    )
    
    :: Manual download fallback
    echo [INFO] Downloading Visual Studio Build Tools installer...
    set "VS_INSTALLER=%TEMP%\vs_buildtools.exe"
    
    powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://aka.ms/vs/17/release/vs_buildtools.exe' -OutFile '%VS_INSTALLER%'}" 2>nul
    
    if exist "!VS_INSTALLER!" (
        echo [INFO] Installing Visual Studio Build Tools...
        echo [INFO] This will open the Visual Studio Installer.
        echo [INFO] Please select "Desktop development with C++" and click Install.
        echo.
        
        start /wait "" "!VS_INSTALLER!" --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended --passive
        
        del "!VS_INSTALLER!" 2>nul
        
        echo.
        echo [INFO] Installation completed. Please restart this script.
        pause
        exit /b 0
    ) else (
        echo [WARN] Could not download VS Build Tools installer.
        echo [INFO] Please install manually from:
        echo        https://visualstudio.microsoft.com/visual-cpp-build-tools/
        echo [INFO] Continuing anyway - will try pre-built packages...
    )
)

:: ========================================
:: Check/Install Rust
:: ========================================
echo.
echo [INFO] Checking Rust installation...
where rustc >nul 2>&1
if !errorlevel! neq 0 (
    echo [WARN] Rust not found. Attempting to install...
    echo.
    
    :: Download rustup-init.exe
    set "RUSTUP_INSTALLER=%TEMP%\rustup-init.exe"
    
    powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://win.rustup.rs/x86_64' -OutFile '%RUSTUP_INSTALLER%'}" 2>nul
    
    if exist "!RUSTUP_INSTALLER!" (
        echo [INFO] Installing Rust (this may take a few minutes)...
        "!RUSTUP_INSTALLER!" -y --default-toolchain stable
        
        del "!RUSTUP_INSTALLER!" 2>nul
        
        :: Add Rust to current PATH
        set "PATH=%USERPROFILE%\.cargo\bin;!PATH!"
        
        :: Verify installation
        where rustc >nul 2>&1
        if !errorlevel! equ 0 (
            echo [OK] Rust installed successfully
            for /f "tokens=*" %%i in ('rustc --version 2^>^&1') do echo [OK] %%i
        ) else (
            echo [WARN] Rust installed but not in PATH.
            echo [INFO] Please restart this script to load Rust.
            pause
            exit /b 0
        )
    ) else (
        echo [WARN] Could not download Rust installer.
        echo [INFO] Please install manually from: https://rustup.rs
        echo [INFO] Continuing anyway - will try pre-built packages...
    )
) else (
    for /f "tokens=*" %%i in ('rustc --version 2^>^&1') do echo [OK] %%i
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
