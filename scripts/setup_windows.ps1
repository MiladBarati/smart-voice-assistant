# Windows Setup Script for PJSUA Bot (without omnilingual-asr)
# Run this in PowerShell to restore Windows environment

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "PJSUA Bot Windows Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if uv is installed
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] uv is not installed" -ForegroundColor Red
    Write-Host "Install uv first: https://github.com/astral-sh/uv" -ForegroundColor Yellow
    Write-Host "Or run: powershell -c ""irm https://astral.sh/uv/install.ps1 | iex""" -ForegroundColor Yellow
    exit 1
}

Write-Host "[INFO] uv is installed: $(uv --version)" -ForegroundColor Green
Write-Host ""

# Remove WSL virtual environment if it exists
if (Test-Path ".venv") {
    Write-Host "[WARNING] Removing existing WSL virtual environment..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force .venv
    Write-Host "[INFO] WSL .venv removed" -ForegroundColor Green
}

# Temporarily update pyproject.toml for Windows
Write-Host "[INFO] Updating pyproject.toml for Windows..." -ForegroundColor Green

$pyprojectPath = "pyproject.toml"
$content = Get-Content $pyprojectPath -Raw

# Check if already set for Windows
if ($content -match 'required-environments = \["sys_platform == ''win32''"\]') {
    Write-Host "[INFO] pyproject.toml already configured for Windows" -ForegroundColor Green
} else {
    # Backup original
    Copy-Item $pyprojectPath "$pyprojectPath.wsl.backup"
    Write-Host "[INFO] Backed up pyproject.toml to pyproject.toml.wsl.backup" -ForegroundColor Green
    
    # Update for Windows
    $content = $content -replace 'required-environments = \["sys_platform == ''linux''"\]', 'required-environments = ["sys_platform == ''win32'']'
    $content = $content -replace '"omnilingual-asr>=0\.1\.0",\s*#[^\n]*', ''
    
    Set-Content $pyprojectPath $content
    Write-Host "[INFO] Updated pyproject.toml for Windows" -ForegroundColor Green
}

Write-Host ""

# Create Windows virtual environment
Write-Host "[INFO] Creating Windows virtual environment..." -ForegroundColor Green
uv venv --python 3.11

if (-not $?) {
    Write-Host "[ERROR] Failed to create virtual environment" -ForegroundColor Red
    exit 1
}

Write-Host "[INFO] Virtual environment created at .venv" -ForegroundColor Green
Write-Host ""

# Activate and install dependencies
Write-Host "[INFO] Installing dependencies..." -ForegroundColor Green
Write-Host "[WARNING] This will NOT include omnilingual-asr (WSL only)" -ForegroundColor Yellow
Write-Host ""

# Note: uv sync will handle activation internally
uv sync

if (-not $?) {
    Write-Host "[ERROR] Failed to install dependencies" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Windows Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "To activate virtual environment:" -ForegroundColor Yellow
Write-Host "  .venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host ""
Write-Host "Or in CMD:" -ForegroundColor Yellow
Write-Host "  .venv\Scripts\activate.bat" -ForegroundColor White
Write-Host ""
Write-Host "Note: This Windows environment does NOT include omnilingual-asr" -ForegroundColor Yellow
Write-Host "For omnilingual-asr, use WSL (run: wsl)" -ForegroundColor Yellow
Write-Host ""

