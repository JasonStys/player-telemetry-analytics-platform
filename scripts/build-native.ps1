# File: build-native.ps1
# Purpose: Bundle the actual Python/DuckDB/SQL/React/Tk application into a fresh Windows app directory.
# Symbols and important variables are indexed in docs/code-index.md.
param([string]$Output = 'release/windows', [string]$Python = $env:PLAYER_BUILD_PYTHON)
$ErrorActionPreference = 'Stop'
$taskRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$taskRelease = [IO.Path]::GetFullPath((Join-Path $taskRoot 'release'))
$taskOutput = [IO.Path]::GetFullPath((Join-Path $taskRoot $Output))
if (-not $IsWindows -or -not $taskOutput.StartsWith($taskRelease + [IO.Path]::DirectorySeparatorChar) -or (Test-Path -LiteralPath $taskOutput)) {
    throw 'Use a new Windows output directory below release; existing packages are preserved.'
}
if (-not $Python) { $Python = Join-Path $taskRoot '.venv-native31410/Scripts/python.exe' }
if (-not (Test-Path -LiteralPath $Python)) { throw 'A build-only isolated Python environment is required.' }
function Invoke-Checked([string]$Program, [string[]]$Arguments) {
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Build tool failed: $([IO.Path]::GetFileName($Program))" }
}
Push-Location $taskRoot
$taskOldCache = $env:PYINSTALLER_CONFIG_DIR
try {
    $taskPackage = Get-Content -LiteralPath web/package.json -Raw | ConvertFrom-Json
    if ($taskPackage.version -ne '1.1.0') { throw 'Native product version must be1.1.0.' }
    Invoke-Checked $Python @('-c', 'import sys; sys.exit(0 if sys.version_info[:3] == (3,14,10) else 2)')
    Invoke-Checked 'npm.cmd' @('--prefix', 'web', 'run', 'build')
    $taskMetadata = Join-Path $taskRoot ('.runtime/native-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $taskMetadata -Force | Out-Null
    $env:PYINSTALLER_CONFIG_DIR = Join-Path $taskMetadata 'cache'
    $taskSource = (& git -c "safe.directory=$($taskRoot.Replace('\','/'))" rev-parse HEAD).Trim()
    if ($LASTEXITCODE -ne 0 -or $taskSource -notmatch '^[a-f0-9]{40}$') { throw 'Git source identity required.' }
    $taskDirty = [bool](& git -c "safe.directory=$($taskRoot.Replace('\','/'))" status --porcelain)
    [IO.File]::WriteAllText((Join-Path $taskMetadata 'source-release.json'),
        (@{source=$taskSource;source_dirty=$taskDirty} | ConvertTo-Json), [Text.UTF8Encoding]::new($false))
    Invoke-Checked $Python @('-m', 'PyInstaller', '--noconfirm', '--clean', '--windowed', '--onefile',
        '--name', 'PlayerTelemetryAnalytics', '--distpath', $taskOutput, '--paths', '.', '--paths', 'src',
        '--collect-data', 'duckdb', '--hidden-import', '_duckdb', '--add-data', 'sql:telemetry_platform/sql',
        '--add-data', 'web/dist:ui', '--add-data', "${taskMetadata}/source-release.json:.", 'desktop/launcher.py')
    Copy-Item -LiteralPath LICENSE -Destination (Join-Path $taskOutput 'LICENSE.txt')
    Invoke-Checked $Python @('scripts/native-notices.py', (Join-Path $taskOutput 'THIRD-PARTY-NOTICES'))
    [IO.File]::WriteAllText((Join-Path $taskOutput 'SOURCE.json'),
        (@{schema=1;product='player-telemetry-analytics-platform';version='1.1.0';source=$taskSource;
            sourceDirty=$taskDirty;distribution='unsigned-windows-portable-executable'} | ConvertTo-Json),
        [Text.UTF8Encoding]::new($false))
    Write-Output 'Built actual bundled application. Native acceptance and publication are still required.'
} finally { $env:PYINSTALLER_CONFIG_DIR = $taskOldCache; Pop-Location }
