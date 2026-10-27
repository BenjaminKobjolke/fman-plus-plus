@echo off
REM Point FMAN_PYTHON at the project's uv venv (.venv, created by install.bat).
REM No setlocal: callers read FMAN_PYTHON after the call. A preset FMAN_PYTHON wins.
if defined FMAN_PYTHON exit /b 0
set "FMAN_PYTHON=%~dp0..\.venv\Scripts\python.exe"
if exist "%FMAN_PYTHON%" exit /b 0
echo ERROR: no .venv python at %FMAN_PYTHON% - run install.bat first.
set "FMAN_PYTHON="
exit /b 1
