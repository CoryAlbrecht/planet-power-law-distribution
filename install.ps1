# planet-power-law-distribution installer
# Usage: powershell -ExecutionPolicy Bypass -Command "Invoke-WebRequest -Uri '<link-to-script-on-github>' -OutFile 'install.ps1'; .\install.ps1 [repo-url] [install-dir]"
# Or: .\install.ps1 [repo-url] [install-dir]

param(
    [string]$RepoUrl = "https://github.com/cory/planet-power-law-distribution",
    [string]$InstallDir = "$env:USERPROFILE\planet-power-law-distribution"
)

$ErrorActionPreference = "Stop"

Write-Host "=== planet-power-law-distribution installer ===" -ForegroundColor Cyan
Write-Host "Repo: $RepoUrl"
Write-Host "Install dir: $InstallDir"
Write-Host ""

# Check for git
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "Error: git is required but not installed." -ForegroundColor Red
    Write-Host "Please install git and try again." -ForegroundColor Yellow
    exit 1
}

# Check for python
$pythonCmd = $null
foreach ($cmd in @("python", "python3", "py")) {
    if (Get-Command $cmd -ErrorAction SilentlyContinue) {
        $pythonCmd = $cmd
        break
    }
}

if (-not $pythonCmd) {
    Write-Host "Error: Python 3 is required but not installed." -ForegroundColor Red
    Write-Host "Please install Python 3 and try again." -ForegroundColor Yellow
    exit 1
}

# Check python version
$version = & $pythonCmd -c "import sys; print('.'.join(map(str, sys.version_info[:2])))"
Write-Host "Found Python $version"

# Check for pip
$pipCmd = $null
foreach ($cmd in @("pip", "pip3", "py")) {
    $result = & $cmd --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        $pipCmd = $cmd
        break
    }
}

if (-not $pipCmd) {
    # Try python -m pip
    $result = & $pythonCmd -m pip --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        $pipCmd = "$pythonCmd -m pip"
    }
}

if (-not $pipCmd) {
    Write-Host "Error: pip is required but not installed." -ForegroundColor Red
    Write-Host "Please install pip and try again." -ForegroundColor Yellow
    exit 1
}

# Clone or update repository
if (Test-Path "$InstallDir\.git") {
    Write-Host "Updating existing installation..."
    Set-Location $InstallDir
    git pull
} else {
    Write-Host "Cloning repository..."
    git clone $RepoUrl $InstallDir
    Set-Location $InstallDir
}

# Create virtual environment
if (Test-Path ".venv") {
    Write-Host "Updating virtual environment..."
    Remove-Item -Recurse -Force ".venv"
}

Write-Host "Creating virtual environment..."
& $pythonCmd -m venv .venv

# Determine activate script
$activateScript = if ($IsWindows -or -not $env:OSTYPE.StartsWith("linux")) {
    ".venv\Scripts\Activate.ps1"
} else {
    ".venv/bin/activate"
}

# Activate venv and install
Write-Host "Activating virtual environment..."
& . $activateScript

Write-Host "Installing dependencies..."
pip install --upgrade pip
pip install -e .

Write-Host ""
Write-Host "=== Installation complete! ===" -ForegroundColor Green
Write-Host "To activate the environment, run: .venv\Scripts\Activate.ps1"
Write-Host "To run the tool, use: planet-power"
Write-Host ""
Write-Host "Or activate and run in one command:"
Write-Host "  .venv\Scripts\Activate.ps1; planet-power --help"