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
  --windowed `
  --name "LJM-Java-Manager" `
  --icon "$Assets\java.ico" `
  --hidden-import plistlib `
  --hidden-import hashlib `
  --hidden-import locale `
  --hidden-import socket `
  --hidden-import stat `
  --add-data "$Assets\java.ico;." `
  --add-data "$Deps;deps" `
  "$Src\LJM.pyw"

Write-Host "Windows build finished: $Root\dist\LJM-Java-Manager.exe"
