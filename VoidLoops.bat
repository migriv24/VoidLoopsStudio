@echo off
rem Void Loops Studio — launch the canvas UI (the prototype's front door).
rem Builds/opens the demo project and serves the node editor in your browser.
cd /d "%~dp0"
python -m voidloops --ui
pause
