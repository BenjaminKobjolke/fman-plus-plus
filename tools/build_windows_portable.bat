@REM Local test build: freeze, then target\fmanPortable.zip. No installer, signing or release.
call "%~dp0build_windows.bat"
@set "RESULT=%ERRORLEVEL%"
@if not "%RESULT%"=="0" goto :done
@REM build_windows.bat leaves the cwd in tools\; portable_zip resolves paths from the root.
cd "%~dp0.."
call "%FMAN_PYTHON%" build.py portable_zip
@set "RESULT=%ERRORLEVEL%"
:done
cd "%~dp0"
@exit /b %RESULT%
