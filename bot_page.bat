@echo off
REM Start the bot web page and open it in the browser (password: logs\web_password.txt).
cd /d "%~dp0"
REM Open the browser a moment after the server starts: it isn't listening yet otherwise.
start "" /b cmd /c "ping -n 3 127.0.0.1 >nul & start "" http://127.0.0.1:8765"
"%USERPROFILE%\miniconda3\envs\d2r\python.exe" -m bot.web
