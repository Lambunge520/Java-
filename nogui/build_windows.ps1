$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

python -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --console `
  --name "LJM-Java-Manager-nogui" `
  --icon "$Root\java.ico" `
  --add-data "$Root\LJM_nogui.pyw;." `
  --add-data "$Root\LJM.pyw;." `
  --add-data "$Root\java.ico;." `
  --add-data "$Root\deps;deps" `
  "$Root\LJM_nogui_entry.py"

Write-Host "Windows nogui build finished: $Root\dist\LJM-Java-Manager-nogui.exe"
