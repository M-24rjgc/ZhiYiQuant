# PowerShell script for building Docker image with registry fallback

Write-Host "Building frontend Docker image..." -ForegroundColor Green

# Try to build with --pull flag to force pull from official registry
$buildResult = docker build `
  --pull `
  --platform linux/amd64 `
  -t zhiyiquant-frontend:latest `
  -f Dockerfile `
  .

if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed, trying with no-cache..." -ForegroundColor Yellow
    docker build `
      --no-cache `
      --platform linux/amd64 `
      -t zhiyiquant-frontend:latest `
      -f Dockerfile `
      .
}

if ($LASTEXITCODE -eq 0) {
    Write-Host "Build successful!" -ForegroundColor Green
} else {
    Write-Host "Build failed. Please check Docker registry configuration." -ForegroundColor Red
}
