@echo off
REM ============================================================================
REM Auto Claude - Web Frontend Build and Start Script (Windows)
REM ============================================================================
REM
REM PURPOSE:
REM This script automates the complete build and startup process for the
REM web-frontend service (React/Vite) on Windows systems.
REM
REM WHAT IT DOES:
REM 1. Verifies Node.js and npm are installed
REM 2. Installs npm dependencies from package.json
REM 3. Checks for .env file (copies from .env.example if missing)
REM 4. Checks if port 3000 is available
REM 5. Starts Vite development server on port 3000
REM
REM USAGE:
REM   build-and-start.bat
REM
REM REQUIREMENTS:
REM   Node.js >= 24.0.0
REM   npm >= 10.0.0
REM
REM ============================================================================

setlocal enabledelayedexpansion

REM Change to script directory
cd /d "%~dp0"

echo.
echo ================================================================
echo          Auto Claude - Web Frontend Build ^& Start
echo ================================================================
echo.

REM ============================================================================
REM 1. CHECK FOR NODE.JS AND NPM
REM ============================================================================

echo [*] Checking for Node.js and npm...
echo.

REM Check for Node.js
where node >nul 2>&1
if !errorlevel! neq 0 (
    echo [ERROR] Node.js is not installed
    echo.
    echo Please install Node.js ^(^>= 24.0.0^) from:
    echo   * https://nodejs.org/
    echo   * Or use winget: winget install OpenJS.NodeJS
    echo.
    exit /b 1
)

REM Check for npm
where npm >nul 2>&1
if !errorlevel! neq 0 (
    echo [ERROR] npm is not installed
    echo.
    echo npm should come with Node.js. Please reinstall Node.js from:
    echo   * https://nodejs.org/
    echo.
    exit /b 1
)

REM Get versions
for /f "tokens=*" %%a in ('node --version 2^>^&1') do set "NODE_VERSION=%%a"
for /f "tokens=*" %%a in ('npm --version 2^>^&1') do set "NPM_VERSION=%%a"

echo [OK] Node.js %NODE_VERSION% found
echo [OK] npm %NPM_VERSION% found
echo.

REM ============================================================================
REM 2. INSTALL DEPENDENCIES
REM ============================================================================

echo [*] Installing npm dependencies...
echo.

if not exist "package.json" (
    echo [ERROR] package.json not found
    echo Make sure you're running this script from the web-frontend directory.
    exit /b 1
)

REM Install dependencies
echo Installing packages from package.json...
call npm install
if !errorlevel! neq 0 (
    echo.
    echo [ERROR] Failed to install dependencies
    exit /b 1
)

echo.
echo [OK] Dependencies installed successfully
echo.

REM ============================================================================
REM 3. ENVIRONMENT CONFIGURATION
REM ============================================================================

echo [*] Checking environment configuration...
echo.

if not exist ".env" (
    if exist ".env.example" (
        echo [WARNING] .env file not found, creating from .env.example...
        copy /y ".env.example" ".env" >nul
        echo [OK] Created .env file
        echo.
        echo IMPORTANT: Please review and configure your .env file:
        echo   * Edit: apps\web-frontend\.env
        echo   * VITE_API_URL: Backend API URL ^(default: http://localhost:8000^)
        echo   * VITE_WS_URL: Backend WebSocket URL ^(default: ws://localhost:8000/ws^)
        echo.
    ) else (
        echo [ERROR] Neither .env nor .env.example found
        echo.
        echo Please create a .env file with required variables:
        echo   VITE_API_URL=http://localhost:8000
        echo   VITE_WS_URL=ws://localhost:8000/ws
        echo.
        exit /b 1
    )
) else (
    echo [OK] .env file found
)
echo.

REM ============================================================================
REM 4. CHECK PORT AVAILABILITY
REM ============================================================================

echo [*] Checking if port 3000 is available...
echo.

REM Check if port 3000 is already in use
netstat -ano | findstr ":3000" | findstr "LISTENING" >nul 2>&1
if !errorlevel! equ 0 (
    echo [WARNING] Port 3000 is already in use
    echo.
    echo Another process is using port 3000. Options:
    echo   1. Stop the other process
    echo   2. Vite will automatically try port 3001, 3002, etc.
    echo.
) else (
    echo [OK] Port 3000 is available
    echo.
)

REM ============================================================================
REM 5. START DEVELOPMENT SERVER
REM ============================================================================

echo.
echo ================================================================
echo                   STARTING WEB FRONTEND
echo ================================================================
echo.
echo [*] Starting Vite development server...
echo.
echo Development server will be available at:
echo   * Local:   http://localhost:3000
echo.
echo Press Ctrl+C to stop the server
echo ================================================================
echo.

REM Start the Vite dev server
call npm run dev

REM If npm exits with error
if !errorlevel! neq 0 (
    echo.
    echo [ERROR] Vite exited with error code !errorlevel!
    exit /b !errorlevel!
)
