#!/usr/bin/env powershell

$ServerInfo = @{
    Host = "192.168.123.99"
    User = "admin"
    Path = "/vol3/1000/private/code/fundval/"
    KeyFile = "C:\Users\Ash\pc"
}

$SshArgs = @("-i", $ServerInfo.KeyFile)

Write-Host "上传前端代码到服务器..." -ForegroundColor Cyan
scp @SshArgs "frontend/src/pages/AISimulation.jsx" "$($ServerInfo.User)@$($ServerInfo.Host):$($ServerInfo.Path)frontend/src/pages/"

Write-Host "复制前端代码到容器内..." -ForegroundColor Cyan
ssh @SshArgs "$($ServerInfo.User)@$($ServerInfo.Host)" "cd $($ServerInfo.Path) && docker compose cp frontend/src/pages/AISimulation.jsx fundval:/app/frontend/src/pages/"

Write-Host "重新构建前端..." -ForegroundColor Cyan
ssh @SshArgs "$($ServerInfo.User)@$($ServerInfo.Host)" "cd $($ServerInfo.Path) && docker compose exec fundval npm run build"

Write-Host "重启容器..." -ForegroundColor Cyan
ssh @SshArgs "$($ServerInfo.User)@$($ServerInfo.Host)" "cd $($ServerInfo.Path) && docker compose restart fundval"

Write-Host "完成!" -ForegroundColor Green