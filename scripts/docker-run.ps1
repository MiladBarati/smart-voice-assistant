# PowerShell script to run Docker container with omnilingual-asr
# Run this in Windows PowerShell

param(
    [string]$Image = "pjsua-bot-omnilingual:latest",
    [string]$Command = "",
    [switch]$Interactive,
    [switch]$Shell,
    [switch]$TestASR
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Running Docker Container" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is running
$dockerRunning = docker info 2>&1 | Select-String "Server Version"
if (-not $dockerRunning) {
    Write-Host "[ERROR] Docker is not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}

# Check if image exists
$imageExists = docker images -q $Image
if (-not $imageExists) {
    Write-Host "[ERROR] Image '$Image' not found. Build it first with:" -ForegroundColor Red
    Write-Host "  .\docker-build.ps1" -ForegroundColor Yellow
    exit 1
}

Write-Host "[INFO] Running image: $Image" -ForegroundColor Green
Write-Host ""

# Load environment variables from .env file if it exists
$envVars = @{}
if (Test-Path "${PWD}/.env") {
    Write-Host "[INFO] Loading environment variables from .env file..." -ForegroundColor Cyan
    Get-Content "${PWD}/.env" | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+?)\s*=\s*(.+?)\s*$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim('"', "'")
            $envVars[$key] = $value
        }
    }
}

# Base docker run arguments
$runArgs = @(
    "run",
    "--rm",
    "-v", "${PWD}/recordings:/app/recordings",
    "-v", "${PWD}/assets:/app/assets",
    "-v", "${PWD}/examples:/app/examples",
    "-v", "${PWD}/.cache:/app/.cache",
    "-v", "${PWD}/test_omnilingual.py:/app/test_omnilingual.py:ro",
    "-v", "${PWD}/test_asr_migration.py:/app/test_asr_migration.py:ro",
    "-v", "${PWD}/scripts/debug_cache.py:/app/debug_cache.py:ro",
    "-v", "${PWD}/src:/app/src:ro",
    "-e", "HOME=/home/voicebot",
    "-e", "XDG_CACHE_HOME=/app/.cache",
    "-e", "HF_HOME=/app/.cache/huggingface",
    "-e", "HUGGINGFACE_HUB_CACHE=/app/.cache/huggingface/hub",
    "-e", "TRANSFORMERS_CACHE=/app/.cache/huggingface/transformers",
    "-e", "TORCH_HOME=/app/.cache/torch",
    "-e", "FAIRSEQ2_CACHE_DIR=/app/.cache/fairseq2",
    "-e", "PYTHONPATH=/app:/app/src"
)

# Mount .env file if it exists
if (Test-Path "${PWD}/.env") {
    $runArgs += "-v", "${PWD}/.env:/app/.env:ro"
}

# Pass Elasticsearch environment variables from .env file
$esVars = @("ES_HOST", "ES_PORT", "ES_USERNAME", "ES_PASSWORD", "ES_USE_SSL", "ES_VERIFY_CERTS", "ELASTIC_INDEX_PREFIX")
foreach ($var in $esVars) {
    if ($envVars.ContainsKey($var)) {
        $runArgs += "-e", "${var}=$($envVars[$var])"
    }
}

# Determine what to run
if ($Shell) {
    # Interactive shell with better experience
    $runArgs += "-it"
    $runArgs += "-e", "PS1=\[\e[1;32m\](omnilingual-docker)\[\e[0m\] \w\$ "
    $runArgs += $Image
    $runArgs += "/bin/bash"
    Write-Host "[INFO] Starting interactive shell..." -ForegroundColor Green
    Write-Host "[INFO] All packages are installed system-wide (no venv needed)" -ForegroundColor Cyan
    Write-Host "[INFO] Try: python3 -c 'from omnilingual_asr import ASR; print(\"Ready\")'" -ForegroundColor Cyan
}
elseif ($TestASR) {
    # Test omnilingual-asr using a test script file
    $runArgs += "-it"
    $runArgs += "-v"
    $runArgs += "${PWD}/test_omnilingual.py:/tmp/test_omnilingual.py:ro"
    $runArgs += $Image
    $runArgs += "python3"
    $runArgs += "/tmp/test_omnilingual.py"
    Write-Host "[INFO] Testing omnilingual-asr installation..." -ForegroundColor Green
}
elseif ($Interactive) {
    # Interactive mode with custom command
    $runArgs += "-it"
    $runArgs += $Image
    if ($Command) {
        $runArgs += "python3"
        $runArgs += $Command
    }
    Write-Host "[INFO] Running in interactive mode..." -ForegroundColor Green
}
elseif ($Command) {
    # Run specific command
    $runArgs += $Image
    $runArgs += "python3"
    $runArgs += $Command
    Write-Host "[INFO] Running command: $Command" -ForegroundColor Green
}
else {
    # Default: run example
    $runArgs += "-it"
    $runArgs += $Image
    $runArgs += "python3"
    $runArgs += "examples/omnilingual_asr_example.py"
    Write-Host "[INFO] Running omnilingual-asr example..." -ForegroundColor Green
}

Write-Host ""

# Execute docker run
& docker @runArgs

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "[SUCCESS] Container exited successfully" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "[ERROR] Container exited with code: $LASTEXITCODE" -ForegroundColor Red
    exit $LASTEXITCODE
}

