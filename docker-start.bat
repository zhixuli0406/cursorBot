@echo off
chcp 65001 >nul 2>&1
title CursorBot Docker

echo ========================================
echo       CursorBot Docker Launcher
echo ========================================
echo.

:: Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running.
    echo Please start Docker Desktop and try again.
    echo.
    pause
    exit /b 1
)
echo [OK] Docker is running

:: Check if .env file exists
if not exist ".env" (
    echo.
    echo [WARN] .env file not found
    if exist "env.example" (
        echo [INFO] Copying env.example to .env
        copy env.example .env >nul
        echo [INFO] Please edit .env file with your settings
        echo.
        echo Required settings:
        echo   - TELEGRAM_BOT_TOKEN
        echo   - TELEGRAM_ALLOWED_USERS  
        echo   - CURSOR_API_KEY
        echo.
        notepad .env
        pause
    ) else (
        echo [ERROR] env.example not found
        pause
        exit /b 1
    )
)
echo [OK] .env file exists
echo.

:: Parse command
if "%1"=="" goto start
if "%1"=="start" goto start
if "%1"=="up" goto start
if "%1"=="stop" goto stop
if "%1"=="down" goto stop
if "%1"=="restart" goto restart
if "%1"=="logs" goto logs
if "%1"=="build" goto build
if "%1"=="shell" goto shell
if "%1"=="status" goto status
goto help

:start
echo [INFO] Starting CursorBot...
docker compose up -d --build
echo.
echo [OK] CursorBot started!
echo.
echo Useful commands:
echo   View logs:    docker compose logs -f
echo   Stop:         docker compose down
echo   Restart:      docker compose restart
echo.
goto end

:stop
echo [INFO] Stopping CursorBot...
docker compose down
echo [OK] CursorBot stopped
goto end

:restart
echo [INFO] Restarting CursorBot...
docker compose restart
echo [OK] CursorBot restarted
goto end

:logs
echo [INFO] Showing logs (Ctrl+C to exit)...
docker compose logs -f
goto end

:build
echo [INFO] Building Docker image...
docker compose build --no-cache
echo [OK] Build completed
goto end

:shell
echo [INFO] Opening shell in container...
docker exec -it cursorbot /bin/bash
goto end

:status
echo [INFO] Container status:
docker ps -a --filter "name=cursorbot"
goto end

:help
echo.
echo Usage: docker-start.bat [command]
echo.
echo Commands:
echo   start   - Start CursorBot (default)
echo   stop    - Stop CursorBot
echo   restart - Restart CursorBot
echo   logs    - View logs
echo   build   - Rebuild Docker image
echo   shell   - Open shell in container
echo   status  - Show container status
echo.
goto end

:end
pause
