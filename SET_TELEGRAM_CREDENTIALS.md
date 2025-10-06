# How to Set Telegram Environment Variables

## Method 1: PowerShell (Recommended)

If you're using PowerShell (the default terminal in VS Code):

```powershell
# Set environment variables for current session
$env:TELEGRAM_BOT_TOKEN = "your_bot_token_here"
$env:TELEGRAM_CHAT_ID = "your_chat_id_here"

# Verify they are set
echo $env:TELEGRAM_BOT_TOKEN
echo $env:TELEGRAM_CHAT_ID

# Run the automation in the same PowerShell window
python alt_triggered_automation.py
```

## Method 2: Command Prompt (CMD)

If you're using Command Prompt (cmd.exe):

```cmd
set TELEGRAM_BOT_TOKEN=your_bot_token_here
set TELEGRAM_CHAT_ID=your_chat_id_here

REM Verify they are set
echo %TELEGRAM_BOT_TOKEN%
echo %TELEGRAM_CHAT_ID%

REM Run the automation in the same CMD window
python alt_triggered_automation.py
```

## Method 3: Set in Python Script (Easiest)

Create a file called `set_credentials.py`:

```python
import os

# Set your credentials here
os.environ['TELEGRAM_BOT_TOKEN'] = 'your_bot_token_here'
os.environ['TELEGRAM_CHAT_ID'] = 'your_chat_id_here'

print("Credentials set successfully!")
```

Then run:
```bash
python set_credentials.py
python alt_triggered_automation.py
```

## Method 4: Modify telegram_message.py Directly (Quick & Dirty)

**NOT RECOMMENDED for security, but works for testing:**

Edit `telegram_message.py` and replace:

```python
# FROM:
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')

# TO:
TOKEN = 'your_bot_token_here'
CHAT_ID = 'your_chat_id_here'
```

## Method 5: Using .env File (Clean & Secure)

1. Create a file named `.env` in your project folder:
```
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

2. Install python-dotenv:
```bash
pip install python-dotenv
```

3. Add to the top of `telegram_message.py`:
```python
from dotenv import load_dotenv
load_dotenv()
```

## Method 6: System Environment Variables (Permanent)

### Windows 10/11 GUI:
1. Press `Win + X` → System
2. Click "Advanced system settings"
3. Click "Environment Variables"
4. Under "User variables", click "New"
5. Add:
   - Variable name: `TELEGRAM_BOT_TOKEN`
   - Variable value: `your_bot_token_here`
6. Repeat for `TELEGRAM_CHAT_ID`
7. Click OK
8. **Restart your terminal/VSCode**

### Windows PowerShell (Permanent):
```powershell
[System.Environment]::SetEnvironmentVariable('TELEGRAM_BOT_TOKEN', 'your_bot_token_here', 'User')
[System.Environment]::SetEnvironmentVariable('TELEGRAM_CHAT_ID', 'your_chat_id_here', 'User')

# Restart terminal after this
```

---

## How to Get Telegram Credentials

### Get Bot Token:
1. Open Telegram
2. Search for `@BotFather`
3. Send: `/newbot`
4. Follow instructions to create bot
5. Copy the token (looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### Get Chat ID:
1. Start a chat with your bot
2. Send any message to it
3. Open browser and visit:
   ```
   https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
   ```
   Replace `<YOUR_BOT_TOKEN>` with your actual token
4. Look for `"chat":{"id":123456789` in the response
5. That number is your chat ID

---

## Quick Test

After setting variables, test with:

```python
python -c "import os; print('Token:', os.getenv('TELEGRAM_BOT_TOKEN')); print('Chat ID:', os.getenv('TELEGRAM_CHAT_ID'))"
```

Should output:
```
Token: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz
Chat ID: 987654321
```

---

## Troubleshooting

### "set is not working"
- You're likely in PowerShell, not CMD
- Use `$env:VARIABLE_NAME = "value"` in PowerShell
- Or use `set VARIABLE_NAME=value` in CMD

### Variables not found
- Make sure to run the automation in the **same terminal window** where you set them
- Session variables are lost when you close the terminal
- Use permanent method if you want them to persist

### Still not working?
- Use Method 4 (direct edit) for quick testing
- Or create a wrapper script that sets variables before running

---

## Example: Complete Setup Script

Create `run_with_telegram.bat`:

```batch
@echo off
set TELEGRAM_BOT_TOKEN=your_bot_token_here
set TELEGRAM_CHAT_ID=your_chat_id_here
python alt_triggered_automation.py
pause
```

Then just run: `run_with_telegram.bat`

---

## Security Note

**Never commit credentials to git!**

Add to `.gitignore`:
```
.env
set_credentials.py
run_with_telegram.bat
```
