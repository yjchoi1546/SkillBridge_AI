param([switch]$Test, [ValidateRange(1024,65535)][int]$Port = 8080)
$ErrorActionPreference = 'Stop'
$appRoot = Split-Path -Parent $PSScriptRoot
$localJdk = Get-ChildItem -LiteralPath (Join-Path $appRoot '.tools/jdk21') -Directory -ErrorAction SilentlyContinue | Sort-Object Name -Descending | Select-Object -First 1
if ($localJdk) { $env:JAVA_HOME = $localJdk.FullName }
if (-not $env:JAVA_HOME -or -not (Test-Path -LiteralPath (Join-Path $env:JAVA_HOME 'bin/java.exe'))) { throw 'Install JDK 21 and set JAVA_HOME.' }
$localMaven = Get-ChildItem -LiteralPath (Join-Path $appRoot '.tools') -Directory -Filter 'apache-maven-*' -ErrorAction SilentlyContinue | Sort-Object Name -Descending | Select-Object -First 1
$maven = if ($localMaven) { Join-Path $localMaven.FullName 'bin/mvn.cmd' } else { (Get-Command mvn.cmd -ErrorAction Stop).Source }
Push-Location (Join-Path $appRoot 'backend')
try {
    $task = if ($Test) { 'test' } else { 'spring-boot:run' }
    $taskArgs = @("-Dmaven.repo.local=$(Join-Path $appRoot '.cache/m2')", $task, '-B', '-ntp')
    if (-not $Test) { $taskArgs += "-Dspring-boot.run.arguments=--server.port=$Port" }
    & $maven @taskArgs
    if ($LASTEXITCODE -ne 0) { throw 'Spring Boot command failed.' }
} finally { Pop-Location }
