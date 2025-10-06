@echo off
REM Set your Telegram credentials here
set TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN_HERE
set TELEGRAM_CHAT_ID=YOUR_CHAT_ID_HERE

REM Run the automation
.venv\Scripts\python.exe alt_triggered_automation.py

pause
