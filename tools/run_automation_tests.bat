@echo off
setlocal
set ROOT=%~dp0..
set PYTHONPATH=%ROOT%\src\main\python;%ROOT%\src\unittest\python
set QT_QPA_PLATFORM=offscreen
call "%~dp0unittest_with_timeout.bat" fman_unittest.impl.scripting_automation_test
set "FIRST_RESULT=%ERRORLEVEL%"
call "%~dp0unittest_with_timeout.bat" fman_unittest.impl.link_capture_test
if not "%FIRST_RESULT%"=="0" exit /b %FIRST_RESULT%
exit /b %ERRORLEVEL%
