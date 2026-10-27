@echo off
REM Print the full release label <version>_<build> (version from src/build/settings/base.json).
call "%~dp0find_build_python.bat"
if errorlevel 1 exit /b 1
"%FMAN_PYTHON%" "%~dp0release\build_number.py" label
exit /b %ERRORLEVEL%
