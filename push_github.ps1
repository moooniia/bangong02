# 推送本地 master 分支与标签到 GitHub
# 首次运行会弹出浏览器/Git 凭据窗口，请用 moooniia 账号登录授权

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "远程仓库:" -ForegroundColor Cyan
git remote -v
Write-Host ""
Write-Host "推送 master 分支..." -ForegroundColor Yellow
git push -u origin master
if ($LASTEXITCODE -ne 0) { throw "git push master 失败 (exit $LASTEXITCODE)" }

Write-Host ""
Write-Host "推送标签..." -ForegroundColor Yellow
git push --tags
if ($LASTEXITCODE -ne 0) { throw "git push --tags 失败 (exit $LASTEXITCODE)" }

Write-Host ""
Write-Host "完成! 查看: https://github.com/moooniia/bangong02" -ForegroundColor Green