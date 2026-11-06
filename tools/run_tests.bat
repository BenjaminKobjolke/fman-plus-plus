@echo off
REM Run the whole fman_unittest suite in two processes: test*.py, then the
REM *_test.py files that need their own QApplication. Does not run fman_integrationtest.
setlocal
set ROOT=%~dp0..
set PYTHONPATH=%ROOT%\src\main\python;%ROOT%\src\unittest\python;%ROOT%\src\main\resources\base\Plugins\Core
echo Running unit test suite: test*.py
call "%~dp0unittest_with_timeout.bat" discover -v -s "%ROOT%\src\unittest\python" -t "%ROOT%\src\unittest\python" -p "test*.py" 2>&1
set "TESTRESULT=%ERRORLEVEL%"
echo Running unit test suite: *_test.py (tests that need their own QApplication)
call "%~dp0unittest_with_timeout.bat" discover -v -s "%ROOT%\src\unittest\python" -t "%ROOT%\src\unittest\python" -p "*_test.py" 2>&1
if "%TESTRESULT%"=="0" set "TESTRESULT=%ERRORLEVEL%"
exit /b %TESTRESULT%
