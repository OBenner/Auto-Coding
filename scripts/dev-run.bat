@echo off
setlocal EnableDelayedExpansion

:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:: Auto Claude - Development Server Start Script (Windows)
:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
::
:: PURPOSE:
:: Starts the development environment (Electron frontend in dev mode).
::
:: USAGE:
::   scripts\dev-run.bat           - Start dev server
::   scripts\dev-run.bat --mcp     - Start with MCP debugging enabled
::   scripts\dev-run.bat --help    - Show help message
::
:: PREREQUISITES:
::   - Run scripts\dev-setup.bat first
::   - Configure apps\backend\.env with API keys
::
:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

:: Get script directory and project root
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."

:: Parse arguments
set "MODE=dev"
set "SHOW_HELP=0"

:parse_args
if "%~1"=="" goto :done_parsing
if /i "%~1"=="--mcp" (
    set "MODE=dev:mcp"
    shift
    goto :parse_args
)
if /i "%~1"=="-m" (
    set "MODE=dev:mcp"
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
    echo Auto Claude - Development Server
    echo.
    echo USAGE:
    echo   scripts\dev-run.bat           Start dev server
    echo   scripts\dev-run.bat --mcp     Start with MCP debugging enabled
    echo   scripts\dev-run.bat --help    Show this help message
    echo.
    echo OPTIONS:
    echo   --mcp, -m    Enable MCP debugging ^(uses npm run dev:mcp^)
    echo   --help, -h   Show this help message
    echo.
    exit /b 0
)

echo.
echo ========================================================================
echo            Auto Claude - Starting Development Server
echo ========================================================================
echo.

:: Quick prerequisite check
echo [*] Checking prerequisites...
where node >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [-] Node.js not found. Run scripts\dev-setup.bat first.
    exit /b 1
)

cd /d "%PROJECT_ROOT%"

:: Check if node_modules exists
if not exist "node_modules" (
    echo [-] Dependencies not installed. Run scripts\dev-setup.bat first.
    exit /b 1
)

if not exist "apps\frontend\node_modules" (
    echo [-] Frontend dependencies not installed. Run scripts\dev-setup.bat first.
    exit /b 1
)

echo [+] Prerequisites OK
echo.

:: Display mode info
if "%MODE%"=="dev:mcp" (
    echo [*] Starting dev server with MCP debugging...
    echo     Remote debugging port: 9222
) else (
    echo [*] Starting dev server...
)
echo.
echo ========================================================================
echo TIP: Press Ctrl+C to stop the server
echo ========================================================================
echo.

:: Start the dev server
call npm run %MODE%

:: Handle exit
if %ERRORLEVEL% equ 0 (
    echo.
    echo [+] Dev server stopped.
    exit /b 0
) else (
    echo.
    echo [-] Dev server exited with error code %ERRORLEVEL%
    exit /b %ERRORLEVEL%
)
