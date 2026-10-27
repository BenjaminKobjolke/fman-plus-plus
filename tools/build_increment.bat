@echo off
REM Bump the version in base.json and print the new value.
call "%~dp0find_build_python.bat"
if errorlevel 1 exit /b 1
"%FMAN_PYTHON%" "%~dp0release\build_number.py" increment
exit /b %ERRORLEVEL%
