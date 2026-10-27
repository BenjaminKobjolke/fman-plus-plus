@echo off
REM Run the file list view's row height tests (UniformRowHeights keeping the
REM Fixed vertical header in step with its row height).
REM Excluded from `python build.py test` - hence the *_test.py name, which its
REM discovery does not match - because they need a QApplication of their own
REM and leftover Qt state is what makes that suite hang. See CLAUDE.md.
REM Offscreen, so no window appears.
setlocal
set ROOT=%~dp0..
set PYTHONPATH=%ROOT%\src\main\python;%ROOT%\src\unittest\python
call "%~dp0unittest_with_timeout.bat" -v fman_unittest.impl.view.uniform_row_heights_test fman_unittest.impl.view.selection_test
exit /b %ERRORLEVEL%
