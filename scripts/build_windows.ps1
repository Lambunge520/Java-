$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ScriptDir
$Src = Join-Path $Root "src"
$Assets = Join-Path $Root "assets"
$Deps = Join-Path $Root "vendor\deps"
Set-Location $Root

# vendor\deps carries wheels for every platform; only the directory matching
# this build machine may go into the exe, otherwise one package would ship
# components for all three operating systems.
$Arch = "amd64"
if ($env:PROCESSOR_ARCHITECTURE -eq "ARM64") { $Arch = "arm64" }
elseif ($env:PROCESSOR_ARCHITECTURE -eq "X86") { $Arch = "x86" }
$PlatformDepsName = "windows-$Arch"
$PlatformDeps = Join-Path $Deps $PlatformDepsName

$PyInstallerArgs = @(
  "--noconfirm",
  "--clean",
  "--onefile",
  "--windowed",
  "--name", "LJM-Java-Manager",
  "--icon", "$Assets\java.ico",
  "--hidden-import", "plistlib",
  "--hidden-import", "hashlib",
  "--hidden-import", "locale",
  "--hidden-import", "socket",
  "--hidden-import", "stat",
  "--add-data", "$Assets\java.ico;."
)

if (Test-Path $PlatformDeps) {
  $StageRoot = Join-Path $Root "build\deps-stage"
  $StagePlatform = Join-Path $StageRoot $PlatformDepsName
  if (Test-Path $StageRoot) { Remove-Item -Recurse -Force $StageRoot }
  New-Item -ItemType Directory -Force -Path $StagePlatform | Out-Null
  Copy-Item -Path (Join-Path $PlatformDeps "*") -Destination $StagePlatform -Recurse -Force
  $PyInstallerArgs += @("--add-data", "$StageRoot;deps")
} else {
  Write-Warning "Platform dependency directory not found: $PlatformDeps (tray deps will be installed at runtime)"
}

$PyInstallerArgs += "$Src\LJM.pyw"

python -m PyInstaller @PyInstallerArgs

Write-Host "Windows build finished: $Root\dist\LJM-Java-Manager.exe"
