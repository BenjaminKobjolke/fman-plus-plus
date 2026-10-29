@echo off
REM Rebuild windrop.exe from the windrop repo and re-vendor it into
REM src\main\resources\base\Plugins\Core\bin\windows, next to 7z.exe. The exe
REM is committed on purpose: "Drag to last used app" launches it, and building
REM fman must not need Visual Studio. Set WINDROP_DIR when the windrop repo is
REM not a sibling of this one.
setlocal
if not defined WINDROP_DIR set "WINDROP_DIR=%~dp0..\..\windrop"
if not exist "%WINDROP_DIR%\tools\build.bat" (
    echo windrop repo not found at %WINDROP_DIR% - set WINDROP_DIR.
    exit /b 1
)
call "%WINDROP_DIR%\tools\build.bat"
if errorlevel 1 exit /b %ERRORLEVEL%
copy /y "%WINDROP_DIR%\build\Release\windrop.exe" "%~dp0..\src\main\resources\base\Plugins\Core\bin\windows\windrop.exe"
exit /b %ERRORLEVEL%
