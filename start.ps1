# CursorBot PowerShell Startup Script
# Run: .\start.ps1

$Host.UI.RawUI.WindowTitle = "CursorBot"

Write-Host "========================================"
Write-Host "         CursorBot Quick Start"
Write-Host "========================================" 
Write-Host ""

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[OK] $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python not found. Please install Python 3.10+" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Check/Install Rust (required for pydantic-core compilation)
Write-Host "[INFO] Checking Rust installation..." -ForegroundColor Yellow
$rustInstalled = Get-Command rustc -ErrorAction SilentlyContinue
if (-not $rustInstalled) {
    Write-Host "[WARN] Rust not found. Attempting to install..." -ForegroundColor Yellow
    Write-Host "[INFO] Downloading rustup-init.exe..." -ForegroundColor Yellow
    
    try {
        # Download rustup-init.exe
        $rustupUrl = "https://win.rustup.rs/x86_64"
        $rustupPath = "$env:TEMP\rustup-init.exe"
        Invoke-WebRequest -Uri $rustupUrl -OutFile $rustupPath -UseBasicParsing
        
        if (Test-Path $rustupPath) {
            Write-Host "[INFO] Installing Rust (this may take a few minutes)..." -ForegroundColor Yellow
            & $rustupPath -y --default-toolchain stable
            Remove-Item $rustupPath -Force
            
            # Add Rust to current PATH
            $env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
            
            Write-Host "[OK] Rust installed successfully" -ForegroundColor Green
            Write-Host "[INFO] Please restart this script to ensure Rust is properly loaded" -ForegroundColor Yellow
            Read-Host "Press Enter to exit"
            exit 0
        }
    } catch {
        Write-Host "[WARN] Could not download Rust installer: $_" -ForegroundColor Yellow
        Write-Host "[INFO] You can manually install from: https://rustup.rs" -ForegroundColor Cyan
        Write-Host "[INFO] Continuing with pre-built packages..." -ForegroundColor Yellow
    }
} else {
    $rustVersion = rustc --version
    Write-Host "[OK] $rustVersion" -ForegroundColor Green
}

# Check/Create venv
if (-not (Test-Path "venv")) {
    Write-Host "[INFO] Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to create venv" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
    Write-Host "[OK] Virtual environment created" -ForegroundColor Green
}

# Activate venv
Write-Host "[INFO] Activating virtual environment..." -ForegroundColor Yellow
& .\venv\Scripts\Activate.ps1

# Upgrade pip first (important for pre-built wheels)
Write-Host "[INFO] Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip 2>$null
Write-Host "[OK] pip upgraded" -ForegroundColor Green

# Check .env
if (-not (Test-Path ".env")) {
    Write-Host "[WARN] .env file not found" -ForegroundColor Yellow
    if (Test-Path "env.example") {
        Write-Host "[INFO] Copying env.example to .env" -ForegroundColor Yellow
        Copy-Item "env.example" ".env"
        Write-Host "[INFO] Please edit .env file with your settings" -ForegroundColor Yellow
        notepad .env
        Read-Host "Press Enter after editing .env"
    } else {
        Write-Host "[ERROR] No env.example found" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
}

# Install dependencies
Write-Host "[INFO] Checking dependencies..." -ForegroundColor Yellow
$installed = pip show python-telegram-bot 2>$null
if (-not $installed) {
    Write-Host "[INFO] Installing dependencies..." -ForegroundColor Yellow
    
    # Try pre-built packages first (avoid compilation)
    Write-Host "[INFO] Attempting to install pydantic with pre-built packages..." -ForegroundColor Yellow
    pip install pydantic pydantic-core --only-binary :all: 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[WARN] Pre-built packages not available, trying source build..." -ForegroundColor Yellow
        pip install pydantic pydantic-core
    }
    
    # Install remaining dependencies
    pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to install dependencies" -ForegroundColor Red
        Write-Host ""
        Write-Host "Possible solutions:" -ForegroundColor Cyan
        Write-Host "1. Install Visual Studio Build Tools: https://visualstudio.microsoft.com/visual-cpp-build-tools/" -ForegroundColor White
        Write-Host "2. Make sure Rust is installed: https://rustup.rs" -ForegroundColor White
        Write-Host "3. Use Python 3.11 or 3.12 for better pre-built support" -ForegroundColor White
        Write-Host ""
        Read-Host "Press Enter to exit"
        exit 1
    }
}

# Optional: Install Discord support
$discordEnabled = Get-Content ".env" | Select-String "DISCORD_ENABLED=true"
if ($discordEnabled) {
    $discordInstalled = pip show discord.py 2>$null
    if (-not $discordInstalled) {
        Write-Host "[INFO] Installing Discord support..." -ForegroundColor Yellow
        pip install discord.py
    }
}

# Start bot
Write-Host ""
Write-Host "========================================"
Write-Host "         Starting CursorBot..."
Write-Host "========================================" 
Write-Host ""
Write-Host "Press Ctrl+C to stop" -ForegroundColor Cyan
Write-Host ""

python -m src.main

Write-Host ""
Write-Host "[INFO] CursorBot stopped" -ForegroundColor Yellow
Read-Host "Press Enter to exit"
