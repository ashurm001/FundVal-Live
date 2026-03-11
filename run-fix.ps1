#!/usr/bin/env powershell

$ServerInfo = @{
    Host = "192.168.123.99"
    User = "admin"
    Path = "/vol3/1000/private/code/fundval/"
    KeyFile = "C:\Users\Ash\pc"
}

$SshArgs = @("-i", $ServerInfo.KeyFile)

Write-Host "上传修复脚本到服务器..." -ForegroundColor Cyan
scp @SshArgs "backend\fix_database.py" "$($ServerInfo.User)@$($ServerInfo.Host):$($ServerInfo.Path)backend/"

Write-Host "复制修复脚本到容器内..." -ForegroundColor Cyan
ssh @SshArgs "$($ServerInfo.User)@$($ServerInfo.Host)" "cd $($ServerInfo.Path) && docker compose cp backend/fix_database.py fundval:/app/backend/"

Write-Host "执行修复脚本..." -ForegroundColor Cyan
ssh @SshArgs "$($ServerInfo.User)@$($ServerInfo.Host)" "cd $($ServerInfo.Path) && docker compose exec fundval python fix_database.py"

Write-Host "完成!" -ForegroundColor Green
