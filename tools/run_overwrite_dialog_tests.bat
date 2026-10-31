@echo off
setlocal
set ROOT=%~dp0..
set PYTHONPATH=%ROOT%\src\main\python;%ROOT%\src\unittest\python
call "%~dp0unittest_with_timeout.bat" -v fman_unittest.impl.overwrite_dialog_test
exit /b %ERRORLEVEL%
