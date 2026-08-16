$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ScriptDir
$Src = Join-Path $Root "src"
$Assets = Join-Path $Root "assets"
Set-Location $Root

# NoGUI never starts the desktop tray, so the pystray/Pillow wheels are
# intentionally not bundled; the shared desktop core only loads them lazily
# for the tray icon.

$PyInstallerArgs = @(
  "--noconfirm",
  "--clean",
  "--onefile",
  "--console",
  "--name", "LJM-Java-Manager-nogui",
  "--icon", "$Assets\java.ico",
  "--hidden-import", "plistlib",
  "--hidden-import", "hashlib",
  "--hidden-import", "locale",
  "--hidden-import", "socket",
  "--hidden-import", "stat",
  "--add-data", "$Src\LJM_nogui.pyw;.",
  "--add-data", "$Src\LJM.pyw;.",
  "--add-data", "$Assets\java.ico;.",
  "$Src\LJM_nogui_entry.py"
)

python -m PyInstaller @PyInstallerArgs

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
