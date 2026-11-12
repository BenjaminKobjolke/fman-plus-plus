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
REM The tour chapters are ids 3-7 (TOUR_CHAPTERS in demo_scripts_tour.py,
REM "group": "tour" in fman.json).
set "IS_TOUR="
if %1 GEQ 3 if %1 LEQ 7 set "IS_TOUR=1"

REM Record against a throwaway fman profile, never the developer's own: their
REM third-party plugins prepend key bindings (so they'd beat Core's) and add
REM palette commands that change what a typed query resolves to. Dropping
REM Plugins/ each run also resets the persisted viewer zoom/volume, so a
REM re-recording matches the first one. Redirecting APPDATA would do it too,
REM but that is also where pip --user puts PyQt5 and fbs_runtime - hence
REM fman's own FMAN_DATA_DIRECTORY override.
set "FMAN_DATA_DIRECTORY=%TEMP%\fman-demo-profile"
REM Isolate the OS credential store too: profile isolation alone would still
REM read a signed-in recordist's real account and could sync their plugins/settings.
set "PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring"
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
set "SETTINGS_FILE=%FMAN_DATA_DIRECTORY%\Local\Settings.json"
if "%1"=="18" (
	REM A copied single_instance=false would make the plain launch open its own window.
	powershell -NoProfile -Command "$p=$env:SETTINGS_FILE; New-Item -ItemType Directory -Force -Path (Split-Path $p) | Out-Null; $s=if (Test-Path -LiteralPath $p) { Get-Content -Raw -LiteralPath $p | ConvertFrom-Json } else { [pscustomobject]@{} }; $s | Add-Member -NotePropertyName single_instance -NotePropertyValue $true -Force; [System.IO.File]::WriteAllText($p, ($s | ConvertTo-Json -Depth 20), [System.Text.UTF8Encoding]::new($false))"
)
if "%1"=="15" (
	REM A copied pane_location_bars_visible=false would make the first toggle show them.
	powershell -NoProfile -Command "$p=$env:SETTINGS_FILE; if (Test-Path -LiteralPath $p) { $s=Get-Content -Raw -LiteralPath $p | ConvertFrom-Json; $null=$s.PSObject.Properties.Remove('pane_location_bars_visible'); [System.IO.File]::WriteAllText($p, ($s | ConvertTo-Json -Depth 20), [System.Text.UTF8Encoding]::new($false)) }"
)
if defined IS_TOUR (
	REM The path line above each pane would put the scratch path on camera.
	REM $false, not false: a bare false is stored as the STRING "false", and
	REM window_chrome.py reads anything that is not False as visible.
	powershell -NoProfile -Command "$p=$env:SETTINGS_FILE; New-Item -ItemType Directory -Force -Path (Split-Path $p) | Out-Null; $s=if (Test-Path -LiteralPath $p) { Get-Content -Raw -LiteralPath $p | ConvertFrom-Json } else { [pscustomobject]@{} }; $s | Add-Member -NotePropertyName pane_location_bars_visible -NotePropertyValue $false -Force; [System.IO.File]::WriteAllText($p, ($s | ConvertTo-Json -Depth 20), [System.Text.UTF8Encoding]::new($false))"
)
REM A custom theme lives outside the bundled Themes dir, so mirror those too -
REM otherwise load_theme silently falls back to the default.
if exist "%APPDATA%\fman\Themes" (
	xcopy /e /i /q /y "%APPDATA%\fman\Themes" "%FMAN_DATA_DIRECTORY%\Themes\" >nul
)

REM The window is captured at 1920x1080, then the published tour is 1280px
REM wide and the standalone GIFs are narrower. Seed a demo-only Theme.css for
REM every recording so the text remains readable after composition.
REM The tour chapters (3-7) and the standalone feature/plugin clips need the
REM larger variant; all others use Core sizes at 1.5x. See
REM tools/create_media/demo_Theme*.css.
set "FONT_CSS=demo_Theme_default.css"
if defined IS_TOUR set "FONT_CSS=demo_Theme.css"
if "%1"=="8" set "FONT_CSS=demo_Theme.css"
if "%1"=="9" set "FONT_CSS=demo_Theme.css"
if "%1"=="10" set "FONT_CSS=demo_Theme.css"
if "%1"=="21" set "FONT_CSS=demo_Theme.css"
mkdir "%FMAN_DATA_DIRECTORY%\Plugins\User\DemoFont" 2>nul
copy /y "%CD%\tools\create_media\%FONT_CSS%" "%FMAN_DATA_DIRECTORY%\Plugins\User\DemoFont\Theme.css" >nul

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

REM Demo 17 needs the FTP plugin to connect to its local overwrite fixture.
if "%1"=="17" (
	if exist "%APPDATA%\fman\Plugins\User\FMAN_FTPClient" (
		xcopy /e /i /q /y "%APPDATA%\fman\Plugins\User\FMAN_FTPClient" "%FMAN_DATA_DIRECTORY%\Plugins\User\FMAN_FTPClient\" >nul
	) else (
		echo ERROR: FMAN_FTPClient is not installed in %APPDATA%\fman\Plugins\User - cannot record demo 17.
		exit /b 1
	)
)

