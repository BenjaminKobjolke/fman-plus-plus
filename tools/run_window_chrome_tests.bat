@echo off
REM Run the window chrome and widget tests (fman_unittest.impl.
REM test_window_chrome, .test_widgets). Excluded from `python build.py test`
REM for the same reason as run_theme_tests.bat - see CLAUDE.md. Fast feedback
REM when touching window_chrome.py, MainWindow's title/menu/status bar setters
REM or the tutorial Overlay's placement.
setlocal
set ROOT=%~dp0..
set PYTHONPATH=%ROOT%\src\main\python;%ROOT%\src\unittest\python
call "%~dp0unittest_with_timeout.bat" -v ^
	fman_unittest.impl.test_window_chrome ^
	fman_unittest.impl.test_widgets
exit /b %ERRORLEVEL%
