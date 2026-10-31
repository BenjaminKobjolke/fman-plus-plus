@echo off
REM Run the in-window dialog focus, resize and cancellation tests.
REM Excluded from `python build.py test` because they own a QApplication.
setlocal
set ROOT=%~dp0..
set PYTHONPATH=%ROOT%\src\main\python;%ROOT%\src\unittest\python
call "%~dp0unittest_with_timeout.bat" -v fman_unittest.impl.in_window_dialog_test
exit /b %ERRORLEVEL%
