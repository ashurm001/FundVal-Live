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

Write-Host "=== Test Remote AI API Script ===" -ForegroundColor Green
Write-Host "Target Server: $($ServerInfo.Host)"
Write-Host ""

# 1. Upload test script to server
Write-Host "1. Uploading test script to server..." -ForegroundColor Cyan
try {
    $SshArgs = @()
    if ($ServerInfo.KeyFile) {
        $SshArgs += "-i", $ServerInfo.KeyFile
    }
    
    # Upload test script
    scp @SshArgs "backend\test_ai_api.py" "$($ServerInfo.User)@$($ServerInfo.Host):$($ServerInfo.Path)backend/"
    Write-Host "Test script upload completed!" -ForegroundColor Green
} catch {
    Write-Host "Test script upload failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# 2. Execute test script on server
Write-Host "`n2. Executing test script on server..." -ForegroundColor Cyan
try {
    $SshArgs = @()
    if ($ServerInfo.KeyFile) {
        $SshArgs += "-i", $ServerInfo.KeyFile
    }
    
    # Copy test script to container and execute
    ssh @SshArgs "$($ServerInfo.User)@$($ServerInfo.Host)" "cd $($ServerInfo.Path) && docker compose cp backend/test_ai_api.py fundval:/app/backend/ && docker compose exec fundval python test_ai_api.py"
    Write-Host "Test script execution completed!" -ForegroundColor Green
} catch {
    Write-Host "Test script execution failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host "`nRemote API test completed!" -ForegroundColor Green
