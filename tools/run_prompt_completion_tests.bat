@echo off
REM Run prompt Tab-completion tests in an isolated offscreen QApplication.
setlocal
set ROOT=%~dp0..
set PYTHONPATH=%ROOT%\src\main\python;%ROOT%\src\unittest\python
call "%~dp0unittest_with_timeout.bat" -v fman_unittest.impl.prompt_completion_test
exit /b %ERRORLEVEL%
