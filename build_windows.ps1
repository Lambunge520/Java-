$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

python -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --windowed `
  --name "LJM-Java-Manager" `
  --icon "$Root\java.ico" `
  --add-data "$Root\java.ico;." `
  --add-data "$Root\deps;deps" `
  "$Root\LJM.pyw"

Write-Host "Windows build finished: $Root\dist\LJM-Java-Manager.exe"
