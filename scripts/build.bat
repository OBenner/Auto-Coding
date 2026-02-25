@echo off
setlocal EnableDelayedExpansion

:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:: Auto Claude - Production Build Script (Windows)
:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
::
:: PURPOSE:
:: Builds the production version of Auto Claude (Electron app with bundled Python).
::
:: USAGE:
::   scripts\build.bat              - Build only (fast, for testing)
::   scripts\build.bat --package    - Package for current platform (Windows)
::   scripts\build.bat --win        - Package for Windows
::   scripts\build.bat --mac        - Package for macOS
::   scripts\build.bat --linux      - Package for Linux
::   scripts\build.bat --all        - Package for all platforms
::   scripts\build.bat --sign       - Enable code signing (disabled by default)
::   scripts\build.bat --run        - Build and run production build
::   scripts\build.bat --help       - Show help message
::
:: PREREQUISITES:
::   - Run scripts\dev-setup.bat first
::   - Node.js >= 24.0.0
::
:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

:: Get script directory and project root
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
set "FRONTEND_DIR=%PROJECT_ROOT%\apps\frontend"

:: Default options
set "ACTION=build"
set "PLATFORM="
set "SIGN=0"
set "SHOW_HELP=0"

:: Parse arguments
:parse_args
if "%~1"=="" goto :done_parsing
if /i "%~1"=="--package" (
    set "ACTION=package"
    shift
    goto :parse_args
)
if /i "%~1"=="-p" (
    set "ACTION=package"
    shift
    goto :parse_args
)
if /i "%~1"=="--win" (
    set "ACTION=package"
    set "PLATFORM=win"
    shift
    goto :parse_args
)
if /i "%~1"=="--windows" (
    set "ACTION=package"
    set "PLATFORM=win"
    shift
    goto :parse_args
)
if /i "%~1"=="--mac" (
    set "ACTION=package"
    set "PLATFORM=mac"
    shift
    goto :parse_args
)
if /i "%~1"=="--macos" (
    set "ACTION=package"
    set "PLATFORM=mac"
    shift
    goto :parse_args
)
if /i "%~1"=="--linux" (
    set "ACTION=package"
    set "PLATFORM=linux"
    shift
    goto :parse_args
)
if /i "%~1"=="--all" (
    set "ACTION=package"
    set "PLATFORM=all"
    shift
    goto :parse_args
)
if /i "%~1"=="--run" (
    set "ACTION=run"
    shift
    goto :parse_args
)
if /i "%~1"=="-r" (
    set "ACTION=run"
    shift
    goto :parse_args
)
if /i "%~1"=="--sign" (
    set "SIGN=1"
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
    echo Auto Claude - Production Build Script
    echo.
    echo USAGE:
    echo   scripts\build.bat              Build only ^(fast, for testing^)
    echo   scripts\build.bat --package    Package for current platform ^(Windows^)
    echo   scripts\build.bat --win        Package for Windows ^(.exe^)
    echo   scripts\build.bat --mac        Package for macOS ^(.dmg^)
    echo   scripts\build.bat --linux      Package for Linux ^(AppImage^)
    echo   scripts\build.bat --all        Package for all platforms
    echo   scripts\build.bat --sign       Enable code signing
    echo   scripts\build.bat --run        Build and run production build
    echo   scripts\build.bat --help       Show this help message
    echo.
    echo OPTIONS:
    echo   --package, -p  Package for current platform
    echo   --win          Create Windows installer ^(.exe NSIS + portable^)
    echo   --mac          Create macOS installer ^(.dmg + .zip^)
    echo   --linux        Create Linux packages ^(AppImage, deb^)
    echo   --all          Create packages for all platforms
    echo   --sign         Enable code signing ^(disabled by default^)
    echo   --run, -r      Run the production build after building
    echo   --help, -h     Show this help message
    echo.
    echo OUTPUT:
    echo   Build only:    apps\frontend\out\
    echo   Package:       apps\frontend\dist\
    echo.
    echo NOTES:
    echo   - Cross-compilation may require additional tools
    echo   - macOS signing requires Apple Developer certificate
    echo   - First package run downloads Python runtime ^(~50MB per platform^)
    echo.
    exit /b 0
)

echo.
echo ========================================================================
echo            Auto Claude - Production Build
echo ========================================================================
echo.

:: Check prerequisites
echo [*] Checking prerequisites...

