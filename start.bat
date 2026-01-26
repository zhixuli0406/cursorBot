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
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install dependencies
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
