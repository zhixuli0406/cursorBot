# CursorBot PowerShell Startup Script
# Run: .\start.ps1

$Host.UI.RawUI.WindowTitle = "CursorBot"

Write-Host "========================================"
Write-Host "         CursorBot Quick Start"
Write-Host "========================================" 
Write-Host ""

# Change to script directory
Set-Location $PSScriptRoot
Write-Host "[INFO] Working directory: $(Get-Location)" -ForegroundColor Cyan
Write-Host ""

# Check Python
Write-Host "[INFO] Checking Python..." -ForegroundColor Yellow

$usePy312 = $false
$pythonCmd = "python"

# First check if Python 3.12 is already available via py launcher
try {
    $py312Version = py -3.12 --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] $py312Version (via py launcher)" -ForegroundColor Green
        $usePy312 = $true
        $pythonCmd = "py -3.12"
    }
} catch {}

if (-not $usePy312) {
    try {
        $pythonVersion = python --version 2>&1
        
        # Check if Python version is too new (3.13+)
        if ($pythonVersion -match "3\.(1[3-9]|[2-9][0-9])") {
            Write-Host "[WARN] $pythonVersion is too new!" -ForegroundColor Yellow
            Write-Host "[INFO] Will install Python 3.12 automatically..." -ForegroundColor Yellow
            
            # Install Python 3.12
            Write-Host ""
            Write-Host "============================================================"
            Write-Host "   Installing Python 3.12" -ForegroundColor Cyan
            Write-Host "============================================================"
            Write-Host ""
            
            # Try winget first
            $wingetExists = Get-Command winget -ErrorAction SilentlyContinue
            if ($wingetExists) {
                Write-Host "[INFO] Installing Python 3.12 via winget..." -ForegroundColor Yellow
                winget install Python.Python.3.12 --accept-package-agreements --accept-source-agreements
                
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "[OK] Python 3.12 installed via winget" -ForegroundColor Green
                    Write-Host ""
                    Write-Host "[INFO] Please RESTART this script to use Python 3.12" -ForegroundColor Yellow
                    Read-Host "Press Enter to exit"
                    exit 0
                }
                Write-Host "[WARN] winget installation failed, trying manual download..." -ForegroundColor Yellow
            }
            
            # Manual download
            Write-Host "[INFO] Downloading Python 3.12 installer..." -ForegroundColor Yellow
            $pyInstaller = "$env:TEMP\python-3.12.8-amd64.exe"
            
            try {
                [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
                Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe" -OutFile $pyInstaller -UseBasicParsing
                
                if (Test-Path $pyInstaller) {
                    Write-Host "[INFO] Installing Python 3.12..." -ForegroundColor Yellow
                    Start-Process -FilePath $pyInstaller -ArgumentList "/passive", "InstallAllUsers=0", "PrependPath=1", "Include_test=0" -Wait
                    Remove-Item $pyInstaller -Force -ErrorAction SilentlyContinue
                    
                    Write-Host "[OK] Python 3.12 installation completed" -ForegroundColor Green
                    Write-Host "[INFO] Please RESTART this script to use Python 3.12" -ForegroundColor Yellow
                    Read-Host "Press Enter to exit"
                    exit 0
                }
            } catch {
                Write-Host "[ERROR] Failed to download Python installer: $_" -ForegroundColor Red
                Write-Host "[INFO] Please download manually from: https://www.python.org/downloads/release/python-3128/" -ForegroundColor Cyan
                Read-Host "Press Enter to exit"
                exit 1
            }
        } else {
            Write-Host "[OK] $pythonVersion" -ForegroundColor Green
        }
    } catch {
        Write-Host "[ERROR] Python not found. Installing Python 3.12..." -ForegroundColor Yellow
        
        # Try to install Python 3.12
        $wingetExists = Get-Command winget -ErrorAction SilentlyContinue
        if ($wingetExists) {
            winget install Python.Python.3.12 --accept-package-agreements --accept-source-agreements
            Write-Host "[INFO] Please RESTART this script after installation" -ForegroundColor Yellow
            Read-Host "Press Enter to exit"
            exit 0
        } else {
            Write-Host "[ERROR] Please install Python 3.12 from: https://www.python.org/downloads/release/python-3128/" -ForegroundColor Red
            Read-Host "Press Enter to exit"
            exit 1
        }
    }
}

# Delete old venv if using Python 3.12 and venv was created with different version
if ($usePy312 -and (Test-Path "venv")) {
    Write-Host ""
    Write-Host "[INFO] Checking venv Python version..." -ForegroundColor Yellow
    $venvVersion = & .\venv\Scripts\python --version 2>&1
    if ($venvVersion -notmatch "3\.12") {
        Write-Host "[WARN] venv was created with different Python version" -ForegroundColor Yellow
        Write-Host "[INFO] Deleting old venv..." -ForegroundColor Yellow
        Remove-Item -Recurse -Force venv
        Write-Host "[OK] Old venv deleted" -ForegroundColor Green
    }
}

# Check/Create venv
Write-Host ""
if (-not (Test-Path "venv")) {
    Write-Host "[INFO] Creating virtual environment..." -ForegroundColor Yellow
    if ($usePy312) {
        Write-Host "[INFO] Using Python 3.12..." -ForegroundColor Cyan
        py -3.12 -m venv venv
    } else {
        python -m venv venv
    }
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to create venv" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
    Write-Host "[OK] Virtual environment created" -ForegroundColor Green
} else {
    Write-Host "[OK] Virtual environment exists" -ForegroundColor Green
}

