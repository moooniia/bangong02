$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    $arguments = '-NoProfile -ExecutionPolicy Bypass -File "{0}"' -f $PSCommandPath
    Start-Process powershell.exe -Verb RunAs -ArgumentList $arguments
    exit
}

$cert = Join-Path $root 'winui_app\InvoiceToolboxRoot.cer'
$msix = Join-Path $root 'winui_app\AppPackages\InvoiceToolbox.WinUI_1.0.0.0_x64_Test\InvoiceToolbox.WinUI_1.0.0.0_x64.msix'

try {
    if (-not (Test-Path $cert)) { throw "开发证书不存在：$cert" }
    if (-not (Test-Path $msix)) { throw "MSIX 安装包不存在：$msix" }
    & certutil.exe -addstore -f Root $cert | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "开发证书导入失败，错误码：$LASTEXITCODE" }
    Add-AppxPackage -Path $msix -ForceApplicationShutdown
    Write-Host '发票工具箱安装完成。' -ForegroundColor Green
} catch {
    Write-Host "安装失败：$($_.Exception.Message)" -ForegroundColor Red
}
Read-Host '按回车关闭'
