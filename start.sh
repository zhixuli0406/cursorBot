#!/bin/bash
# CursorBot Startup Script for macOS/Linux

echo "========================================"
echo "         CursorBot Quick Start"
echo "========================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 not found. Please install Python 3.10+"
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo "[OK] $PYTHON_VERSION"

# Check/Create venv
if [ ! -d "venv" ]; then
    echo "[INFO] Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "[ERROR] Failed to create venv"
        exit 1
    fi
    echo "[OK] Virtual environment created"
fi

# Activate venv
echo "[INFO] Activating virtual environment..."
source venv/bin/activate

# Check .env
if [ ! -f ".env" ]; then
    echo "[WARN] .env file not found"
    if [ -f "env.example" ]; then
        echo "[INFO] Copying env.example to .env"
        cp env.example .env
        echo "[INFO] Please edit .env file with your settings"
        echo "       Run: nano .env"
        read -p "Press Enter after editing .env..."
    else
        echo "[ERROR] No env.example found"
        exit 1
    fi
fi

# Install dependencies
echo "[INFO] Checking dependencies..."
pip install -r requirements.txt

# Check Discord support
if grep -q "DISCORD_ENABLED=true" .env 2>/dev/null; then
    if ! pip show discord.py &> /dev/null; then
        echo "[INFO] Installing Discord support..."
        pip install discord.py
    fi
fi

# Check/Install Playwright (Browser tool)
echo "[INFO] Checking Playwright..."
if ! pip show playwright &> /dev/null; then
    echo "[INFO] Installing Playwright..."
    pip install playwright
    
    echo "[INFO] Installing Playwright browsers (this may take a while)..."
    playwright install chromium
    
    if [ $? -eq 0 ]; then
        echo "[OK] Playwright installed"
    else
        echo "[WARN] Playwright browser installation failed"
        echo "[INFO] You can manually run: playwright install"
    fi
else
    echo "[OK] Playwright already installed"
fi

# Start bot
echo ""
echo "========================================"
echo "         Starting CursorBot..."
echo "========================================"
echo ""
echo "Press Ctrl+C to stop"
echo ""

python -m src.main

echo ""
echo "[INFO] CursorBot stopped"
