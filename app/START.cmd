@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-app.ps1" %*
if errorlevel 1 (
  echo.
  echo Start failed. See the message above and app\.cache\launcher.log.
  pause
  exit /b 1
)
