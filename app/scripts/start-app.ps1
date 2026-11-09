param(
    [switch]$Restart,
    [switch]$NoBrowser,
    [ValidateRange(1024,65535)][int]$BackendPort = 18080,
    [ValidateRange(1024,65535)][int]$FrontendPort = 5173
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'launcher-common.ps1')
$lock = $null
$transcript = $false
$started = $null
try {
    $lock = Get-LauncherLock
    Start-Transcript -LiteralPath (Join-Path $cacheRoot 'launcher.log') -Append | Out-Null
    $transcript = $true
    $runtime = Read-Runtime
    if ($runtime -and -not $Restart -and (Get-OwnedProcess $runtime.backend) -and (Get-OwnedProcess $runtime.frontend) -and (Test-Http "$($runtime.url)/api/health")) {
        Write-Host "SkillBridge is already running: $($runtime.url)"
        if (-not $NoBrowser) { Start-Process $runtime.url }
        exit 0
    }
    if ($runtime) { Write-Host 'Stopping the previous SkillBridge instance...'; Stop-Runtime $runtime }

    Write-Host '[1/5] Preparing tools. First startup needs internet and may take several minutes.'
    $tools = & (Join-Path $PSScriptRoot 'setup-tools.ps1')
    $env:JAVA_HOME = $tools.JavaRoot
    $env:PATH = $tools.NodeRoot + ';' + (Split-Path -Parent $tools.Uv) + ';' + $env:PATH

    Write-Host '[2/5] Preparing the Python AI environment...'
    & (Join-Path $PSScriptRoot 'setup-ai.ps1')

    Write-Host '[3/5] Preparing the web app...'
    Push-Location (Join-Path $appRoot 'frontend')
    try {
        $dependencyKey = (Get-FileHash -LiteralPath 'package.json').Hash + (Get-FileHash -LiteralPath 'package-lock.json').Hash
        $dependencyStamp = Join-Path $cacheRoot 'frontend-dependencies.txt'
        $previousKey = if (Test-Path -LiteralPath $dependencyStamp) { [IO.File]::ReadAllText($dependencyStamp) } else { '' }
        if ($dependencyKey -ne $previousKey -or -not (Test-Path -LiteralPath 'node_modules/vite/bin/vite.js')) {
            if (Test-Path -LiteralPath $dependencyStamp) { Remove-Item -LiteralPath $dependencyStamp }
            & (Join-Path $tools.NodeRoot 'npm.cmd') ci --cache (Join-Path $cacheRoot 'npm') --no-audit --no-fund
            if ($LASTEXITCODE -ne 0) { throw 'Web dependencies could not be installed. Check internet access and retry START.cmd.' }
            [IO.File]::WriteAllText($dependencyStamp, $dependencyKey)
        }
    } finally { Pop-Location }
    Push-Location (Join-Path $appRoot 'backend')
    try {
        & $tools.Maven "-Dmaven.repo.local=$(Join-Path $cacheRoot 'm2')" package '-DskipTests' -B -ntp
        if ($LASTEXITCODE -ne 0) { throw 'Backend build failed. See app/.cache/launcher.log.' }
    } finally { Pop-Location }

    Write-Host '[4/5] Starting the servers...'
    $backend = Find-FreePort $BackendPort
    $frontend = Find-FreePort $FrontendPort
    if ($frontend -eq $backend) { $frontend = Find-FreePort ($frontend + 1) }
    $started = @{ backend = $null; frontend = $null; url = "http://127.0.0.1:$frontend"; backendPort = $backend }
    # Team preview always uses local H2 and fake AI, without API keys or external services.
    $env:SKILLBRIDGE_PYTHON = $tools.Uv
    $env:LLM_PROVIDER = 'fake'
    $env:SKILLBRIDGE_AI_MODE = 'python'
    $env:SPRING_PROFILES_ACTIVE = 'local'
    $jar = Join-Path $appRoot 'backend/target/skillbridge-api-0.1.0.jar'
    $javaArgs = @('-jar', ('"' + $jar + '"'), "--server.port=$backend", '--server.address=127.0.0.1',
        '--spring.datasource.url=jdbc:h2:file:./.data/skillbridge;MODE=PostgreSQL;DB_CLOSE_ON_EXIT=FALSE',
        '--spring.datasource.username=sa', '--spring.datasource.password=', '--skillbridge.demo-enabled=false',
        '--skillbridge.ai.mode=python', '--skillbridge.ai.provider=fake')
    $process = Start-Process -FilePath (Join-Path $tools.JavaRoot 'bin/java.exe') -ArgumentList $javaArgs -WorkingDirectory (Join-Path $appRoot 'backend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $cacheRoot 'backend-server.log') -RedirectStandardError (Join-Path $cacheRoot 'backend-server-error.log')
    $started.backend = Get-ProcessIdentity $process
    Save-Runtime $started
    Wait-Server "http://127.0.0.1:$backend/api/health" $started.backend

    $env:VITE_API_MODE = 'server'
    $env:VITE_API_TARGET = "http://127.0.0.1:$backend"
    $vite = Join-Path $appRoot 'frontend/node_modules/vite/bin/vite.js'
    $process = Start-Process -FilePath (Join-Path $tools.NodeRoot 'node.exe') -ArgumentList @(('"' + $vite + '"'), '--host', '127.0.0.1', '--port', $frontend, '--strictPort') -WorkingDirectory (Join-Path $appRoot 'frontend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $cacheRoot 'frontend-server.log') -RedirectStandardError (Join-Path $cacheRoot 'frontend-server-error.log')
    $started.frontend = Get-ProcessIdentity $process
    Save-Runtime $started
    Wait-Server "$($started.url)/api/health" $started.frontend

    Write-Host "[5/5] Ready: $($started.url)" -ForegroundColor Green
    Write-Host 'Create a personal or company account to begin. AI preview uses fake mode (no API key).'
    Write-Host 'Close this window freely. Use STOP.cmd to stop, or RESTART.cmd after pulling updates.'
    if (-not $NoBrowser) { Start-Process $started.url }
} catch {
    if ($started) { try { Stop-Runtime $started } catch { Write-Warning $_.Exception.Message } }
    Write-Host "Startup failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host 'See app/.cache/launcher.log and *-server-error.log. Fix the problem and double-click START.cmd again.'
    exit 1
} finally {
    if ($transcript) { Stop-Transcript | Out-Null }
    if ($lock) { $lock.Dispose() }
}
