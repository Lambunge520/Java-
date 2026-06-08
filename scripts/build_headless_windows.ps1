$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ScriptDir
$Src = Join-Path $Root "src"
$Assets = Join-Path $Root "assets"
$Deps = Join-Path $Root "vendor\deps"
Set-Location $Root

python -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --console `
  --name "LJM-Java-Manager-headless" `
  --icon "$Assets\java.ico" `
  --add-data "$Src\LJM_headless.pyw;." `
  --add-data "$Src\LJM.pyw;." `
  --add-data "$Assets\java.ico;." `
  --add-data "$Deps;deps" `
  "$Src\LJM_headless_entry.py"

Write-Host "Windows headless build finished: $Root\dist\LJM-Java-Manager-headless.exe"
