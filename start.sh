#!/bin/bash
# CursorBot Startup Script for macOS/Linux

echo "========================================"
echo "         CursorBot Quick Start"
echo "========================================"
echo ""

# Parse command line arguments
START_POSTGRES=false
USE_DOCKER=false

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --postgres) START_POSTGRES=true ;;
        --docker) USE_DOCKER=true ;;
        --help|-h)
            echo "Usage: ./start.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --postgres    Start PostgreSQL with pgvector for RAG memory"
            echo "  --docker      Start using Docker Compose (includes PostgreSQL)"
            echo "  --help, -h    Show this help message"
            echo ""
            exit 0
            ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

# Docker mode - start everything via docker-compose
if [ "$USE_DOCKER" = true ]; then
    echo "[INFO] Starting CursorBot with Docker Compose..."
    
    if ! command -v docker &> /dev/null; then
        echo "[ERROR] Docker not found. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        echo "[ERROR] Docker Compose not found. Please install Docker Compose."
        exit 1
    fi
    
    # Use docker compose (v2) or docker-compose (v1)
    if docker compose version &> /dev/null; then
        docker compose up -d
    else
        docker-compose up -d
    fi
    
    echo ""
    echo "[OK] CursorBot started with Docker"
    echo "[INFO] View logs: docker compose logs -f cursorbot"
    echo "[INFO] Stop: docker compose down"
    exit 0
fi

# Start PostgreSQL if requested
if [ "$START_POSTGRES" = true ]; then
    echo "[INFO] Checking PostgreSQL with pgvector..."
    
    if command -v docker &> /dev/null; then
        # Check if PostgreSQL container is already running
        if docker ps | grep -q "cursorbot-postgres"; then
            echo "[OK] PostgreSQL container already running"
        else
            echo "[INFO] Starting PostgreSQL container with pgvector..."
            
            # Check if container exists but stopped
            if docker ps -a | grep -q "cursorbot-postgres"; then
                docker start cursorbot-postgres
            else
                # Start new PostgreSQL container
                docker run -d \
                    --name cursorbot-postgres \
                    -e POSTGRES_DB=cursorbot \
                    -e POSTGRES_USER=cursorbot \
                    -e POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-cursorbot_secret} \
                    -p 5432:5432 \
                    -v cursorbot_postgres_data:/var/lib/postgresql/data \
                    -v "$(pwd)/scripts/init_pgvector.sql:/docker-entrypoint-initdb.d/init.sql:ro" \
                    pgvector/pgvector:pg16
            fi
            
            # Wait for PostgreSQL to be ready
            echo "[INFO] Waiting for PostgreSQL to be ready..."
            for i in {1..30}; do
                if docker exec cursorbot-postgres pg_isready -U cursorbot -d cursorbot &> /dev/null; then
                    echo "[OK] PostgreSQL is ready"
                    break
                fi
                sleep 1
            done
        fi
        
        # Set environment variables for PostgreSQL
        export POSTGRES_ENABLED=true
        export POSTGRES_HOST=localhost
        export POSTGRES_PORT=5432
        export POSTGRES_DB=cursorbot
        export POSTGRES_USER=cursorbot
        export POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-cursorbot_secret}
        
        echo "[OK] PostgreSQL environment configured"
    else
        echo "[WARN] Docker not found. PostgreSQL will not be started."
        echo "[INFO] Install Docker to enable conversation RAG memory."
    fi
fi

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
