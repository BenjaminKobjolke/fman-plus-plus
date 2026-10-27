@echo off
REM Run ProgressDialog and ToolWindows tests (pass one unittest module to run just that file).
REM Excluded from `python build.py test` - hence the *_test.py name, which its
REM discovery does not match - because they need a QApplication of their own
REM and leftover Qt state is what makes that suite hang. See CLAUDE.md.
REM Offscreen, so no window appears.
setlocal
set ROOT=%~dp0..
set PYTHONPATH=%ROOT%\src\main\python;%ROOT%\src\unittest\python
if not "%1"=="" (
	call "%~dp0unittest_with_timeout.bat" -v %1
	exit /b %ERRORLEVEL%
)
call "%~dp0unittest_with_timeout.bat" -v fman_unittest.impl.progress_dialog_test
if errorlevel 1 exit /b %ERRORLEVEL%
call "%~dp0unittest_with_timeout.bat" -v fman_unittest.impl.tool_windows_test
exit /b %ERRORLEVEL%
