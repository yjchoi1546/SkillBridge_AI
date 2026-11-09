$appRoot = Split-Path -Parent $PSScriptRoot
$cacheRoot = Join-Path $appRoot '.cache'
$runtimeFile = Join-Path $cacheRoot 'app-runtime.json'

function Get-LauncherLock {
    New-Item -ItemType Directory -Path $cacheRoot -Force | Out-Null
    try { return [IO.File]::Open((Join-Path $cacheRoot 'launcher.lock'), 'OpenOrCreate', 'ReadWrite', 'None') }
    catch { throw 'Another start/stop operation is running. Wait until it finishes, then try again.' }
}
function Read-Runtime {
    if (Test-Path -LiteralPath $runtimeFile) { return Get-Content -LiteralPath $runtimeFile -Raw | ConvertFrom-Json }
    return $null
}
function Get-OwnedProcess($Identity) {
    if (-not $Identity) { return $null }
    $process = Get-Process -Id $Identity.id -ErrorAction SilentlyContinue
    if ($process -and $process.StartTime.ToUniversalTime().Ticks.ToString() -eq $Identity.started) { return $process }
    return $null
}
function Get-ProcessIdentity($Process) {
    $Process.Refresh()
    return @{ id = $Process.Id; started = $Process.StartTime.ToUniversalTime().Ticks.ToString() }
}
function Save-Runtime($Runtime) {
    # Atomic file replacement: an interrupted launch still leaves enough information to stop its children.
    $temporary = "$runtimeFile.new"
    [IO.File]::WriteAllText($temporary, ($Runtime | ConvertTo-Json -Depth 5), [Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $temporary -Destination $runtimeFile -Force
}
function Stop-Runtime($Runtime) {
    if ($Runtime) {
        foreach ($identity in @($Runtime.frontend, $Runtime.backend)) {
            $process = Get-OwnedProcess $identity
            if ($process) {
                # Include Vite's esbuild child and any Python job started by this Java process.
                $killer = Start-Process -FilePath (Join-Path $env:SystemRoot 'System32/taskkill.exe') -ArgumentList @('/PID', $process.Id, '/T', '/F') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $cacheRoot 'stop-process.log') -RedirectStandardError (Join-Path $cacheRoot 'stop-process-error.log')
                if (-not $killer.WaitForExit(10000)) {
                    $killer.Kill()
                    throw "Stopping process $($process.Id) timed out. Retry STOP.cmd."
                }
                if (-not $process.WaitForExit(10000)) { throw "Could not stop process $($process.Id). See app/.cache/stop-process-error.log." }
            }
        }
    }
    if (Test-Path -LiteralPath $runtimeFile) { Remove-Item -LiteralPath $runtimeFile -Force }
}
function Find-FreePort([int]$Preferred) {
    for ($port = $Preferred; $port -le [Math]::Min($Preferred + 99, 65535); $port++) {
        $listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, $port)
        try { $listener.Start(); return $port }
        catch [Net.Sockets.SocketException] { }
        finally { $listener.Stop() }
    }
    throw "No free local port found near $Preferred."
}
function Test-Http([string]$Uri) {
    try { return (Invoke-WebRequest -UseBasicParsing -Uri $Uri -TimeoutSec 2).StatusCode -eq 200 }
    catch { return $false }
}
function Wait-Server([string]$Uri, $Identity, [int]$Seconds = 180) {
    $deadline = [DateTime]::UtcNow.AddSeconds($Seconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        if (-not (Get-OwnedProcess $Identity)) { throw 'A server stopped before it became ready. Check the server logs in app/.cache.' }
        if (Test-Http $Uri) { return }
        Start-Sleep -Milliseconds 500
    }
    throw "Server startup timed out: $Uri. Check the server logs in app/.cache."
}
