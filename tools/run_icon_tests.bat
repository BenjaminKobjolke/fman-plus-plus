@echo off
REM Run the icon set tests (fman_unittest.impl.model.test_icon_set /
REM test_icon_provider / test_icon_tint). Excluded from `python build.py
REM test` for the same reason as run_theme_tests.bat - see CLAUDE.md. Fast
REM feedback when touching icon_set.py, icon_provider.py, icon_tint.py or
REM the vendored Material set.
REM
REM test_table is in here for the icon generation: it is what makes a new
REM set or color actually reach the panes (table.py, Row#__eq__).
setlocal
set ROOT=%~dp0..
set PYTHONPATH=%ROOT%\src\main\python;%ROOT%\src\unittest\python
call "%~dp0unittest_with_timeout.bat" -v ^
	fman_unittest.impl.model.test_icon_set ^
	fman_unittest.impl.model.test_icon_provider ^
	fman_unittest.impl.model.test_icon_tint ^
	fman_unittest.impl.model.test_table
exit /b %ERRORLEVEL%
