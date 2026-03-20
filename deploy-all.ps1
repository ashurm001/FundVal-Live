#!/usr/bin/env powershell

$ServerInfo = @{
    Host = "192.168.123.99"
    User = "admin"
    Path = "/vol3/1000/private/code/fundval/"
    KeyFile = "C:\Users\Ash\pc"
}

$SshArgs = @("-i", $ServerInfo.KeyFile)

Write-Host "上传修改后的文件到服务器..." -ForegroundColor Cyan
scp @SshArgs "frontend/src/pages/AISimulation.jsx" "$($ServerInfo.User)@$($ServerInfo.Host):$($ServerInfo.Path)frontend/src/pages/"
scp @SshArgs "backend/app/services/ai_simulation.py" "$($ServerInfo.User)@$($ServerInfo.Host):$($ServerInfo.Path)backend/app/services/"

Write-Host "重新构建并部署..." -ForegroundColor Cyan
ssh @SshArgs "$($ServerInfo.User)@$($ServerInfo.Host)" "cd $($ServerInfo.Path) && bash deploy-server.sh"

Write-Host "完成!" -ForegroundColor Green
Write-Host "访问地址: http://$($ServerInfo.Host):21345" -ForegroundColor Cyan