@echo off
setlocal
set ROOT=%~dp0..
set PYTHONPATH=%ROOT%\src\main\python;%ROOT%\src\unittest\python
set QT_QPA_PLATFORM=offscreen
call "%~dp0unittest_with_timeout.bat" fman_unittest.impl.scripting_automation_test
set "FIRST_RESULT=%ERRORLEVEL%"
call "%~dp0unittest_with_timeout.bat" fman_unittest.impl.external_drop_test
set "DROP_RESULT=%ERRORLEVEL%"
call "%~dp0unittest_with_timeout.bat" fman_unittest.impl.pane_drag_test
set "PANE_DRAG_RESULT=%ERRORLEVEL%"
call "%~dp0unittest_with_timeout.bat" fman_unittest.impl.link_capture_test
set "SECOND_RESULT=%ERRORLEVEL%"
call "%~dp0unittest_with_timeout.bat" fman_unittest.impl.native_readout_test
if not "%FIRST_RESULT%"=="0" exit /b %FIRST_RESULT%
if not "%DROP_RESULT%"=="0" exit /b %DROP_RESULT%
if not "%PANE_DRAG_RESULT%"=="0" exit /b %PANE_DRAG_RESULT%
if not "%SECOND_RESULT%"=="0" exit /b %SECOND_RESULT%
exit /b %ERRORLEVEL%
