@echo off
REM Run the pane model's tests (fman_unittest.impl.model.test_model /
REM test_record_files / test_table / test_diff / test_worker). Excluded from `python build.py test` for the same
REM reason as run_theme_tests.bat - see CLAUDE.md. Fast feedback when touching
REM sorted_table.py, record_files.py or model.py: the sort order of a pane and
REM where an added / renamed / changed row is inserted into it.
setlocal
set ROOT=%~dp0..
set PYTHONPATH=%ROOT%\src\main\python;%ROOT%\src\unittest\python
call "%~dp0unittest_with_timeout.bat" -v ^
	fman_unittest.impl.model.test_model ^
	fman_unittest.impl.model.test_record_files ^
	fman_unittest.impl.model.test_table ^
	fman_unittest.impl.model.test_diff ^
	fman_unittest.impl.model.test_worker
exit /b %ERRORLEVEL%
