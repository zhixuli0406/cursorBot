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
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[OK] $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python not found. Please install Python 3.10+" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# ========================================
# Check/Install Visual Studio Build Tools
# ========================================
Write-Host ""
Write-Host "[INFO] Checking Visual Studio Build Tools..." -ForegroundColor Yellow

$vsInstalled = $false

# Check if cl.exe exists in PATH
$clExists = Get-Command cl.exe -ErrorAction SilentlyContinue
if ($clExists) {
    $vsInstalled = $true
    Write-Host "[OK] Visual Studio Build Tools found (cl.exe in PATH)" -ForegroundColor Green
} else {
    # Check common VS installation paths
    $vsPaths = @(
        "C:\Program Files\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC",
        "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC",
        "C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Tools\MSVC",
        "C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\VC\Tools\MSVC"
    )
    
    foreach ($path in $vsPaths) {
        if (Test-Path $path) {
            $vsInstalled = $true
            Write-Host "[OK] Visual Studio Build Tools found at: $path" -ForegroundColor Green
            break
        }
    }
}

if (-not $vsInstalled) {
    Write-Host "[WARN] Visual Studio Build Tools not found." -ForegroundColor Yellow
    Write-Host ""
    
    # Try winget first
    $wingetExists = Get-Command winget -ErrorAction SilentlyContinue
    if ($wingetExists) {
        Write-Host "[INFO] Attempting to install via winget..." -ForegroundColor Yellow
        Write-Host "[INFO] This requires administrator privileges." -ForegroundColor Yellow
        Write-Host ""
        
        try {
            $process = Start-Process -FilePath "winget" -ArgumentList "install", "Microsoft.VisualStudio.2022.BuildTools", "--override", "`"--wait --passive --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended`"" -Wait -PassThru
            
            if ($process.ExitCode -eq 0) {
                Write-Host "[OK] Visual Studio Build Tools installed successfully" -ForegroundColor Green
                Write-Host "[INFO] Please restart this script to use the new tools." -ForegroundColor Yellow
                Read-Host "Press Enter to exit"
                exit 0
            } else {
                Write-Host "[WARN] winget installation failed (exit code: $($process.ExitCode)), trying manual download..." -ForegroundColor Yellow
            }
        } catch {
            Write-Host "[WARN] winget installation failed: $_" -ForegroundColor Yellow
        }
    }
    
    # Manual download fallback
    Write-Host "[INFO] Downloading Visual Studio Build Tools installer..." -ForegroundColor Yellow
    $vsInstallerPath = "$env:TEMP\vs_buildtools.exe"
    
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri "https://aka.ms/vs/17/release/vs_buildtools.exe" -OutFile $vsInstallerPath -UseBasicParsing
        
        if (Test-Path $vsInstallerPath) {
            Write-Host "[INFO] Installing Visual Studio Build Tools..." -ForegroundColor Yellow
            Write-Host "[INFO] This will open the Visual Studio Installer." -ForegroundColor Cyan
            Write-Host "[INFO] Please select 'Desktop development with C++' and click Install." -ForegroundColor Cyan
            Write-Host ""
            
            $installProcess = Start-Process -FilePath $vsInstallerPath -ArgumentList "--add", "Microsoft.VisualStudio.Workload.VCTools", "--includeRecommended", "--passive" -Wait -PassThru
            
            Remove-Item $vsInstallerPath -Force -ErrorAction SilentlyContinue
            
            Write-Host ""
            Write-Host "[INFO] Installation completed. Please restart this script." -ForegroundColor Yellow
            Read-Host "Press Enter to exit"
            exit 0
        }
    } catch {
        Write-Host "[WARN] Could not download VS Build Tools installer: $_" -ForegroundColor Yellow
        Write-Host "[INFO] Please install manually from:" -ForegroundColor Cyan
        Write-Host "       https://visualstudio.microsoft.com/visual-cpp-build-tools/" -ForegroundColor White
        Write-Host "[INFO] Continuing anyway - will try pre-built packages..." -ForegroundColor Yellow
    }
}

# ========================================
# Check/Install Rust
# ========================================
Write-Host ""
Write-Host "[INFO] Checking Rust installation..." -ForegroundColor Yellow

$rustInstalled = Get-Command rustc -ErrorAction SilentlyContinue
if (-not $rustInstalled) {
    Write-Host "[WARN] Rust not found. Attempting to install..." -ForegroundColor Yellow
    Write-Host ""
    
    try {
        # Download rustup-init.exe
        $rustupUrl = "https://win.rustup.rs/x86_64"
        $rustupPath = "$env:TEMP\rustup-init.exe"
        
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri $rustupUrl -OutFile $rustupPath -UseBasicParsing
        
        if (Test-Path $rustupPath) {
            Write-Host "[INFO] Installing Rust (this may take a few minutes)..." -ForegroundColor Yellow
            & $rustupPath -y --default-toolchain stable
            Remove-Item $rustupPath -Force -ErrorAction SilentlyContinue
            
            # Add Rust to current PATH
            $env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
            
            # Verify installation
            $rustInstalled = Get-Command rustc -ErrorAction SilentlyContinue
            if ($rustInstalled) {
                $rustVersion = rustc --version
                Write-Host "[OK] Rust installed successfully: $rustVersion" -ForegroundColor Green
            } else {
                Write-Host "[WARN] Rust installed but not in PATH." -ForegroundColor Yellow
                Write-Host "[INFO] Please restart this script to load Rust." -ForegroundColor Yellow
                Read-Host "Press Enter to exit"
                exit 0
            }
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
