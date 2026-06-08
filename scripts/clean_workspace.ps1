[CmdletBinding(SupportsShouldProcess = $true)]
param()

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = (Resolve-Path (Join-Path $ScriptDir "..")).Path

function Remove-WorkspacePath {
  param([Parameter(Mandatory = $true)][string]$Path)

  if (-not (Test-Path -LiteralPath $Path)) {
    return
  }

  $resolved = (Resolve-Path -LiteralPath $Path).Path
  $rootWithSep = $Root.TrimEnd([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar
  if ($resolved -ne $Root -and -not $resolved.StartsWith($rootWithSep, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to remove path outside repository: $resolved"
  }

  if ($PSCmdlet.ShouldProcess($resolved, "Remove workspace temporary path")) {
    Remove-Item -LiteralPath $resolved -Recurse -Force
  }
}

$fixedPaths = @(
  "build",
  "dist",
  "deps_wheels_tmp",
  "release-assets"
)

foreach ($item in $fixedPaths) {
  Remove-WorkspacePath (Join-Path $Root $item)
}

$patterns = @(
  "__pycache__",
  "*.pyc",
  "*.pyo",
  "*.spec",
  "*.log",
  "*.tmp",
  "*.new",
  "ljm_headless_result.json",
  "headless_test_result*.json",
  "LJM-Java-Manager*.zip",
  "LJM-Java-Manager*.tar.gz",
  "LJM-Java-Manager*.tgz",
  "LJM-Java-Manager*.exe",
  "SHA256SUMS*.txt"
)

foreach ($pattern in $patterns) {
  Get-ChildItem -LiteralPath $Root -Recurse -Force -Filter $pattern -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notlike "$Root\.git*" } |
    ForEach-Object { Remove-WorkspacePath $_.FullName }
}

Write-Host "Workspace cleanup finished: $Root"