REM Demo 16 uses a fake signed-in account and API; the null keyring above keeps
REM the real credential store out of the recording.
if "%1"=="16" xcopy /e /i /q /y "%CD%\tools\create_media\DemoAccount" "%FMAN_DATA_DIRECTORY%\Plugins\User\DemoAccount\" >nul

REM Demo 1 reads the committed examples. The tour chapters (id 3+) create,
REM rename, move and pack files, so they get a fresh scratch copy of both
REM example folders on the left and an empty folder on the right.
set "LEFT=%CD%\examples\left_pane"
set "RIGHT=%CD%\examples\right_pane"
REM Not %TEMP%: its path holds the Windows user name, and the Move, Copy and
REM Pack prompts show the scratch path on camera. Override with FMAN_DEMO_SCRATCH.
if not defined FMAN_DEMO_SCRATCH set "FMAN_DEMO_SCRATCH=D:\fman-demo"
if %1 GEQ 3 (
	set "LEFT=%FMAN_DEMO_SCRATCH%\%1-left"
	set "RIGHT=%FMAN_DEMO_SCRATCH%\%1-right"
	if exist "!LEFT!" rmdir /s /q "!LEFT!"
	if exist "!RIGHT!" rmdir /s /q "!RIGHT!"
	mkdir "!LEFT!"
	mkdir "!RIGHT!"
	REM Unlike %TEMP% the base can be missing; an empty pane would only show up as a wasted take.
	if not exist "!LEFT!" (
		echo ERROR: cannot create !LEFT! - set FMAN_DEMO_SCRATCH to a writable folder.
		exit /b 1
	)
	xcopy /q /y "%CD%\examples\left_pane\*" "!LEFT!\" >nul
	xcopy /q /y "%CD%\examples\right_pane\*" "!LEFT!\" >nul
)
if "%1"=="18" mkdir "%LEFT%\opened-by-new-instance"
if "%1"=="18" >"%LEFT%\opened-by-new-instance\demo.txt" echo Separate window
if "%1"=="18" mkdir "%LEFT%\forwarded-to-original"
if "%1"=="18" >"%LEFT%\forwarded-to-original\demo.txt" echo Forwarded launch

REM Demo 19 holds in-use.txt open so its copy fails and the end-of-copy retry question appears.
if "%1"=="19" mkdir "%LEFT%\retry-demo"
if "%1"=="19" >"%LEFT%\retry-demo\notes.txt" echo Copied fine
if "%1"=="19" >"%LEFT%\retry-demo\in-use.txt" echo Held open by another program
if "%1"=="19" set "LOCK_PID=%TEMP%\fman-demo-19-lock.pid"
if "%1"=="19" set "LOCKED_FILE=%LEFT%\retry-demo\in-use.txt"
if "%1"=="19" set "LOCK_READY=%TEMP%\fman-demo-19-lock.ready"
if "%1"=="19" if exist "%LOCK_PID%" (
	for /f %%p in (%LOCK_PID%) do taskkill /pid %%p /t /f >nul 2>nul
	del "%LOCK_PID%"
)
if "%1"=="19" if exist "%LOCK_READY%" del "%LOCK_READY%"
if "%1"=="19" powershell -NoProfile -Command "$p=Start-Process -WindowStyle Hidden -FilePath powershell -ArgumentList @('-NoProfile','-Command','$f=[IO.File]::Open($env:LOCKED_FILE,''Open'',''Read'',''None''); Set-Content -LiteralPath $env:LOCK_READY -Value ready; Start-Sleep 120') -PassThru; Set-Content -LiteralPath '%LOCK_PID%' -Value $p.Id; for($i=0; $i -lt 50 -and -not(Test-Path $env:LOCK_READY); $i++){ Start-Sleep -Milliseconds 100 }; if(-not(Test-Path $env:LOCK_READY)){ throw 'Demo file lock did not start' }"
if "%1"=="19" if errorlevel 1 (
	if exist "%LOCK_PID%" for /f %%p in (%LOCK_PID%) do taskkill /pid %%p /t /f >nul 2>nul
	if exist "%LOCK_PID%" del "%LOCK_PID%"
	if exist "%LOCK_READY%" del "%LOCK_READY%"
	exit /b 1
)

