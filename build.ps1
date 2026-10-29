param([string]$Python = '.venv\Scripts\python.exe', [string]$OutputDirectory = 'dist/public-release', [switch]$SkipTests)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Output exists. Choose a fresh directory; stable releases are never replaced.' }
& $Python tools/render_preview.py --icon-only
if ($LASTEXITCODE -ne 0) { throw 'Icon generation failed' }
if (-not $SkipTests) {
    & $Python -m pytest -q --tb=short
    if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
}
& $Python tools/prepare_compliance.py
if ($LASTEXITCODE -ne 0) { throw 'Third-party source/license preparation failed' }
& $Python -m PyInstaller --clean --noconfirm --distpath $OutputDirectory FileFlow.spec
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed' }
$bundle = Join-Path $OutputDirectory 'FileFlow'
foreach ($file in @('README.md','LICENSING.md','THIRD_PARTY_RIGHTS.md','CHANGELOG.md','THIRD_PARTY_NOTICES.md')) { Copy-Item -LiteralPath $file -Destination $bundle }
New-Item -ItemType Directory -Path (Join-Path $bundle 'docs/screenshots') -Force | Out-Null
Get-ChildItem -LiteralPath 'docs' -File -Filter '*.md' | Copy-Item -Destination (Join-Path $bundle 'docs')
Copy-Item -LiteralPath 'docs/screenshots/public' -Destination (Join-Path $bundle 'docs/screenshots') -Recurse -Force
Write-Host "Built $bundle. Run tools/validate_portable.py before packaging."
