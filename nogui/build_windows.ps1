$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Deps = Join-Path $Root "deps"
if (-not (Test-Path -LiteralPath $Deps)) {
  $RepoDeps = Join-Path (Split-Path -Parent $Root) "vendor\deps"
  if (Test-Path -LiteralPath $RepoDeps) {
    $Deps = $RepoDeps
  }
}
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
  --add-data "$Deps;deps" `
  "$Root\LJM_nogui_entry.py"

Write-Host "Windows nogui build finished: $Root\dist\LJM-Java-Manager-nogui.exe"
