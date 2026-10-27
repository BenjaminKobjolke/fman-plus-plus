@echo off
REM Re-vendor fman's bundled font families into
REM src\main\resources\base\Plugins\Core\Fonts from Google Fonts. Their
REM output is committed on purpose: fman must not need the network to draw
REM text. Pass --family "Fira Code" to refresh a single family.
setlocal
call "%~dp0find_build_python.bat"
if errorlevel 1 exit /b 1
"%FMAN_PYTHON%" "%~dp0fetch_google_fonts.py" %*
exit /b %ERRORLEVEL%
