@echo off
REM Run the tutorial Overlay's keyboard tests (focus, arrow keys, Enter).
REM Excluded from `python build.py test` - hence the *_test.py name, which its
REM discovery does not match - because they need a QApplication of their own
REM and leftover Qt state is what makes that suite hang. See CLAUDE.md.
REM Offscreen, so no window appears.
setlocal
set ROOT=%~dp0..
set PYTHONPATH=%ROOT%\src\main\python;%ROOT%\src\unittest\python
call "%~dp0unittest_with_timeout.bat" -v fman_unittest.impl.overlay_focus_test
exit /b %ERRORLEVEL%
