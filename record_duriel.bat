@echo off
REM Record one Duriel run: town -> Canyon -> true tomb -> kill. F9 = new area, F10 = done, F12 = stop.
cd /d "%~dp0"
"%USERPROFILE%\miniconda3\envs\d2r\python.exe" tools\record_route.py --duriel --players 1
pause
