@echo off
REM Restore the version from the current Git commit and print it.
call "%~dp0find_build_python.bat"
if errorlevel 1 exit /b 1
"%FMAN_PYTHON%" "%~dp0release\build_number.py" decrement
exit /b %ERRORLEVEL%
