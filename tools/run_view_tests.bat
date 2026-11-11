@echo off
REM Run the file list view tests that own a QApplication.
REM Excluded from `python build.py test` - hence the *_test.py name, which its
REM discovery does not match - because they need a QApplication of their own
REM and leftover Qt state is what makes that suite hang. See CLAUDE.md.
REM Offscreen, so no window appears.
setlocal
set ROOT=%~dp0..
set PYTHONPATH=%ROOT%\src\main\python;%ROOT%\src\unittest\python
call "%~dp0unittest_with_timeout.bat" -v fman_unittest.impl.view.uniform_row_heights_test fman_unittest.impl.view.selection_test fman_unittest.impl.view.scroll_margin_test fman_unittest.impl.view.right_button_selection_test fman_unittest.impl.view.drag_range_selection_test fman_unittest.impl.view.compact_view_test fman_unittest.impl.view.pane_view_mode_test fman_unittest.impl.view.column_widths_test fman_unittest.impl.view.header_sort_arrow_test fman_unittest.impl.view.location_bar_test
exit /b %ERRORLEVEL%
