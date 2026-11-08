@echo off
rem uv also fetches Linux-only URL deps (pgi) to validate the lock; if that fails, start anyway.
uv sync --quiet || echo WARNING: uv sync failed, starting with the existing .venv
uv run --no-sync python build.py run
exit /b %ERRORLEVEL%
