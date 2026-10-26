@echo off
setlocal
set ROOT=%~dp0..
set PYTHONPATH=%ROOT%\src\main\python;%ROOT%\src\unittest\python
set QT_QPA_PLATFORM=offscreen
call "%~dp0unittest_with_timeout.bat" fman_unittest.impl.scripting_automation_test
exit /b %ERRORLEVEL%
