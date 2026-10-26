@echo off
rem Call fman's scripting API from cmd, using the curl.exe that ships with Windows 10+.
rem
rem Usage:
rem   fman_api.bat state
rem   fman_api.bat commands
rem   fman_api.bat command move_cursor_down
rem   fman_api.bat open C:\Windows
rem
rem Set FMAN_API_URL to override the default http://127.0.0.1:47447.
setlocal

if "%FMAN_API_URL%"=="" set "FMAN_API_URL=http://127.0.0.1:47447"
set "TOKEN_FILE=%APPDATA%\fman\Local\ScriptingApiToken.txt"
if not exist "%TOKEN_FILE%" (
    echo No token file at %TOKEN_FILE%. Run "Toggle scripting API" in fman first.
    exit /b 1
)
set /p TOKEN=<"%TOKEN_FILE%"
set CURL=curl.exe -sS --fail-with-body -H "Authorization: Bearer %TOKEN%"

if /i "%~1"=="state" goto state
if /i "%~1"=="commands" goto commands
if /i "%~1"=="command" goto command
if /i "%~1"=="open" goto open
echo Usage: %~nx0 state ^| commands ^| command ^<name^> ^| open ^<folder^>
exit /b 1

:state
%CURL% "%FMAN_API_URL%/v1/state"
goto done

:commands
%CURL% "%FMAN_API_URL%/v1/commands"
goto done

:command
if "%~2"=="" (
    echo Usage: %~nx0 command ^<name^>
    exit /b 1
)
%CURL% -H "Content-Type: application/json" -d "{\"name\":\"%~2\"}" "%FMAN_API_URL%/v1/command"
goto done

:open
if "%~2"=="" (
    echo Usage: %~nx0 open ^<folder^>
    exit /b 1
)
rem fman URLs use forward slashes: C:\Windows becomes file://C:/Windows
set "FOLDER=%~f2"
set "FOLDER=%FOLDER:\=/%"
%CURL% -H "Content-Type: application/json" -d "{\"name\":\"open_directory\",\"args\":{\"url\":\"file://%FOLDER%\"}}" "%FMAN_API_URL%/v1/command"
goto done

:done
set RESULT=%ERRORLEVEL%
echo.
exit /b %RESULT%
