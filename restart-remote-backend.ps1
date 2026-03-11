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

Write-Host "=== Restart Backend Service ===" -ForegroundColor Green
Write-Host "Target Server: $($ServerInfo.Host)"
Write-Host ""

try {
    $SshArgs = @()
    if ($ServerInfo.KeyFile) {
        $SshArgs += "-i", $ServerInfo.KeyFile
    }
    
    # Restart backend container
    Write-Host "Restarting backend container..." -ForegroundColor Cyan
    ssh @SshArgs "$($ServerInfo.User)@$($ServerInfo.Host)" "cd $($ServerInfo.Path) && docker compose restart fundval"
    Write-Host "Backend container restarted!" -ForegroundColor Green
    
    # Wait for service to be ready
    Write-Host "Waiting for service to be ready..." -ForegroundColor Gray
    Start-Sleep -Seconds 10
    
    # Test API
    Write-Host "Testing AI Simulation API..." -ForegroundColor Gray
    ssh @SshArgs "$($ServerInfo.User)@$($ServerInfo.Host)" "cd $($ServerInfo.Path) && docker compose exec fundval python -c 'import requests; r = requests.get(\"http://localhost:8000/api/ai-simulation/accounts\", timeout=10); print(f\"Status Code: {r.status_code}\"); print(f\"Response: {r.text[:200] if r.status_code == 200 else r.text}\")'"
    
    Write-Host "Fix completed!" -ForegroundColor Green
    Write-Host "Please check: http://$($ServerInfo.Host):21345" -ForegroundColor Cyan
} catch {
    Write-Host "Fix failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
