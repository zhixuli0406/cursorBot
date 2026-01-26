@echo off
echo ========================================
echo         Environment Test
echo ========================================
echo.

echo [1] Current directory:
cd
echo.

echo [2] Script directory:
echo %~dp0
echo.

echo [3] Changing to script directory...
cd /d "%~dp0"
echo Now in: %CD%
echo.

echo [4] Checking Python...
where python
if %errorlevel% neq 0 (
    echo Python NOT found!
) else (
    python --version
)
echo.

echo [5] Checking if venv folder exists...
if exist "venv" (
    echo venv folder EXISTS
) else (
    echo venv folder NOT found
)
echo.

echo [6] Checking if requirements.txt exists...
if exist "requirements.txt" (
    echo requirements.txt EXISTS
) else (
    echo requirements.txt NOT found
)
echo.

echo [7] Checking Rust...
where rustc
if %errorlevel% neq 0 (
    echo Rust NOT found
) else (
    rustc --version
)
echo.

echo ========================================
echo Test completed. Press any key to exit.
echo ========================================
pause
