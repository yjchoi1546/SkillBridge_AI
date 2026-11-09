# All downloads and tools stay in app. No administrator access or global PATH edits.
param()
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
if (-not [Environment]::Is64BitOperatingSystem -or $env:PROCESSOR_ARCHITECTURE -eq 'ARM64') {
    throw 'The one-click launcher currently supports Windows x64. See app/README.md for manual startup.'
}
$appRoot = Split-Path -Parent $PSScriptRoot
$toolsRoot = Join-Path $appRoot '.tools'
$downloadRoot = Join-Path $appRoot '.cache/downloads'
New-Item -ItemType Directory -Path $toolsRoot,$downloadRoot -Force | Out-Null

function Read-RemoteText([string]$Uri) {
    $response = Invoke-WebRequest -UseBasicParsing -Uri $Uri -TimeoutSec 120
    if ($response.Content -is [byte[]]) { return [Text.Encoding]::UTF8.GetString($response.Content) }
    return [string]$response.Content
}
function Install-Archive([string]$Name, [string]$Uri, [string]$Hash, [string]$Algorithm, [string]$Destination) {
    if ($Hash -notmatch '^[a-fA-F0-9]{64}$|^[a-fA-F0-9]{128}$') { throw "Invalid checksum for $Name" }
    $archive = Join-Path $downloadRoot "$Name.zip"
    if (-not (Test-Path -LiteralPath $archive) -or (Get-FileHash -LiteralPath $archive -Algorithm $Algorithm).Hash -ne $Hash) {
        Write-Host "Downloading $Name (first run only)..."
        $partial = "$archive.part"
        Invoke-WebRequest -UseBasicParsing -Uri $Uri -OutFile $partial -TimeoutSec 900
        if ((Get-FileHash -LiteralPath $partial -Algorithm $Algorithm).Hash -ne $Hash) { throw "Download checksum failed: $Name. Please retry." }
        Move-Item -LiteralPath $partial -Destination $archive -Force
    }
    Write-Host "Unpacking $Name..."
    Expand-Archive -LiteralPath $archive -DestinationPath $Destination -Force
}

$nodeName = 'node-v22.23.4-win-x64'
$nodeRoot = Join-Path $toolsRoot $nodeName
if (-not (Test-Path -LiteralPath (Join-Path $nodeRoot 'node.exe')) -or
    -not (Test-Path -LiteralPath (Join-Path $nodeRoot 'node_modules/npm/bin/npm-cli.js'))) {
    $nodeBase = 'https://nodejs.org/dist/v22.23.4'
    $checksum = (Read-RemoteText "$nodeBase/SHASUMS256.txt") -split '\r?\n' |
        ForEach-Object { $parts = $_.Trim() -split '\s+'; if ($parts.Count -eq 2 -and $parts[1] -eq "$nodeName.zip") { $parts[0] } }
    Install-Archive 'node-22.23.4' "$nodeBase/$nodeName.zip" $checksum 'SHA256' $toolsRoot
}

$jdkContainer = Join-Path $toolsRoot 'jdk21'
$jdk = Get-ChildItem -LiteralPath $jdkContainer -Directory -ErrorAction SilentlyContinue |
    Where-Object { (Test-Path -LiteralPath (Join-Path $_.FullName 'bin/java.exe')) -and (Test-Path -LiteralPath (Join-Path $_.FullName 'bin/javac.exe')) } |
    Sort-Object Name -Descending | Select-Object -First 1
if (-not $jdk) {
    $assets = Invoke-RestMethod -Uri 'https://api.adoptium.net/v3/assets/latest/21/hotspot?architecture=x64&image_type=jdk&os=windows&vendor=eclipse' -TimeoutSec 120
    $package = $assets[0].binary.package
    Install-Archive 'jdk21' $package.link $package.checksum 'SHA256' $jdkContainer
    $jdk = Get-ChildItem -LiteralPath $jdkContainer -Directory |
        Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'bin/javac.exe') } | Select-Object -First 1
}
if (-not $jdk) { throw 'JDK installation did not produce a JDK 21 directory.' }

$mavenRoot = Join-Path $toolsRoot 'apache-maven-3.9.9'
if (-not (Test-Path -LiteralPath (Join-Path $mavenRoot 'bin/mvn.cmd'))) {
    $mavenUri = 'https://archive.apache.org/dist/maven/maven-3/3.9.9/binaries/apache-maven-3.9.9-bin.zip'
    $checksum = ((Read-RemoteText "$mavenUri.sha512").Trim() -split '\s+')[0]
    Install-Archive 'maven-3.9.9' $mavenUri $checksum 'SHA512' $toolsRoot
}

$uvRoot = Join-Path $toolsRoot 'uv'
$uv = Join-Path $uvRoot 'uv.exe'
if (-not (Test-Path -LiteralPath $uv)) {
    $existingUv = Get-Command uv.exe -ErrorAction SilentlyContinue
    if ($existingUv) { $uv = $existingUv.Source }
    else {
        $uvUri = 'https://releases.astral.sh/github/uv/releases/download/0.12.15/uv-x86_64-pc-windows-msvc.zip'
        $checksum = ((Read-RemoteText "$uvUri.sha256").Trim() -split '\s+')[0]
        Install-Archive 'uv-0.12.15' $uvUri $checksum 'SHA256' $uvRoot
    }
}
foreach ($executable in @((Join-Path $nodeRoot 'node.exe'), (Join-Path $jdk.FullName 'bin/java.exe'), (Join-Path $mavenRoot 'bin/mvn.cmd'), $uv)) {
    if (-not (Test-Path -LiteralPath $executable)) { throw "Tool installation incomplete: $executable" }
}
[pscustomobject]@{
    NodeRoot = $nodeRoot
    JavaRoot = $jdk.FullName
    Maven = Join-Path $mavenRoot 'bin/mvn.cmd'
    Uv = $uv
}
