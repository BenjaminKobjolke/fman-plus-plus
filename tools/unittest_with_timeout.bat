@echo off
setlocal
REM Shared entry point for run_*_tests.bat commands.
REM Tickets Watcher starts this with its own venv first on PATH. Drop it so it
REM does not leak into child processes; fman's tests run on the project .venv.
if defined VIRTUAL_ENV call set "PATH=%%PATH:%VIRTUAL_ENV%\Scripts;=%%"
set "VIRTUAL_ENV="
call "%~dp0find_build_python.bat"
if errorlevel 1 exit /b 1
set QT_QPA_PLATFORM=offscreen
"%FMAN_PYTHON%" "%~dp0unittest_with_timeout.py" %*
exit /b %ERRORLEVEL%
