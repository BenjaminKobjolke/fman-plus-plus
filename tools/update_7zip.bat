@echo off
REM Download and re-vendor the official 7-Zip binaries for all platforms.
REM When SEVEN_ZIP_VERSION changes, update the version and matching source URL
REM in src\main\resources\base\LICENSE as well.
setlocal
set "SEVEN_ZIP_VERSION=2600"
set "ROOT=%~dp0.."
set "WORK=%TEMP%\fman-7zip-%RANDOM%-%RANDOM%"
set "RESULT=0"
pushd "%ROOT%"
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" goto :failed
mkdir "%WORK%"
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" goto :failed
mkdir "%WORK%\windows"
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" goto :failed
mkdir "%WORK%\mac"
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" goto :failed
mkdir "%WORK%\linux"
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" goto :failed

curl.exe -fL "https://www.7-zip.org/a/7z%SEVEN_ZIP_VERSION%-x64.exe" -o "%WORK%\7z-windows.exe"
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" goto :failed
curl.exe -fL "https://www.7-zip.org/a/7zr.exe" -o "%WORK%\7zr.exe"
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" goto :failed
curl.exe -fL "https://www.7-zip.org/a/7z%SEVEN_ZIP_VERSION%-mac.tar.xz" -o "%WORK%\7z-mac.tar.xz"
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" goto :failed
curl.exe -fL "https://www.7-zip.org/a/7z%SEVEN_ZIP_VERSION%-linux-x64.tar.xz" -o "%WORK%\7z-linux.tar.xz"
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" goto :failed

"%WORK%\7zr.exe" x "%WORK%\7z-windows.exe" -o"%WORK%\windows" -y
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" goto :failed
tar.exe -xf "%WORK%\7z-mac.tar.xz" -C "%WORK%\mac"
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" goto :failed
tar.exe -xf "%WORK%\7z-linux.tar.xz" -C "%WORK%\linux"
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" goto :failed

set "BIN=src\main\resources\base\Plugins\Core\bin"
copy /y "%WORK%\windows\7z.exe" "%BIN%\windows\7z.exe"
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" goto :failed
copy /y "%WORK%\windows\7z.dll" "%BIN%\windows\7z.dll"
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" goto :failed
copy /y "%WORK%\windows\License.txt" "%BIN%\windows\License.txt"
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" goto :failed
if exist "%BIN%\windows\7za.exe" del /q "%BIN%\windows\7za.exe"
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" goto :failed

copy /y "%WORK%\mac\7zz" "%BIN%\mac\7zz"
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" goto :failed
copy /y "%WORK%\windows\License.txt" "%BIN%\mac\License.txt"
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" goto :failed
if exist "%BIN%\mac\7za" del /q "%BIN%\mac\7za"
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" goto :failed

copy /y "%WORK%\linux\7zz" "%BIN%\linux\7zz"
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" goto :failed
copy /y "%WORK%\windows\License.txt" "%BIN%\linux\License.txt"
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" goto :failed
if exist "%BIN%\linux\7za" del /q "%BIN%\linux\7za"
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" goto :failed

git add -A -- "%BIN%"
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" goto :failed
git update-index --chmod=+x "%BIN%/mac/7zz" "%BIN%/linux/7zz"
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" goto :failed
rmdir /s /q "%WORK%"
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" goto :failed
echo Update src\main\resources\base\LICENSE with version %SEVEN_ZIP_VERSION% and its matching source URL whenever SEVEN_ZIP_VERSION changes.
popd
exit /b 0

:failed
if "%RESULT%"=="0" set "RESULT=1"
if exist "%WORK%" rmdir /s /q "%WORK%"
popd
exit /b %RESULT%
