param()
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'launcher-common.ps1')
$lock = $null
try {
    $lock = Get-LauncherLock
    $runtime = Read-Runtime
    if ($runtime) { Stop-Runtime $runtime; Write-Host 'SkillBridge stopped. Your accounts and saved work are kept.' }
    else { Write-Host 'No instance started by START.cmd is running.' }
} catch {
    Write-Host "Could not stop SkillBridge: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
} finally { if ($lock) { $lock.Dispose() } }
