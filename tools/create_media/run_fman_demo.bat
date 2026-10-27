@echo off
REM Launch fman in demo mode for the automated-application-screenshots tool.
REM Not a Tickets Watcher command: started by the recording tool with 4 arguments; the demo 9 log writer uses start without /wait on purpose.
REM `python build.py run` (fbs) does not forward CLI args, so we launch the
REM main module directly the way fbs run does: PYTHONPATH=src\main\python.
REM
REM The tool starts this via `uv run`, which puts ITS virtualenv first on PATH
REM (that venv has neither fbs_runtime nor PyQt5). Drop it and run fman's own
REM .venv (tools\find_build_python.bat). Override with FMAN_PYTHON.
REM Args from the tool: %1=demo id  %2=port  %3=width  %4=height
setlocal enabledelayedexpansion
if defined VIRTUAL_ENV call set "PATH=%%PATH:%VIRTUAL_ENV%\Scripts;=%%"
set "VIRTUAL_ENV="
call "%~dp0..\find_build_python.bat"
if errorlevel 1 exit /b 1
cd /d "%~dp0..\.."
set "PYTHONPATH=%CD%\src\main\python"

REM Record against a throwaway fman profile, never the developer's own: their
REM third-party plugins prepend key bindings (so they'd beat Core's) and add
REM palette commands that change what a typed query resolves to. Dropping
REM Plugins/ each run also resets the persisted viewer zoom/volume, so a
REM re-recording matches the first one. Redirecting APPDATA would do it too,
REM but that is also where pip --user puts PyQt5 and fbs_runtime - hence
REM fman's own FMAN_DATA_DIRECTORY override.
set "FMAN_DATA_DIRECTORY=%TEMP%\fman-demo-profile"
if exist "%FMAN_DATA_DIRECTORY%\Plugins" rmdir /s /q "%FMAN_DATA_DIRECTORY%\Plugins"
if not exist "%FMAN_DATA_DIRECTORY%\Local\libmpv" mkdir "%FMAN_DATA_DIRECTORY%\Local\libmpv"
REM Without a cached libmpv the first video view downloads ~100 MB behind a
REM progress dialog - on camera. Reuse the real profile's copy instead.
if not exist "%FMAN_DATA_DIRECTORY%\Local\libmpv\libmpv-2.dll" (
	if exist "%APPDATA%\fman\Local\libmpv\libmpv-2.dll" (
		copy /y "%APPDATA%\fman\Local\libmpv\libmpv-2.dll" "%FMAN_DATA_DIRECTORY%\Local\libmpv\" >nul
	) else (
		echo WARNING: no cached libmpv-2.dll - a video demo would record its download.
	)
)

REM ...but DO record in the developer's theme: a demo showing Monokai when the
REM screenshots elsewhere show their actual theme looks like a different app.
REM The theme lives in plain Local\Settings.json (fman reads it before the
REM plugin system exists), so copying that one file brings the look across
REM without any plugin or key binding. The window_opacity in it is ignored:
REM demo mode pins DEMO_OPACITY so every chapter records at a known value.
if exist "%APPDATA%\fman\Local\Settings.json" (
	copy /y "%APPDATA%\fman\Local\Settings.json" "%FMAN_DATA_DIRECTORY%\Local\" >nul
)
REM A custom theme lives outside the bundled Themes dir, so mirror those too -
REM otherwise load_theme silently falls back to the default.
if exist "%APPDATA%\fman\Themes" (
	xcopy /e /i /q /y "%APPDATA%\fman\Themes" "%FMAN_DATA_DIRECTORY%\Themes\" >nul
)

REM The standalone clips are encoded into GIFs narrower than this 1280px
REM capture - 800px for the feature-* ones, less for the plugin-* ones - so
REM the whole UI lands at 0.625x or less in the README, and Core 9pt reads as
REM ~5.6pt there. Drop in a demo-only Theme.css that bumps the font sizes;
REM user plugins load after Core and Theme keeps load order, so it wins.
REM Ids 8-10 only: the tour chapters are published at full 1280 width and stay
REM legible without it. See tools/create_media/demo_Theme.css.
if "%1"=="8" set "FONT_CSS=1"
if "%1"=="9" set "FONT_CSS=1"
if "%1"=="10" set "FONT_CSS=1"
if defined FONT_CSS (
	mkdir "%FMAN_DATA_DIRECTORY%\Plugins\User\DemoFont" 2>nul
	copy /y "%CD%\tools\create_media\demo_Theme.css" "%FMAN_DATA_DIRECTORY%\Plugins\User\DemoFont\Theme.css" >nul
)

