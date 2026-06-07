$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

python -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --console `
  --name "LJM-Java-Manager-headless" `
  --icon "$Root\java.ico" `
  --add-data "$Root\LJM_headless.pyw;." `
  --add-data "$Root\LJM.pyw;." `
  --add-data "$Root\java.ico;." `
  --add-data "$Root\deps;deps" `
  "$Root\LJM_headless_entry.py"

Write-Host "Windows headless build finished: $Root\dist\LJM-Java-Manager-headless.exe"
