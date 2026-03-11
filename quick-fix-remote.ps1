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

Write-Host "=== Quick Fix Remote API Script ===" -ForegroundColor Green
Write-Host "Target Server: $($ServerInfo.Host)"
Write-Host ""

# 1. Upload fixed main.py to server
Write-Host "1. Uploading fixed main.py to server..." -ForegroundColor Cyan
try {
    $SshArgs = @()
    if ($ServerInfo.KeyFile) {
        $SshArgs += "-i", $ServerInfo.KeyFile
    }
    
    # Upload fixed main.py
    scp @SshArgs "backend\app\main.py" "$($ServerInfo.User)@$($ServerInfo.Host):$($ServerInfo.Path)backend/app/"
    Write-Host "Fixed main.py upload completed!" -ForegroundColor Green
} catch {
    Write-Host "Fixed main.py upload failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# 2. Restart backend service
Write-Host "`n2. Restarting backend service..." -ForegroundColor Cyan
try {
    $SshArgs = @()
    if ($ServerInfo.KeyFile) {
        $SshArgs += "-i", $ServerInfo.KeyFile
    }
    
    # Restart containers
    ssh @SshArgs "$($ServerInfo.User)@$($ServerInfo.Host)" "cd $($ServerInfo.Path) && docker compose restart fundval"
    Write-Host "Backend service restarted!" -ForegroundColor Green
    
    # Wait for service to be ready
    Write-Host "  Waiting for service to be ready..." -ForegroundColor Gray
    Start-Sleep -Seconds 5
    
    # Test API
    ssh @SshArgs "$($ServerInfo.User)@$($ServerInfo.Host)" "cd $($ServerInfo.Path) && docker compose exec fundval python -c 'import requests; r = requests.get(\"http://localhost:8000/api/ai-simulation/accounts\", timeout=5); print(f\"Status: {r.status_code}\"); print(f\"Response: {r.text[:200] if r.status_code == 200 else r.text}\")'"
    
    Write-Host "API test completed!" -ForegroundColor Green
} catch {
    Write-Host "Backend service restart failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host "`nQuick fix completed!" -ForegroundColor Green
Write-Host "Please check: http://$($ServerInfo.Host):21345" -ForegroundColor Cyan