REM Demo 10 films a THIRD-PARTY plugin, so the one plugin under test has to go
REM back into the tree the rmdir above just emptied. Only that one: seeding all
REM of %APPDATA%\fman\Plugins would put the recordist key bindings (which are
REM prepended, so they beat Core) and their palette commands into the take -
REM exactly what the wipe exists to prevent. MatrixRain itself is safe to seed:
REM its Key Bindings.json is [] by design, so it steals no chord.
REM A missing plugin is fatal, not a warning: the take would look perfectly
REM fine and show fman WITHOUT the plugin, every palette query matching nothing.
if "%1"=="10" (
	if exist "%APPDATA%\fman\Plugins\User\MatrixRain" (
		xcopy /e /i /q /y "%APPDATA%\fman\Plugins\User\MatrixRain" "%FMAN_DATA_DIRECTORY%\Plugins\User\MatrixRain\" >nul
	) else (
		echo ERROR: MatrixRain is not installed in %APPDATA%\fman\Plugins\User - cannot record demo 10.
		exit /b 1
	)
)

REM Demo 1 reads the committed examples. The tour chapters (id 3+) create,
REM rename, move and pack files, so they get a fresh scratch copy of both
REM example folders on the left and an empty folder on the right.
set "LEFT=%CD%\examples\left_pane"
set "RIGHT=%CD%\examples\right_pane"
if %1 GEQ 3 (
	set "LEFT=%TEMP%\fman-demo-%1-left"
	set "RIGHT=%TEMP%\fman-demo-%1-right"
	if exist "!LEFT!" rmdir /s /q "!LEFT!"
	if exist "!RIGHT!" rmdir /s /q "!RIGHT!"
	mkdir "!LEFT!"
	mkdir "!RIGHT!"
	xcopy /q /y "%CD%\examples\left_pane\*" "!LEFT!\" >nul
	xcopy /q /y "%CD%\examples\right_pane\*" "!LEFT!\" >nul
)

REM Demo 10 turns the rain translucent, and what shows through is the file
REM list underneath - so the right pane cannot be the empty one it gets above.
if "%1"=="10" xcopy /q /y "%CD%\examples\right_pane\*" "%RIGHT%\" >nul

REM Chapter 8 (Go to) jumps around a small folder tree, and seeds this run
REM with its OWN Visited Paths.json. Both matter: SuggestLocations falls back
REM to the home directory subdirs when it finds 2 or fewer visited paths, and
REM it queries the Windows Search index once a query is longer than two chars
REM - either would put the recordist private folders on camera.
if "%1"=="8" mkdir "%LEFT%\projects\alpha" 2>nul
if "%1"=="8" mkdir "%LEFT%\projects\beta" 2>nul
if "%1"=="8" mkdir "%LEFT%\reports" 2>nul
if "%1"=="8" set "SETTINGS_DIR=%FMAN_DATA_DIRECTORY%\Plugins\User\Settings"
if "%1"=="8" powershell -NoProfile -Command "$s=$env:SETTINGS_DIR; New-Item -ItemType Directory -Force -Path $s | Out-Null; $l=$env:LEFT; $p=Join-Path $l 'projects'; $h=[ordered]@{}; $h[$l]=5; $h[$p]=4; $h[(Join-Path $p 'alpha')]=3; $h[(Join-Path $p 'beta')]=2; $h[(Join-Path $l 'reports')]=1; [System.IO.File]::WriteAllText((Join-Path $s 'Visited Paths.json'), ($h | ConvertTo-Json))"

REM Chapter 9 (tail mode) needs a log that actually GROWS while the viewer is
REM open - a static file cannot show the view following the end. Append a line
REM every 1.5 s for 60 s in the background, then stop on its own.
if "%1"=="9" set "LOGFILE=%LEFT%\service.log"
if "%1"=="9" powershell -NoProfile -Command "1..12 | ForEach-Object { Add-Content -LiteralPath $env:LOGFILE -Value ('{0:HH:mm:ss}  service started, worker {1} ready' -f (Get-Date), $_) }"
if "%1"=="9" start "" /b powershell -NoProfile -Command "1..40 | ForEach-Object { Add-Content -LiteralPath $env:LOGFILE -Value ('{0:HH:mm:ss}  request {1} handled in {2} ms' -f (Get-Date), $_, (Get-Random -Minimum 4 -Maximum 90)); Start-Sleep -Milliseconds 1500 }"

REM The desktop is cleared by the recording tool itself, before it starts this
REM launcher ("minimize_all" in its config, on by default): it enumerates the
REM top-level windows and minimizes each one, its own console included. A
REM leftover window would otherwise be burned into every frame - the capture is
REM a screen region - and at DEMO_OPACITY 0.8 anything left BEHIND fman shows
REM through it too. Running fman by hand skips that; close what is on screen.

"%FMAN_PYTHON%" src\main\python\fman\main.py ^
  --automation-demo %1 ^
  --automation-demo-port %2 ^
  --automation-demo-width %3 ^
  --automation-demo-height %4 ^
  "%LEFT%" "%RIGHT%"
