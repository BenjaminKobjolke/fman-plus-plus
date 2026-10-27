@echo off
setlocal
if defined VIRTUAL_ENV call set "PATH=%%PATH:%VIRTUAL_ENV%\Scripts;=%%"
set "VIRTUAL_ENV="
call "%~dp0find_build_python.bat"
if errorlevel 1 exit /b 1
"%FMAN_PYTHON%" "%~dp0fman_ui\fman_ui.py" %*
exit /b %ERRORLEVEL%
