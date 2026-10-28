@echo off
REM Publish (or re-publish) the GitHub Release of a completed build.
REM Usage: github_release.bat [label]
REM   label  <version>_<build> of the installer in target\. Default: the label
REM          build_release.bat recorded in target\release_version.txt. Pass it only
REM          for an installer that was built before that record existed.
REM release_create.bat normally publishes by itself (its GitHub Release gate). This
REM is the retry path: it neither rebuilds nor bumps anything, and never reads the
REM current source version - that may have moved on since the build.
REM Requires the gh CLI, authenticated once via `gh auth login`. Idempotent: a
REM re-run re-uploads the asset (--clobber).
setlocal
set "ROOT=%~dp0.."
set "RECORD=%ROOT%\target\release_version.txt"

set "LABEL=%~1"
if not defined LABEL if exist "%RECORD%" for /f "usebackq delims=" %%L in ("%RECORD%") do set "LABEL=%%L"
if not defined LABEL (
    echo ERROR: no completed build recorded in %RECORD%.
    echo Run tools\release_create.bat, or pass the label of the installer in target\.
    exit /b 1
)

for %%I in ("%ROOT%\target\fmanSetup.exe") do set "ASSET=%%~fI"
for %%I in ("%ROOT%\target\fmanPortable.zip") do set "PORTABLE_ASSET=%%~fI"
for %%I in ("%ROOT%\release_notes\%LABEL%\en.json") do set "NOTES=%%~fI"

if not exist "%ASSET%" (
    echo ERROR: signed installer not found: %ASSET%
    exit /b 1
)
if not exist "%PORTABLE_ASSET%" (
    echo ERROR: portable archive not found: %PORTABLE_ASSET%
    exit /b 1
)
if not exist "%NOTES%" (
    echo ERROR: release notes not found: %NOTES%
    exit /b 1
)

REM gh creates a missing tag by itself - on the head of the remote default branch,
REM which is not the release commit while that is still unpushed.
call git -C "%ROOT%" ls-remote --exit-code --tags origin "refs/tags/%LABEL%" >nul 2>&1
if errorlevel 1 (
    echo ERROR: tag %LABEL% is not on origin. Commit, tag and push the release first.
    exit /b 1
)

echo Publishing %LABEL%
REM --repo is mandatory: cwd is release-tool's checkout, so gh would otherwise
REM infer release-tool's own remote instead of fman's.
REM The title mirrors title_format in release_create.ini - keep the two in sync.
cd /d D:\GIT\BenjaminKobjolke\release-tool
call uv run python -m release_tool github-release "%LABEL%" "%ASSET%" "%PORTABLE_ASSET%" --repo BenjaminKobjolke/fman --notes-json "%NOTES%" --title "fman++ %LABEL%"
set "RESULT=%ERRORLEVEL%"
cd /d "%~dp0"
if "%RESULT%"=="0" (
    echo Published GitHub Release: %LABEL%
) else (
    echo ERROR: GitHub Release publish failed for %LABEL%
)
endlocal & exit /b %RESULT%