where node >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [-] Node.js not found. Run scripts\dev-setup.bat first.
    exit /b 1
)

for /f "tokens=1 delims=v" %%a in ('node --version') do set "NODE_VERSION=%%a"
for /f "tokens=1 delims=." %%a in ('node --version') do set "NODE_MAJOR=%%a"
set "NODE_MAJOR=%NODE_MAJOR:v=%"

if %NODE_MAJOR% lss 24 (
    echo [-] Node.js v%NODE_VERSION% found, but v24.0.0+ is required
    exit /b 1
)

echo [+] Node.js detected

:: Check if dependencies are installed
if not exist "%PROJECT_ROOT%\node_modules" (
    echo [-] Dependencies not installed. Run scripts\dev-setup.bat first.
    exit /b 1
)

echo [+] Dependencies installed
echo.

:: Build
echo ========================================================================
echo [*] Building production version...
echo ========================================================================
echo.

cd /d "%FRONTEND_DIR%"

call npm run build

if %ERRORLEVEL% neq 0 (
    echo [-] Build failed
    exit /b 1
)

echo.
echo [+] Build completed successfully
echo     Output: apps\frontend\out\

:: Package if requested
if "%ACTION%"=="package" (
    echo.
    echo ========================================================================
    echo [*] Creating distributable packages...
    echo ========================================================================
    echo.

    :: Default to Windows if no platform specified
    if "%PLATFORM%"=="" set "PLATFORM=win"

    :: Set sign argument
    set "SIGN_ARG="
    if %SIGN% equ 1 (
        set "SIGN_ARG=-- --sign"
        echo [*] Code signing enabled
    )

    :: Build for selected platform(s)
    if "%PLATFORM%"=="win" (
        echo [*] Packaging for Windows...
        call npm run package:win %SIGN_ARG%
        if %ERRORLEVEL% neq 0 goto :package_failed
    )

    if "%PLATFORM%"=="mac" (
        echo [*] Packaging for macOS...
        call npm run package:mac %SIGN_ARG%
        if %ERRORLEVEL% neq 0 goto :package_failed
    )

    if "%PLATFORM%"=="linux" (
        echo [*] Packaging for Linux...
        call npm run package:linux %SIGN_ARG%
        if %ERRORLEVEL% neq 0 goto :package_failed
    )

    if "%PLATFORM%"=="all" (
        echo [*] Packaging for Windows...
        call npm run package:win %SIGN_ARG%
        if %ERRORLEVEL% neq 0 goto :package_failed
        echo.
        echo [*] Packaging for macOS...
        call npm run package:mac %SIGN_ARG%
        if %ERRORLEVEL% neq 0 goto :package_failed
        echo.
        echo [*] Packaging for Linux...
        call npm run package:linux %SIGN_ARG%
        if %ERRORLEVEL% neq 0 goto :package_failed
    )

    echo.
    echo [+] Package^(s^) created successfully
    echo     Output: apps\frontend\dist\
    echo.

    echo Created files:
    echo.
    if exist "%FRONTEND_DIR%\dist\*.exe" (
        echo   Windows:
        for %%f in ("%FRONTEND_DIR%\dist\*.exe") do echo     %%~nxf
    )
    if exist "%FRONTEND_DIR%\dist\win-unpacked" (
        echo     win-unpacked\ ^(portable version^)
    )
    if exist "%FRONTEND_DIR%\dist\*.dmg" (
        echo   macOS:
        for %%f in ("%FRONTEND_DIR%\dist\*.dmg") do echo     %%~nxf
    )
    if exist "%FRONTEND_DIR%\dist\*.AppImage" (
        echo   Linux:
        for %%f in ("%FRONTEND_DIR%\dist\*.AppImage") do echo     %%~nxf
    )
    if exist "%FRONTEND_DIR%\dist\*.deb" (
        for %%f in ("%FRONTEND_DIR%\dist\*.deb") do echo     %%~nxf
    )

    goto :after_package

    :package_failed
    echo [-] Packaging failed
    exit /b 1

    :after_package
)

:: Run if requested
if "%ACTION%"=="run" (
    echo.
    echo ========================================================================
    echo [*] Starting production build...
    echo ========================================================================
    echo.

    call npm run start
)

echo.
echo ========================================================================
echo   Build completed successfully!
echo ========================================================================
echo.

exit /b 0
