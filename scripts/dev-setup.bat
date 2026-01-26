@echo off
setlocal EnableDelayedExpansion

:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:: Auto Claude - Development Environment Setup Script (Windows)
:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
::
:: PURPOSE:
:: Sets up the complete development environment by installing all dependencies
:: and verifying prerequisites.
::
:: USAGE:
::   scripts\dev-setup.bat
::
:: PREREQUISITES:
::   - Node.js >= 24.0.0
::   - Python 3.12+
::   - npm >= 10.0.0
::
:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

:: Get script directory and project root
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."

:: Track errors
set ERRORS=0

echo.
echo ========================================================================
echo            Auto Claude - Development Setup (Windows)
echo ========================================================================
echo.

:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:: Prerequisites Check
:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

echo ========================================================================
echo CHECKING PREREQUISITES
echo ========================================================================
echo.

:: Check Node.js
echo [*] Checking Node.js...
where node >nul 2>&1
if %ERRORLEVEL% equ 0 (
    for /f "tokens=1" %%v in ('node --version') do set "NODE_VERSION=%%v"
    set "NODE_VERSION=!NODE_VERSION:v=!"
    for /f "tokens=1 delims=." %%a in ("!NODE_VERSION!") do set "NODE_MAJOR=%%a"
    if !NODE_MAJOR! geq 24 (
        echo [+] Node.js v!NODE_VERSION! ^(^>= 24.0.0 required^)
    ) else (
        echo [-] Node.js v!NODE_VERSION! found, but v24.0.0+ is required
        echo     Install Node.js 24+: https://nodejs.org/
        set /a ERRORS+=1
    )
) else (
    echo [-] Node.js not found
    echo     Install Node.js 24+: https://nodejs.org/
    echo     Or use: winget install OpenJS.NodeJS
    set /a ERRORS+=1
)

:: Check npm
echo [*] Checking npm...
where npm >nul 2>&1
if %ERRORLEVEL% equ 0 (
    for /f "tokens=1" %%v in ('npm --version') do set "NPM_VERSION=%%v"
    for /f "tokens=1 delims=." %%a in ("!NPM_VERSION!") do set "NPM_MAJOR=%%a"
    if !NPM_MAJOR! geq 10 (
        echo [+] npm v!NPM_VERSION! ^(^>= 10.0.0 required^)
    ) else (
        echo [-] npm v!NPM_VERSION! found, but v10.0.0+ is required
        set /a ERRORS+=1
    )
) else (
    echo [-] npm not found
    set /a ERRORS+=1
)

:: Check Python (try py launcher first, then python3, then python)
echo [*] Checking Python...
set "PYTHON_CMD="
set "PYTHON_FOUND=0"

:: Try py launcher with specific versions
for %%v in (3.12 3.13 3.14) do (
    if "!PYTHON_FOUND!"=="0" (
        py -%%v --version >nul 2>&1
        if !ERRORLEVEL! equ 0 (
            for /f "tokens=2" %%p in ('py -%%v --version 2^>^&1') do set "PY_VERSION=%%p"
            set "PYTHON_CMD=py -%%v"
            set "PYTHON_FOUND=1"
        )
    )
)

:: Try python3 and python
if "!PYTHON_FOUND!"=="0" (
    for %%c in (python3 python) do (
        if "!PYTHON_FOUND!"=="0" (
            where %%c >nul 2>&1
            if !ERRORLEVEL! equ 0 (
                for /f "tokens=2" %%p in ('%%c --version 2^>^&1') do set "PY_VERSION=%%p"
                for /f "tokens=1,2 delims=." %%a in ("!PY_VERSION!") do (
                    if %%a equ 3 if %%b geq 12 (
                        set "PYTHON_CMD=%%c"
                        set "PYTHON_FOUND=1"
                    )
                )
            )
        )
    )
)

if "!PYTHON_FOUND!"=="1" (
    echo [+] Python !PY_VERSION! ^(^>= 3.12 required^)
) else (
    echo [-] Python 3.12+ not found
    echo     Install Python 3.12+:
    echo       winget install Python.Python.3.12
    set /a ERRORS+=1
)

echo.

:: Exit early if prerequisites are missing
if %ERRORS% gtr 0 (
    echo ========================================================================
    echo SETUP ABORTED: %ERRORS% prerequisite^(s^) missing
    echo ========================================================================
    echo.
    echo Please install the missing prerequisites and run this script again.
    exit /b 1
)

:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:: Installation
:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

echo ========================================================================
echo INSTALLING DEPENDENCIES
echo ========================================================================
echo.

cd /d "%PROJECT_ROOT%"

:: Install all Node.js dependencies
echo [*] Installing Node.js dependencies (frontend + root)...
call npm run install:all
if %ERRORLEVEL% equ 0 (
    echo [+] Node.js dependencies installed
) else (
    echo [-] Failed to install Node.js dependencies
    set /a ERRORS+=1
)

echo.

:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:: Summary
:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

echo ========================================================================
echo SETUP COMPLETE
echo ========================================================================
echo.

if %ERRORS% equ 0 (
    echo [+] Development environment is ready!
    echo.
    echo   Next steps:
    echo     1. Configure environment: copy apps\backend\.env.example apps\backend\.env
    echo     2. Edit .env with your API keys
    echo     3. Start development: scripts\dev-run.bat
    echo     4. Verify setup: scripts\dev-check.bat
    echo.
    exit /b 0
) else (
    echo [-] Setup completed with %ERRORS% error^(s^)
    echo.
    echo Please fix the errors above and run the script again.
    exit /b 1
)
