@echo off
REM Run the zip/7-Zip and RAR filesystem tests, excluded from `python build.py test`
REM because they spawn 7-Zip as a real subprocess and can hang under AV/EDR
REM interference or resource contention.
setlocal
set ROOT=%~dp0..
set PYTHONPATH=%ROOT%\src\main\python;%ROOT%\src\unittest\python
call "%~dp0unittest_with_timeout.bat" discover -v -p "*_test.py" ^
	-s "%ROOT%\src\main\resources\base\Plugins\Core\core\tests\fs" ^
	-t "%ROOT%\src\main\resources\base\Plugins\Core"
exit /b %ERRORLEVEL%
