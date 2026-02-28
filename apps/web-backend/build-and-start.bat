@echo off
REM ============================================================================
REM Auto Code - Web Backend Build and Start Script (Windows)
REM ============================================================================
REM
REM PURPOSE:
REM This script automates the complete build and startup process for the
REM web-backend FastAPI service on Windows systems.
REM
REM WHAT IT DOES:
REM 1. Verifies Python 3.x is installed
REM 2. Creates/activates Python virtual environment
REM 3. Installs dependencies from requirements.txt
REM 4. Checks for .env file (copies from .env.example if missing)
REM 5. Starts uvicorn server on port 8000 with hot-reload
REM
REM USAGE:
REM   build-and-start.bat
REM
REM ============================================================================

setlocal enabledelayedexpansion

REM Change to script directory
cd /d "%~dp0"

echo.
echo ================================================================
echo           Auto Code - Web Backend Build ^& Start
echo ================================================================
echo.

REM ============================================================================
REM 1. CHECK FOR PYTHON
REM ============================================================================

echo [*] Checking for Python...
echo.

REM Try to find Python 3.12+ (prefer 3.12 for stable wheel support)
set "PYTHON_CMD="
set "PYTHON_VERSION="

REM Try py launcher first (Windows Python Launcher)
for %%v in (3.12 3.13 3.14 3) do (
    py -%%v --version >nul 2>&1
    if !errorlevel! equ 0 (
        for /f "tokens=2" %%a in ('py -%%v --version 2^>^&1') do (
            set "PYTHON_VERSION=%%a"
        )
        set "PYTHON_CMD=py -%%v"
        goto :python_found
    )
)

REM Try direct python commands
for %%c in (python3.12 python3.13 python3.14 python3 python) do (
    where %%c >nul 2>&1
    if !errorlevel! equ 0 (
        %%c --version >nul 2>&1
        if !errorlevel! equ 0 (
            for /f "tokens=2" %%a in ('%%c --version 2^>^&1') do (
                set "PYTHON_VERSION=%%a"
            )
            set "PYTHON_CMD=%%c"
            goto :python_found
        )
    )
)

REM Python not found
echo [ERROR] Python 3.x is required but not found.
echo.
echo Please install Python 3.12 or higher:
echo   winget install Python.Python.3.12
echo.
echo Or download from: https://www.python.org/downloads/
echo.
exit /b 1

:python_found
echo [OK] Found Python %PYTHON_VERSION%: %PYTHON_CMD%
echo.

REM ============================================================================
REM 2. CREATE/ACTIVATE VIRTUAL ENVIRONMENT
REM ============================================================================

echo [*] Setting up virtual environment...
echo.

set "VENV_DIR=venv"

REM Check if venv exists and is working
if exist "%VENV_DIR%" (
    "%VENV_DIR%\Scripts\python.exe" --version >nul 2>&1
    if !errorlevel! neq 0 (
        echo [WARNING] Removing corrupt virtual environment...
        rmdir /s /q "%VENV_DIR%"
    )
)

REM Create venv if it doesn't exist
if not exist "%VENV_DIR%" (
    echo Creating new virtual environment...
    %PYTHON_CMD% -m venv "%VENV_DIR%"
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to create virtual environment
        exit /b 1
    )
    echo [OK] Virtual environment created
) else (
    echo [OK] Virtual environment already exists
)

REM Activate virtual environment
call "%VENV_DIR%\Scripts\activate.bat"
if !errorlevel! neq 0 (
    echo [ERROR] Failed to activate virtual environment
    exit /b 1
)

REM ============================================================================
REM 3. INSTALL DEPENDENCIES
REM ============================================================================

echo.
echo [*] Installing dependencies...
echo.

if not exist "requirements.txt" (
    echo [ERROR] requirements.txt not found
    exit /b 1
)

REM Upgrade pip first
echo Upgrading pip...
python -m pip install --upgrade pip --quiet
if !errorlevel! neq 0 (
    echo [WARNING] Failed to upgrade pip, continuing anyway...
)

REM Install dependencies
echo Installing packages from requirements.txt...
pip install -r requirements.txt --quiet
if !errorlevel! neq 0 (
    echo [ERROR] Failed to install dependencies
    exit /b 1
)

echo [OK] Dependencies installed
echo.

REM ============================================================================
REM 4. CHECK/CREATE .ENV FILE
REM ============================================================================

echo [*] Checking environment configuration...
echo.

if not exist ".env" (
    if exist ".env.example" (
        echo [WARNING] .env file not found, creating from .env.example...
        copy /y ".env.example" ".env" >nul
        echo [OK] Created .env file
        echo.
        echo IMPORTANT: Please configure your .env file:
        echo   * Edit: apps\web-backend\.env
        echo   * Set SECRET_KEY (run: python -c "import secrets; print(secrets.token_urlsafe(32))")
        echo   * Configure CORS_ORIGINS for your frontend URL
        echo.
    ) else (
        echo [ERROR] No .env or .env.example file found
        echo.
        echo Please create a .env file with required variables:
        echo   HOST=0.0.0.0
        echo   PORT=8000
        echo   DEBUG=true
        echo   SECRET_KEY=your-secret-key-here
        echo   CORS_ORIGINS=http://localhost:3000
        echo.
        exit /b 1
    )
) else (
    echo [OK] .env file found
)

REM ============================================================================
REM 5. START UVICORN SERVER
REM ============================================================================

echo.
echo ================================================================
echo                    STARTING WEB BACKEND
echo ================================================================
echo.

REM Read PORT and HOST from .env file, default to 8000 and 0.0.0.0
set PORT=8000
set HOST=0.0.0.0
for /f "tokens=1,2 delims==" %%a in (.env) do (
    if "%%a"=="PORT" set PORT=%%b
    if "%%a"=="HOST" set HOST=%%b
)

REM Check if port is already in use
netstat -ano | findstr ":%PORT%" | findstr "LISTENING" >nul 2>&1
if !errorlevel! equ 0 (
    echo [WARNING] Port %PORT% is already in use
    echo            The server may fail to start. Stop the existing process first.
    echo.
)

echo [*] Starting FastAPI server with uvicorn...
echo.
echo Service Info:
echo   * Health: http://localhost:%PORT%/health
echo   * API Docs: http://localhost:%PORT%/docs
echo   * ReDoc: http://localhost:%PORT%/redoc
echo.
echo Press Ctrl+C to stop the server
echo ================================================================
echo.

REM Start uvicorn with hot-reload
uvicorn main:app --reload --host %HOST% --port %PORT%

REM If uvicorn exits, deactivate venv
if !errorlevel! neq 0 (
    echo.
    echo [ERROR] Uvicorn exited with error code !errorlevel!
    call "%VENV_DIR%\Scripts\deactivate.bat" 2>nul
    exit /b !errorlevel!
)

call "%VENV_DIR%\Scripts\deactivate.bat" 2>nul
