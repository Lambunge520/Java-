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
  --hidden-import plistlib `
  --hidden-import hashlib `
  --hidden-import locale `
  --hidden-import socket `
  --hidden-import stat `
  --add-data "$Root\LJM_nogui.pyw;." `
  --add-data "$Root\LJM.pyw;." `
  --add-data "$Root\java.ico;." `
  --add-data "$Deps;deps" `
  "$Root\LJM_nogui_entry.py"

$Exe = Join-Path $Root "dist\LJM-Java-Manager-nogui.exe"
& $Exe version --stdout
if ($LASTEXITCODE -ne 0) {
  throw "Windows NoGUI one-shot smoke test failed with exit code $LASTEXITCODE"
}
@("status", "exit") | & $Exe
if ($LASTEXITCODE -ne 0) {
  throw "Windows NoGUI terminal smoke test failed with exit code $LASTEXITCODE"
}

Write-Host "Windows nogui build finished: $Root\dist\LJM-Java-Manager-nogui.exe"
