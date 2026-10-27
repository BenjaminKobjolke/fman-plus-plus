@echo off
REM Drive the automated-application-screenshots tool against fman's config.
REM Runs the tool from its own repo; output lands in fman's own media\demos\
REM (see output_dir in tools\create_media\fman.json).
REM
REM Every argument passes straight through to the tool, so this one file covers
REM recording, composing and inspecting.
REM
REM Prereq (once): uv sync --group demos
REM   and, for the tour only, npm install in <tool-repo>\composer
REM
REM Usage: tools\demos_record.bat                        (records every demo)
REM        tools\demos_record.bat --demo 3               (one demo)
REM        tools\demos_record.bat --compose              (build all four artifacts)
REM        tools\demos_record.bat --compose features     (build one)
REM        tools\demos_record.bat --demo all --compose   (record, then build)
REM        tools\demos_record.bat --list                 (what this config can do)
setlocal
set "TOOL_DIR=D:\GIT\BenjaminKobjolke\automated-application-screenshots"
set "CONFIG=%~dp0create_media\fman.json"
if "%~1"=="" (set "DEMO_ARGS=--demo all") else (set "DEMO_ARGS=%*")
cd /d "%TOOL_DIR%" || (echo Tool repo not found: %TOOL_DIR% & exit /b 1)
uv run screenshot-tool --config "%CONFIG%" %DEMO_ARGS%
set "RESULT=%ERRORLEVEL%"
REM The pause is for double-clicking this file. FMAN_NO_PAUSE or a Tickets
REM Watcher command run skips it, including when reached through call.
if not defined FMAN_NO_PAUSE if not "%TICKETS_WATCHER_COMMAND_RUN%"=="1" pause
exit /b %RESULT%
