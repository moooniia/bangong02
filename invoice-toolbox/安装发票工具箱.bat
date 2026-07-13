@echo off
chcp 65001 >nul
net session >nul 2>&1
if not "%errorlevel%"=="0" (
  powershell.exe -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)

set "ROOT=%~dp0"
set "CERT=%ROOT%winui_app\InvoiceToolboxRoot.cer"
set "MSIX=%ROOT%winui_app\AppPackages\InvoiceToolbox.WinUI_1.0.0.0_x64_Test\InvoiceToolbox.WinUI_1.0.0.0_x64.msix"
set "LOG=%ROOT%安装发票工具箱.log"

echo [%date% %time%] 开始安装 > "%LOG%"
certutil.exe -addstore -f Root "%CERT%" >> "%LOG%" 2>&1
if not "%errorlevel%"=="0" goto failed

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Add-AppxPackage -Path '%MSIX%' -ForceApplicationShutdown -ErrorAction Stop" >> "%LOG%" 2>&1
if not "%errorlevel%"=="0" goto failed

echo 安装成功 >> "%LOG%"
echo.
echo 发票工具箱安装完成。
pause
exit /b 0

:failed
echo 安装失败，错误码 %errorlevel% >> "%LOG%"
echo.
echo 安装失败，详细原因已写入：%LOG%
pause
exit /b 1
