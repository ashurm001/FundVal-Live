#!/usr/bin/env powershell

# Set UTF-8 encoding
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# Stop on error
$ErrorActionPreference = "Stop"

# Server configuration
$ServerInfo = @{
    Host = "192.168.123.99"           # Server IP
    User = "admin"             # Server username
    Path = "/vol3/1000/private/code/fundval/"          # Deployment path on server
    KeyFile = "C:\Users\Ash\pc"  # SSH private key path (optional, comment out if using password)
}

Write-Host "=== Test Remote API with Correct Address ===" -ForegroundColor Green
Write-Host "Target Server: $($ServerInfo.Host)"
Write-Host ""

try {
    $SshArgs = @()
    if ($ServerInfo.KeyFile) {
        $SshArgs += "-i", $ServerInfo.KeyFile
    }
    
    # Upload test script
    Write-Host "Uploading test script..." -ForegroundColor Cyan
    scp @SshArgs "backend\test_api_fixed.py" "$($ServerInfo.User)@$($ServerInfo.Host):$($ServerInfo.Path)backend/"
    
    # Copy to container and execute
    Write-Host "Testing API..." -ForegroundColor Cyan
    ssh @SshArgs "$($ServerInfo.User)@$($ServerInfo.Host)" "cd $($ServerInfo.Path) && docker compose cp backend/test_api_fixed.py fundval:/app/backend/ && docker compose exec fundval python test_api_fixed.py"
    
    Write-Host "Test completed!" -ForegroundColor Green
    Write-Host "Please check: http://$($ServerInfo.Host):21345" -ForegroundColor Cyan
} catch {
    Write-Host "Test failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
