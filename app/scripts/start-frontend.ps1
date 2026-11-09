param([switch]$Browser, [switch]$Server, [ValidateRange(1024,65535)][int]$ApiPort = 8080)
$ErrorActionPreference = 'Stop'
if ($Browser -and $Server) { throw 'Choose either -Browser or -Server.' }
$appRoot = Split-Path -Parent $PSScriptRoot
$localNode = Get-ChildItem -LiteralPath (Join-Path $appRoot '.tools') -Directory -Filter 'node-v*-win-x64' -ErrorAction SilentlyContinue | Sort-Object Name -Descending | Select-Object -First 1
if ($localNode) { $env:PATH = $localNode.FullName + ';' + $env:PATH }
if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw 'Install Node.js 22.12+ and retry.' }
$nodeVersion = [version]((& node --version) -replace '^v', '')
if ($nodeVersion -lt [version]'22.12.0') { throw 'Node.js 22.12+ is required.' }
$env:VITE_API_MODE = if ($Browser) { 'browser' } else { 'server' }
$env:VITE_API_TARGET = "http://127.0.0.1:$ApiPort"
Push-Location (Join-Path $appRoot 'frontend')
try {
    if (-not (Test-Path -LiteralPath 'node_modules')) {
        & npm.cmd ci --cache (Join-Path $appRoot '.cache/npm')
        if ($LASTEXITCODE -ne 0) { throw 'npm ci failed.' }
    }
    & npm.cmd run dev
} finally { Pop-Location }
