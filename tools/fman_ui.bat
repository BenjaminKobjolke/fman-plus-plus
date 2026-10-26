@echo off
setlocal
if defined VIRTUAL_ENV call set "PATH=%%PATH:%VIRTUAL_ENV%\Scripts;=%%"
set "VIRTUAL_ENV="
if not defined FMAN_PYTHON set "FMAN_PYTHON=python"
"%FMAN_PYTHON%" "%~dp0fman_ui\fman_ui.py" %*
exit /b %ERRORLEVEL%