# Activate venv
Write-Host ""
Write-Host "[INFO] Activating virtual environment..." -ForegroundColor Yellow
if (Test-Path ".\venv\Scripts\Activate.ps1") {
    & .\venv\Scripts\Activate.ps1
    Write-Host "[OK] Virtual environment activated" -ForegroundColor Green
} else {
    Write-Host "[ERROR] venv\Scripts\Activate.ps1 not found" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Upgrade pip first (important for pre-built wheels)
Write-Host ""
Write-Host "[INFO] Upgrading pip to latest version..." -ForegroundColor Yellow
python -m pip install --upgrade pip --quiet 2>$null
Write-Host "[OK] pip upgraded" -ForegroundColor Green

# Check .env
Write-Host ""
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
} else {
    Write-Host "[OK] .env file exists" -ForegroundColor Green
}

# Install dependencies
Write-Host ""
Write-Host "[INFO] Checking dependencies..." -ForegroundColor Yellow
$installed = pip show python-telegram-bot 2>$null
if (-not $installed) {
    Write-Host "[INFO] Installing dependencies..." -ForegroundColor Yellow
    Write-Host ""
    
    # Try pre-built packages first (no compilation)
    Write-Host "[INFO] Installing packages (pre-built only, no compilation)..." -ForegroundColor Yellow
    pip install -r requirements.txt --only-binary :all: 2>$null
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "[WARN] Some pre-built packages not available." -ForegroundColor Yellow
        Write-Host "[INFO] Trying to install with compilation support..." -ForegroundColor Yellow
        Write-Host ""
        
        # Check if Rust is available
        $hasRust = Get-Command rustc -ErrorAction SilentlyContinue
        
        if ($hasRust) {
            Write-Host "[OK] Rust found, attempting source build..." -ForegroundColor Green
            pip install -r requirements.txt
        } else {
            Write-Host ""
            Write-Host "============================================================" -ForegroundColor Red
            Write-Host "   ERROR: Cannot install packages" -ForegroundColor Red
            Write-Host "============================================================" -ForegroundColor Red
            Write-Host ""
            Write-Host "   Pre-built packages are not available for your Python"
            Write-Host "   version. You need to install build tools:"
            Write-Host ""
            Write-Host "   Option 1: Install Rust (recommended)" -ForegroundColor Cyan
            Write-Host "   -----------------------------------------"
            Write-Host "   1. Open browser: https://rustup.rs"
            Write-Host "   2. Download and run rustup-init.exe"
            Write-Host "   3. Follow the prompts (default options are fine)"
            Write-Host "   4. CLOSE this window and run start.ps1 again"
            Write-Host ""
            Write-Host "   Option 2: Install Visual Studio Build Tools" -ForegroundColor Cyan
            Write-Host "   -----------------------------------------"
            Write-Host "   1. Open browser: https://visualstudio.microsoft.com/visual-cpp-build-tools/"
            Write-Host "   2. Download and install Build Tools"
            Write-Host "   3. Select 'Desktop development with C++'"
            Write-Host "   4. CLOSE this window and run start.ps1 again"
            Write-Host ""
            Write-Host "   Option 3: Use Python 3.11 or 3.12" -ForegroundColor Cyan
            Write-Host "   -----------------------------------------"
            Write-Host "   Pre-built packages are usually available for"
            Write-Host "   Python 3.11 and 3.12."
            Write-Host ""
            Write-Host "============================================================" -ForegroundColor Red
            Write-Host ""
            
            # Ask user what to do
            Write-Host "Press 1 to open Rust download page"
            Write-Host "Press 2 to open VS Build Tools download page"
            Write-Host "Press 3 to exit"
            Write-Host ""
            $choice = Read-Host "Your choice"
            
            switch ($choice) {
                "1" { Start-Process "https://rustup.rs" }
                "2" { Start-Process "https://visualstudio.microsoft.com/visual-cpp-build-tools/" }
            }
            
            Write-Host ""
            Write-Host "Please install the tools, then run this script again."
            Read-Host "Press Enter to exit"
            exit 1
        }
        
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[ERROR] Failed to install dependencies" -ForegroundColor Red
            Read-Host "Press Enter to exit"
            exit 1
        }
    }
    
    Write-Host "[OK] Dependencies installed" -ForegroundColor Green
} else {
    Write-Host "[OK] Dependencies already installed" -ForegroundColor Green
}

# Optional: Install Discord support
$envContent = Get-Content ".env" -ErrorAction SilentlyContinue
$discordEnabled = $envContent | Select-String "DISCORD_ENABLED=true"
if ($discordEnabled) {
    $discordInstalled = pip show discord.py 2>$null
    if (-not $discordInstalled) {
        Write-Host "[INFO] Installing Discord support..." -ForegroundColor Yellow
        pip install discord.py
    }
}

# Install Playwright (Browser tool)
Write-Host ""
Write-Host "[INFO] Checking Playwright..." -ForegroundColor Yellow
$playwrightInstalled = pip show playwright 2>$null
if (-not $playwrightInstalled) {
    Write-Host "[INFO] Installing Playwright..." -ForegroundColor Yellow
    pip install playwright
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[INFO] Installing Playwright browsers (this may take a while)..." -ForegroundColor Yellow
        playwright install chromium
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] Playwright installed" -ForegroundColor Green
        } else {
            Write-Host "[WARN] Playwright browser installation failed" -ForegroundColor Yellow
            Write-Host "[INFO] You can manually run: playwright install" -ForegroundColor Cyan
        }
    } else {
        Write-Host "[WARN] Playwright installation failed, skipping..." -ForegroundColor Yellow
    }
} else {
    Write-Host "[OK] Playwright already installed" -ForegroundColor Green
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
