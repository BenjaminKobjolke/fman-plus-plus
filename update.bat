@echo off
REM fman - Update Libraries: re-resolve uv.lock, sync .venv, run the unit tests.
REM Most dependencies are pinned in pyproject.toml; raise a pin there to move it.
setlocal
cd /d "%~dp0"
where uv >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo ERROR: uv is not installed or not in PATH
    echo Please install uv first: https://docs.astral.sh/uv/getting-started/installation/
    exit /b 1
)
REM fbs Pro is not on PyPI and uv cannot use its URL; see vendor\README.md.
uv run --no-project python "%~dp0tools\fbs_pro.py"
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to download fbs Pro
    exit /b 1
)
uv lock --upgrade
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to update lock file
    exit /b 1
)
uv sync
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to sync dependencies
    exit /b 1
)
call "%~dp0tools\run_tests.bat"
exit /b %ERRORLEVEL%
