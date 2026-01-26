@echo off
echo ========================================
echo         CursorBot Debug Script
echo ========================================
echo.

echo [Step 1] Current directory:
cd
echo.

echo [Step 2] Changing to script directory...
cd /d "%~dp0"
echo Now in: %CD%
echo.

echo [Step 3] Checking Python...
python --version
if %errorlevel% neq 0 (
    echo FAILED: Python not found
    goto :end
)
echo.

echo [Step 4] Checking venv folder...
if exist "venv" (
    echo OK: venv folder exists
) else (
    echo NOT FOUND: venv folder
)
echo.

echo [Step 5] Checking activate.bat...
if exist "venv\Scripts\activate.bat" (
    echo OK: activate.bat exists
) else (
    echo NOT FOUND: venv\Scripts\activate.bat
)
echo.

echo [Step 6] Activating venv...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo FAILED: Could not activate venv
    goto :end
)
echo OK: venv activated
echo.

echo [Step 7] Checking pip...
pip --version
echo.

echo [Step 8] Checking .env file...
if exist ".env" (
    echo OK: .env file exists
) else (
    echo NOT FOUND: .env file
)
echo.

echo [Step 9] Checking requirements.txt...
if exist "requirements.txt" (
    echo OK: requirements.txt exists
) else (
    echo NOT FOUND: requirements.txt
    goto :end
)
echo.

echo [Step 10] Checking if python-telegram-bot is installed...
pip show python-telegram-bot
if %errorlevel% neq 0 (
    echo NOT INSTALLED: python-telegram-bot
    echo.
    echo This is normal if first time running.
) else (
    echo OK: python-telegram-bot is installed
)
echo.

echo [Step 11] Checking Rust...
where rustc
if %errorlevel% neq 0 (
    echo NOT FOUND: Rust (rustc)
) else (
    rustc --version
)
echo.

echo ========================================
echo         Debug completed
echo ========================================

:end
echo.
pause
