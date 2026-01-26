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
    pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to install dependencies" -ForegroundColor Red
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
