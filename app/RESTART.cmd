@echo off
setlocal
call "%~dp0START.cmd" -Restart %*
exit /b %errorlevel%
