param(
  [switch]$Console
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $Root

function Run-Step {
  param(
    [Parameter(Mandatory = $true)]
    [string]$FilePath,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Arguments
  )
  & $FilePath @Arguments
  if ($LASTEXITCODE -ne 0) {
    throw "Command failed: $FilePath $($Arguments -join ' ')"
  }
}

function Test-PythonCommand {
  param(
    [Parameter(Mandatory = $true)]
    [string]$FilePath,
    [string[]]$Arguments = @()
  )
  try {
    & $FilePath @Arguments --version *> $null
    return $LASTEXITCODE -eq 0
  } catch {
    return $false
  }
}

function New-Venv {
  if ($env:PYTHON_EXE) {
    if (-not (Test-PythonCommand $env:PYTHON_EXE)) {
      throw "PYTHON_EXE 指向的 Python 不可用：$env:PYTHON_EXE"
    }
    Run-Step $env:PYTHON_EXE -m venv .venv-win
    return
  }

  if (Test-PythonCommand py @("-3.10")) {
    Run-Step py -3.10 -m venv .venv-win
    return
  }

  if (Test-PythonCommand py @("-3")) {
    Run-Step py -3 -m venv .venv-win
    return
  }

  if (Test-PythonCommand python) {
    Run-Step python -m venv .venv-win
    return
  }

  if (Test-PythonCommand python3) {
    Run-Step python3 -m venv .venv-win
    return
  }

  throw "未找到可用 Python。请安装 Python 3.10/3.11，或设置环境变量 PYTHON_EXE 指向 python.exe 后重试。"
}

if (-not (Test-Path ".venv-win\Scripts\python.exe")) {
  New-Venv
}

$VenvPython = ".\.venv-win\Scripts\python.exe"
Run-Step $VenvPython -m pip install --upgrade pip
Run-Step $VenvPython -m pip install -r requirements.txt
Run-Step $VenvPython -m pip install pyinstaller

Run-Step $VenvPython scripts\generate_icon.py
Run-Step $VenvPython -m unittest discover -s tests -v

$OldConsole = $env:INVOICE_TOOLBOX_CONSOLE
try {
  if ($Console) {
    $env:INVOICE_TOOLBOX_CONSOLE = "1"
    Write-Host "Building console diagnostic exe..."
  } else {
    Remove-Item Env:\INVOICE_TOOLBOX_CONSOLE -ErrorAction SilentlyContinue
    Write-Host "Building windowed exe..."
  }
  Run-Step $VenvPython -m PyInstaller --clean --noconfirm build\pyinstaller\invoice_toolbox.spec
} finally {
  if ($null -eq $OldConsole) {
    Remove-Item Env:\INVOICE_TOOLBOX_CONSOLE -ErrorAction SilentlyContinue
  } else {
    $env:INVOICE_TOOLBOX_CONSOLE = $OldConsole
  }
}

Write-Host ""
Write-Host "Done: dist\发票工具箱.exe"
if (-not $Console) {
  Write-Host "运行时日志：dist\发票工具箱.log"
}
