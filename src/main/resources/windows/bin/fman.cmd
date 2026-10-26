@echo off
rem start: return to the prompt instead of waiting for the GUI app.
if "%~1"=="" (start "" "%~dp0..\fman.exe" .) else (start "" "%~dp0..\fman.exe" %*)
