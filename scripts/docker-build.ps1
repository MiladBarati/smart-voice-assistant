# PowerShell script to build Docker image with omnilingual-asr
# Run this in Windows PowerShell

param(
    [string]$Tag = "pjsua-bot-omnilingual:latest",
    [switch]$NoCache,
    [switch]$Verbose
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Building Docker Image with omnilingual-asr" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is running
$dockerRunning = docker info 2>&1 | Select-String "Server Version"
if (-not $dockerRunning) {
    Write-Host "[ERROR] Docker is not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}

Write-Host "[INFO] Docker is running" -ForegroundColor Green
Write-Host "[INFO] Building image: $Tag" -ForegroundColor Green
Write-Host ""

# Enable BuildKit for cache mounts and better caching
$env:DOCKER_BUILDKIT = "1"
$env:COMPOSE_DOCKER_CLI_BUILD = "1"
Write-Host "[INFO] BuildKit enabled for improved caching" -ForegroundColor Green

# Build arguments
$buildArgs = @(
    "build",
    "-f", "Dockerfile.omnilingual",
    "-t", $Tag
)

if ($NoCache) {
    $buildArgs += "--no-cache"
    Write-Host "[INFO] Building without cache" -ForegroundColor Yellow
}

if ($Verbose) {
    $buildArgs += "--progress=plain"
}

$buildArgs += "."

Write-Host "[INFO] Build command: docker $buildArgs" -ForegroundColor Cyan
Write-Host ""
Write-Host "This will take 10-20 minutes on first build..." -ForegroundColor Yellow
Write-Host ""

# Execute build
& docker @buildArgs

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Build Successful!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Image: $Tag" -ForegroundColor Green
    Write-Host ""
    Write-Host "To run the container:" -ForegroundColor Yellow
    Write-Host "  docker run -it --rm $Tag python examples/omnilingual_asr_example.py" -ForegroundColor White
    Write-Host ""
    Write-Host "Or use docker-compose:" -ForegroundColor Yellow
    Write-Host "  docker-compose -f docker-compose.omnilingual.yml up" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "[ERROR] Build failed with exit code: $LASTEXITCODE" -ForegroundColor Red
    exit $LASTEXITCODE
}

