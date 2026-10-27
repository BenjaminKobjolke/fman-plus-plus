@echo off
REM Run the theme engine's tests (fman_unittest.impl.test_themes /
REM test_theme / test_fonts / test_background). Excluded from
REM `python build.py test` on
REM purpose: that also runs fman_integrationtest, which has a known
REM intermittent hang - see
REM CLAUDE.md. Fast feedback when touching colors, styles.qss or Theme.css.
setlocal
set ROOT=%~dp0..
set PYTHONPATH=%ROOT%\src\main\python;%ROOT%\src\unittest\python
call "%~dp0unittest_with_timeout.bat" -v ^
	fman_unittest.impl.test_themes fman_unittest.impl.test_theme ^
	fman_unittest.impl.test_fonts fman_unittest.impl.test_background
exit /b %ERRORLEVEL%