REM Demo 17 uploads this small site; site sorts first and contains the conflict.
if "%1"=="17" mkdir "%LEFT%\site\css" 2>nul
if "%1"=="17" >"%LEFT%\site\index.html" echo Demo site
if "%1"=="17" >"%LEFT%\site\about.html" echo About this demo
if "%1"=="17" >"%LEFT%\site\contact.html" echo Contact this demo
if "%1"=="17" >"%LEFT%\site\css\style.css" echo body { color: blue; }
if "%1"=="17" >"%LEFT%\site\css\print.css" echo @media print { body { color: black; } }
if "%1"=="17" set "FTP_SERVER_PID=%TEMP%\fman-demo-17-ftp.pid"
if "%1"=="17" if exist "%FTP_SERVER_PID%" (
	for /f %%p in (%FTP_SERVER_PID%) do taskkill /pid %%p /t /f >nul 2>nul
	del "%FTP_SERVER_PID%"
)
if "%1"=="17" powershell -NoProfile -Command "$p=Start-Process -FilePath '%FMAN_PYTHON%' -ArgumentList @('%CD%\tools\create_media\demo_ftp_server.py','%TEMP%\fman-demo-17-ftp') -PassThru; Set-Content -LiteralPath '%FTP_SERVER_PID%' -Value $p.Id"

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
REM The example files have no subfolders; the expanded tree still needs child rows.
if "%1"=="22" mkdir "%LEFT%\projects\alpha" 2>nul
if "%1"=="22" mkdir "%LEFT%\projects\beta" 2>nul
if "%1"=="22" mkdir "%LEFT%\reports" 2>nul
if "%1"=="22" mkdir "%LEFT%\archive" 2>nul
if "%1"=="8" set "SETTINGS_DIR=%FMAN_DATA_DIRECTORY%\Plugins\User\Settings"
if "%1"=="8" powershell -NoProfile -Command "$s=$env:SETTINGS_DIR; New-Item -ItemType Directory -Force -Path $s | Out-Null; $l=$env:LEFT; $p=Join-Path $l 'projects'; $h=[ordered]@{}; $h[$l]=5; $h[$p]=4; $h[(Join-Path $p 'alpha')]=3; $h[(Join-Path $p 'beta')]=2; $h[(Join-Path $l 'reports')]=1; [System.IO.File]::WriteAllText((Join-Path $s 'Visited Paths.json'), ($h | ConvertTo-Json))"

REM Chapter 9 (tail mode) needs a log that actually GROWS while the viewer is
REM open - a static file cannot show the view following the end. Append a line
REM every 1.5 s for 60 s in the background, then stop on its own.
if "%1"=="9" set "LOGFILE=%LEFT%\service.log"
if "%1"=="9" powershell -NoProfile -Command "1..12 | ForEach-Object { Add-Content -LiteralPath $env:LOGFILE -Value ('{0:HH:mm:ss}  service started, worker {1} ready' -f (Get-Date), $_) }"
if "%1"=="9" start "" /b powershell -NoProfile -Command "1..40 | ForEach-Object { Add-Content -LiteralPath $env:LOGFILE -Value ('{0:HH:mm:ss}  request {1} handled in {2} ms' -f (Get-Date), $_, (Get-Random -Minimum 4 -Maximum 90)); Start-Sleep -Milliseconds 1500 }"

REM Demo 12 films Edit link target, which is visible only on a link. A junction
REM needs no admin rights; a file symlink would.
if "%1"=="12" mklink /J "%LEFT%\linked-folder" "%RIGHT%" >nul
if "%1"=="12" powershell -NoProfile -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $env:LEFT 'readme shortcut.lnk')); $s.TargetPath=(Join-Path $env:LEFT 'readme.md'); $s.Save()"

REM Demo 15 needs a visible age spread in the scratch copy; the checked-in
REM example files share nearly identical timestamps, which would shade alike.
if "%1"=="15" powershell -NoProfile -Command "$ages=@(0,2,10,45,200,900); $i=0; Get-ChildItem -LiteralPath $env:LEFT -File | Sort-Object Name | ForEach-Object { $_.LastWriteTime=(Get-Date).AddDays(-$ages[$i]); $i++; if ($i -ge $ages.Count) { $i=0 } }"
if "%1"=="15" xcopy /q /y "%LEFT%\*" "%RIGHT%\" >nul
REM The restart still's child window is found by this folder in its title.
if "%1"=="15" mkdir "%LEFT%\after-restart" 2>nul

REM The desktop is cleared by the recording tool itself, before it starts this
REM launcher ("minimize_all" in its config, on by default): it enumerates the
REM top-level windows and minimizes each one, its own console included. A
REM leftover window would otherwise be burned into every frame - the capture is
REM a screen region - and while a script turns fman translucent, anything left
REM BEHIND it shows through too. Running fman by hand skips that; close what is
REM on screen.

"%FMAN_PYTHON%" src\main\python\fman\main.py ^
  --automation-demo %1 ^
  --automation-demo-port %2 ^
  --automation-demo-width %3 ^
  --automation-demo-height %4 ^
  "%LEFT%" "%RIGHT%"

if "%1"=="17" if exist "%FTP_SERVER_PID%" (
	for /f %%p in (%FTP_SERVER_PID%) do taskkill /pid %%p /t /f >nul 2>nul
	del "%FTP_SERVER_PID%"
)
if "%1"=="19" if exist "%LOCK_PID%" (
	for /f %%p in (%LOCK_PID%) do taskkill /pid %%p /t /f >nul 2>nul
	del "%LOCK_PID%"
)
if "%1"=="19" if exist "%LOCK_READY%" del "%LOCK_READY%"
