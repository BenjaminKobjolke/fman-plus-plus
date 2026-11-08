@echo off
REM Run quicksearch resize, elision and persistence tests.
setlocal
set ROOT=%~dp0..
set PYTHONPATH=%ROOT%\src\main\python;%ROOT%\src\unittest\python
call "%~dp0unittest_with_timeout.bat" -v fman_unittest.impl.quicksearch_test
if errorlevel 1 exit /b %ERRORLEVEL%
call "%~dp0unittest_with_timeout.bat" -v fman_unittest.impl.test_quicksearch_height
if errorlevel 1 exit /b %ERRORLEVEL%
call "%~dp0unittest_with_timeout.bat" -v fman_unittest.impl.test_quicksearch_width
exit /b %ERRORLEVEL%
