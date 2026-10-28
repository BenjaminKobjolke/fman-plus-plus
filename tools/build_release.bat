@echo off
REM Build the signed release installer (target\fmanSetup.exe) and record its label.
REM Called by release_create.bat (release-tool create), which owns the build bump,
REM translation and rollback - this bat only builds the version that is already set.
REM Ask a running fman to close first: freeze() cannot replace target\fman\ under it.
setlocal

set "ROOT=%~dp0.."
set "RECORD=%ROOT%\target\release_version.txt"

REM The build replaces target\fmanSetup.exe in place. Drop the old record first, so
REM a failed build cannot leave a stale label paired with a half-built installer.
if exist "%RECORD%" del "%RECORD%"

cd /d "%ROOT%"
REM Pick the interpreter that has fbs; see find_build_python.bat for why.
call "%~dp0find_build_python.bat"
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" goto :done

REM A fman started from target\fman locks the files freeze() replaces.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0close_running_fman.ps1" -Directory "%ROOT%\target\fman" <NUL
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" goto :done

call "%FMAN_PYTHON%" build.py release_build
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" goto :done

if not exist "target\fmanSetup.exe" (
    echo ERROR: build reported success but target\fmanSetup.exe is missing.
    set "RESULT=1"
    goto :done
)

if not exist "target\fmanPortable.zip" (
    echo ERROR: build reported success but target\fmanPortable.zip is missing.
    set "RESULT=1"
    goto :done
)

REM Recorded only now: github_release.bat publishes this label, not whatever
REM base.json holds by the time it runs.
"%FMAN_PYTHON%" tools\release\build_number.py label > "%RECORD%"
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" del "%RECORD%"

:done
cd /d "%~dp0"
endlocal & exit /b %RESULT%
