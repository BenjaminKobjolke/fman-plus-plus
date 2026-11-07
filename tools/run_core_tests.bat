@echo off
REM Run only the Core plugin's own tests (core/tests/**), skipping the
REM fbs-default fman_unittest/fman_integrationtest suites and the isolated
REM zip tests (see run_zip_tests.bat). Fast, reliable feedback loop for
REM day-to-day feature work in the Core plugin. Pass a dotted module name to
REM run only that module, e.g. core.tests.fs.test_drives.
setlocal
set ROOT=%~dp0..
set PYTHONPATH=%ROOT%\src\main\python;%ROOT%\src\unittest\python;%ROOT%\src\main\resources\base\Plugins\Core
if not "%~1"=="" goto focused
echo Running Core test suite: discovering Core tests...
call "%~dp0unittest_with_timeout.bat" discover -v ^
	-s "%ROOT%\src\main\resources\base\Plugins\Core\core" ^
	-t "%ROOT%\src\main\resources\base\Plugins\Core"
exit /b %ERRORLEVEL%

:focused
echo Running Core test module: %*
call "%~dp0unittest_with_timeout.bat" -v %*
exit /b %ERRORLEVEL%
