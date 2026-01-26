@echo off
setlocal EnableDelayedExpansion

:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:: Auto Claude - Development Environment Verification Script (Windows)
:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
::
:: PURPOSE:
:: Verifies that the development environment is correctly configured and
:: all dependencies are installed. Runs basic smoke tests.
::
:: USAGE:
::   scripts\dev-check.bat           - Run all checks
::   scripts\dev-check.bat --quick   - Skip smoke tests (faster)
::   scripts\dev-check.bat --help    - Show help message
::
:: EXIT CODES:
::   0 - All checks passed
::   1 - One or more checks failed
::
:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

:: Get script directory and project root
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."

:: Parse arguments
set "QUICK_MODE=0"
set "SHOW_HELP=0"

:parse_args
if "%~1"=="" goto :done_parsing
if /i "%~1"=="--quick" (
    set "QUICK_MODE=1"
    shift
    goto :parse_args
)
if /i "%~1"=="-q" (
    set "QUICK_MODE=1"
    shift
    goto :parse_args
)
if /i "%~1"=="--help" (
    set "SHOW_HELP=1"
    shift
    goto :parse_args
)
if /i "%~1"=="-h" (
    set "SHOW_HELP=1"
    shift
    goto :parse_args
)
shift
goto :parse_args
:done_parsing

:: Show help if requested
if %SHOW_HELP% equ 1 (
    echo.
    echo Auto Claude - Development Environment Check
    echo.
    echo USAGE:
    echo   scripts\dev-check.bat           Run all checks
    echo   scripts\dev-check.bat --quick   Skip smoke tests ^(faster^)
    echo   scripts\dev-check.bat --help    Show this help message
    echo.
    echo OPTIONS:
    echo   --quick, -q  Skip lint and type checks ^(faster verification^)
    echo   --help, -h   Show this help message
    echo.
    echo EXIT CODES:
    echo   0 - All checks passed
    echo   1 - One or more checks failed
    echo.
    exit /b 0
)

:: Track results
set ERRORS=0
set WARNINGS=0

echo.
echo ========================================================================
echo            Auto Claude - Development Environment Check
echo ========================================================================
echo.

:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:: Runtime Prerequisites
:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

echo ========================================================================
echo RUNTIME PREREQUISITES
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
        echo [+] Node.js v!NODE_VERSION!
    ) else (
        echo [-] Node.js v!NODE_VERSION! ^(v24+ required^)
        set /a ERRORS+=1
    )
) else (
    echo [-] Node.js not found
    set /a ERRORS+=1
)

:: Check npm
echo [*] Checking npm...
where npm >nul 2>&1
if %ERRORLEVEL% equ 0 (
    for /f "tokens=1" %%v in ('npm --version') do set "NPM_VERSION=%%v"
    for /f "tokens=1 delims=." %%a in ("!NPM_VERSION!") do set "NPM_MAJOR=%%a"
    if !NPM_MAJOR! geq 10 (
        echo [+] npm v!NPM_VERSION!
    ) else (
        echo [-] npm v!NPM_VERSION! ^(v10+ required^)
        set /a ERRORS+=1
    )
) else (
    echo [-] npm not found
    set /a ERRORS+=1
)

:: Check Python
echo [*] Checking Python...
set "PYTHON_CMD="
set "PYTHON_FOUND=0"

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
    echo [+] Python !PY_VERSION!
) else (
    echo [-] Python 3.12+ not found
    set /a ERRORS+=1
)

:: Check uv (optional)
echo [*] Checking uv (Python package manager)...
where uv >nul 2>&1
if %ERRORLEVEL% equ 0 (
    for /f "tokens=2" %%v in ('uv --version 2^>^&1') do set "UV_VERSION=%%v"
    echo [+] uv v!UV_VERSION!
) else (
    echo [~] uv not found ^(optional, but recommended for backend development^)
    set /a WARNINGS+=1
)

echo.

:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:: Dependencies Check
:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

echo ========================================================================
echo INSTALLED DEPENDENCIES
echo ========================================================================
echo.

cd /d "%PROJECT_ROOT%"

:: Check root node_modules
echo [*] Checking root dependencies...
if exist "node_modules" (
    echo [+] Root node_modules present
) else (
    echo [-] Root node_modules missing - run scripts\dev-setup.bat
    set /a ERRORS+=1
)

:: Check frontend node_modules
echo [*] Checking frontend dependencies...
if exist "apps\frontend\node_modules" (
    echo [+] Frontend node_modules present
) else (
    echo [-] Frontend node_modules missing - run scripts\dev-setup.bat
    set /a ERRORS+=1
)

:: Check backend venv (optional)
echo [*] Checking backend virtual environment...
if exist "apps\backend\.venv" (
    echo [+] Backend .venv present
) else (
    echo [~] Backend .venv not found ^(needed for Python development^)
    set /a WARNINGS+=1
)

:: Check .env file
echo [*] Checking backend .env configuration...
if exist "apps\backend\.env" (
    echo [+] Backend .env file present
) else (
    echo [~] Backend .env missing - copy from apps\backend\.env.example
    set /a WARNINGS+=1
)

echo.

:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:: Smoke Tests (unless --quick)
:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

if %QUICK_MODE% equ 0 (
    echo ========================================================================
    echo SMOKE TESTS
    echo ========================================================================
    echo.

    :: Run lint check
    echo [*] Running lint check...
    cd /d "%PROJECT_ROOT%\apps\frontend"
    call npm run lint >nul 2>&1
    if !ERRORLEVEL! equ 0 (
        echo [+] Lint check passed
    ) else (
        echo [-] Lint check failed - run: cd apps\frontend ^&^& npm run lint
        set /a ERRORS+=1
    )

    :: Run type check
    echo [*] Running TypeScript type check...
    call npm run typecheck >nul 2>&1
    if !ERRORLEVEL! equ 0 (
        echo [+] TypeScript type check passed
    ) else (
        echo [-] TypeScript type check failed - run: cd apps\frontend ^&^& npm run typecheck
        set /a ERRORS+=1
    )

    cd /d "%PROJECT_ROOT%"
    echo.
) else (
    echo ========================================================================
    echo SMOKE TESTS ^(skipped - use without --quick to run^)
    echo ========================================================================
    echo.
)

:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:: Summary
:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

echo ========================================================================
echo SUMMARY
echo ========================================================================
echo.

if %ERRORS% equ 0 (
    if %WARNINGS% equ 0 (
        echo [+] All checks passed! Environment is ready.
    ) else (
        echo [+] All required checks passed!
        echo [~] %WARNINGS% warning^(s^) - see optional items above
    )
    echo.
    echo   Quick commands:
    echo     Start dev server:    scripts\dev-run.bat
    echo     Start with MCP:      scripts\dev-run.bat --mcp
    echo.
    exit /b 0
) else (
    echo [-] %ERRORS% check^(s^) failed, %WARNINGS% warning^(s^)
    echo.
    echo Please fix the issues above. Common fixes:
    echo   - Run scripts\dev-setup.bat to install dependencies
    echo   - Copy apps\backend\.env.example to apps\backend\.env
    echo.
    exit /b 1
)
