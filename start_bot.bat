@echo off
REM ================================================================
REM Telegram Remote Dev Agent - Startup Script
REM Run this file to start the bot (or add it to Windows Startup folder)
REM ================================================================

cd /d "%~dp0"

echo [Telegram Remote Dev Agent] Starting...

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Start the bot
python main.py

REM Keep window open if bot crashes (shows error message)
echo.
echo [Bot stopped. Press any key to close...]
pause > nul
