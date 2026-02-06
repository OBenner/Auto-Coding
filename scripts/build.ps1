<#
.SYNOPSIS
    Auto Code - Production Build Script (PowerShell)

.DESCRIPTION
    Builds the production version of Auto Code (Electron app with bundled Python).

.PARAMETER Win
    Package for Windows (.exe)

.PARAMETER Mac
    Package for macOS (.dmg)

.PARAMETER Linux
    Package for Linux (AppImage)

.PARAMETER All
    Package for all platforms

.PARAMETER Run
    Run the production build after building

.PARAMETER Sign
    Enable code signing (disabled by default)

.EXAMPLE
    .\build.ps1           # Build only
    .\build.ps1 -Win      # Build + Windows package (no signing)
    .\build.ps1 -Win -Sign # Build + Windows package (with signing)
    .\build.ps1 -Mac      # Build + macOS package
    .\build.ps1 -All      # Build + all platforms
    .\build.ps1 -Run      # Build + run
#>

param(
    [switch]$Win,
    [switch]$Mac,
    [switch]$Linux,
    [switch]$All,
    [switch]$Run,
    [switch]$Sign,
    [switch]$Help
)

$ErrorActionPreference = "Stop"

# Get paths
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$FrontendDir = Join-Path $ProjectRoot "apps\frontend"

# Show help
if ($Help) {
    Write-Host ""
    Write-Host "Auto Code - Production Build Script" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "USAGE:"
    Write-Host "  .\build.ps1             Build only (fast, for testing)"
    Write-Host "  .\build.ps1 -Win        Build + Windows package (.exe)"
    Write-Host "  .\build.ps1 -Win -Sign  Build + Windows package (with code signing)"
    Write-Host "  .\build.ps1 -Mac        Build + macOS package (.dmg)"
    Write-Host "  .\build.ps1 -Linux      Build + Linux package (AppImage)"
    Write-Host "  .\build.ps1 -All        Build + all platforms"
    Write-Host "  .\build.ps1 -Run        Build + run production build"
    Write-Host "  .\build.ps1 -Help       Show this help"
    Write-Host ""
    Write-Host "OUTPUT:"
    Write-Host "  Build:    apps\frontend\out\"
    Write-Host "  Package:  apps\frontend\dist\"
    Write-Host ""
    exit 0
}

Write-Host ""
Write-Host "========================================================================" -ForegroundColor Blue
Write-Host "           Auto Code - Production Build" -ForegroundColor Blue
Write-Host "========================================================================" -ForegroundColor Blue
Write-Host ""

# Check prerequisites
Write-Host "[*] Checking prerequisites..." -ForegroundColor Cyan

$nodeVersion = $null
try {
    $nodeVersion = (node --version 2>$null)
} catch {}

if (-not $nodeVersion) {
    Write-Host "[-] Node.js not found. Run scripts\dev-setup.bat first." -ForegroundColor Red
    exit 1
}

$nodeMajor = [int]($nodeVersion -replace 'v(\d+)\..*', '$1')
if ($nodeMajor -lt 24) {
    Write-Host "[-] Node.js $nodeVersion found, but v24.0.0+ is required" -ForegroundColor Red
    exit 1
}

Write-Host "[+] Node.js $nodeVersion" -ForegroundColor Green

# Check dependencies
if (-not (Test-Path (Join-Path $ProjectRoot "node_modules"))) {
    Write-Host "[-] Dependencies not installed. Run scripts\dev-setup.bat first." -ForegroundColor Red
    exit 1
}

Write-Host "[+] Dependencies installed" -ForegroundColor Green
Write-Host ""

# Build
Write-Host "========================================================================" -ForegroundColor Blue
Write-Host "[*] Building production version..." -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Blue
Write-Host ""

Set-Location $FrontendDir

npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "[-] Build failed" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[+] Build completed successfully" -ForegroundColor Green
Write-Host "    Output: apps\frontend\out\"

# Package
$doPackage = $Win -or $Mac -or $Linux -or $All

if ($doPackage) {
    Write-Host ""
    Write-Host "========================================================================" -ForegroundColor Blue
    Write-Host "[*] Creating distributable packages..." -ForegroundColor Cyan
    Write-Host "========================================================================" -ForegroundColor Blue
    Write-Host ""

    # Build sign argument
    $signArg = if ($Sign) { "--sign" } else { "" }

    if ($Win -or $All) {
        Write-Host "[*] Packaging for Windows..." -ForegroundColor Cyan
        if ($Sign) {
            Write-Host "    Code signing: enabled" -ForegroundColor Yellow
        }
        npm run package:win -- $signArg
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[-] Windows packaging failed" -ForegroundColor Red
            exit 1
        }
        Write-Host "[+] Windows package created" -ForegroundColor Green
        Write-Host ""
    }

    if ($Mac -or $All) {
        Write-Host "[*] Packaging for macOS..." -ForegroundColor Cyan
        if ($Sign) {
            Write-Host "    Code signing: enabled" -ForegroundColor Yellow
        }
        npm run package:mac -- $signArg
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[-] macOS packaging failed" -ForegroundColor Red
            exit 1
        }
        Write-Host "[+] macOS package created" -ForegroundColor Green
        Write-Host ""
    }

    if ($Linux -or $All) {
        Write-Host "[*] Packaging for Linux..." -ForegroundColor Cyan
        if ($Sign) {
            Write-Host "    Code signing: enabled" -ForegroundColor Yellow
        }
        npm run package:linux -- $signArg
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[-] Linux packaging failed" -ForegroundColor Red
            exit 1
        }
        Write-Host "[+] Linux package created" -ForegroundColor Green
        Write-Host ""
    }

    Write-Host "[+] All packages created successfully" -ForegroundColor Green
    Write-Host "    Output: apps\frontend\dist\"
    Write-Host ""

    # List created files
    Write-Host "Created files:" -ForegroundColor Cyan
    $distDir = Join-Path $FrontendDir "dist"

    if (Test-Path $distDir) {
        Get-ChildItem $distDir -File | Where-Object { $_.Extension -match '\.(exe|dmg|zip|AppImage|deb)$' } | ForEach-Object {
            Write-Host "  $($_.Name)"
        }

        if (Test-Path (Join-Path $distDir "win-unpacked")) {
            Write-Host "  win-unpacked\ (portable)" -ForegroundColor Green
        }
    }
}

# Run
if ($Run) {
    Write-Host ""
    Write-Host "========================================================================" -ForegroundColor Blue
    Write-Host "[*] Starting production build..." -ForegroundColor Cyan
    Write-Host "========================================================================" -ForegroundColor Blue
    Write-Host ""

    npm run start
}

Write-Host ""
Write-Host "========================================================================" -ForegroundColor Green
Write-Host "  Build completed successfully!" -ForegroundColor Green
Write-Host "========================================================================" -ForegroundColor Green
Write-Host ""

Set-Location $ScriptDir
