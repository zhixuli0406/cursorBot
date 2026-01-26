#!/bin/bash
# CursorBot Docker Quick Start Script

set -e

echo "========================================"
echo "      CursorBot Docker Launcher"
echo "========================================"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "[ERROR] Docker is not installed."
    echo "Please install Docker from: https://docs.docker.com/get-docker/"
    exit 1
fi

echo "[OK] Docker found"

# Check if Docker Compose is available
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
elif command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
else
    echo "[ERROR] Docker Compose is not available."
    echo "Please install Docker Compose."
    exit 1
fi

echo "[OK] Docker Compose found"

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo ""
    echo "[WARN] .env file not found"
    if [ -f "env.example" ]; then
        echo "[INFO] Copying env.example to .env"
        cp env.example .env
        echo "[INFO] Please edit .env file with your settings"
        echo ""
        echo "Required settings:"
        echo "  - TELEGRAM_BOT_TOKEN"
        echo "  - TELEGRAM_ALLOWED_USERS"
        echo "  - CURSOR_API_KEY"
        echo ""
        read -p "Press Enter after editing .env to continue..."
    else
        echo "[ERROR] env.example not found"
        exit 1
    fi
fi

echo "[OK] .env file exists"
echo ""

# Parse command line arguments
case "${1:-start}" in
    start|up)
        echo "[INFO] Starting CursorBot..."
        $COMPOSE_CMD up -d --build
        echo ""
        echo "[OK] CursorBot started!"
        echo ""
        echo "Useful commands:"
        echo "  View logs:    $COMPOSE_CMD logs -f"
        echo "  Stop:         $COMPOSE_CMD down"
        echo "  Restart:      $COMPOSE_CMD restart"
        ;;
    stop|down)
        echo "[INFO] Stopping CursorBot..."
        $COMPOSE_CMD down
        echo "[OK] CursorBot stopped"
        ;;
    restart)
        echo "[INFO] Restarting CursorBot..."
        $COMPOSE_CMD restart
        echo "[OK] CursorBot restarted"
        ;;
    logs)
        echo "[INFO] Showing logs (Ctrl+C to exit)..."
        $COMPOSE_CMD logs -f
        ;;
    build)
        echo "[INFO] Building Docker image..."
        $COMPOSE_CMD build --no-cache
        echo "[OK] Build completed"
        ;;
    shell)
        echo "[INFO] Opening shell in container..."
        docker exec -it cursorbot /bin/bash
        ;;
    status)
        echo "[INFO] Container status:"
        docker ps -a --filter "name=cursorbot"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|logs|build|shell|status}"
        echo ""
        echo "Commands:"
        echo "  start   - Start CursorBot (default)"
        echo "  stop    - Stop CursorBot"
        echo "  restart - Restart CursorBot"
        echo "  logs    - View logs"
        echo "  build   - Rebuild Docker image"
        echo "  shell   - Open shell in container"
        echo "  status  - Show container status"
        exit 1
        ;;
esac
