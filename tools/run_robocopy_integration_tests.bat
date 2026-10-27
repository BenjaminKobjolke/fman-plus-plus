@echo off
REM Runs real robocopy.exe; excluded from unit discovery because AV/EDR can stall child processes.
setlocal
set ROOT=%~dp0..
set PYTHONPATH=%ROOT%\src\main\python;%ROOT%\src\main\resources\base\Plugins\Robocopy
call "%~dp0unittest_with_timeout.bat" discover -v -p "robocopy*integration_test.py" ^
	-s "%ROOT%\src\main\resources\base\Plugins\Robocopy\robocopy_plugin\tests"
exit /b %ERRORLEVEL%
