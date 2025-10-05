import asyncio
import os
from telegram import Bot
# from telegram.ext import Application

# Load credentials from environment variables (more secure)
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')

async def send_message(message: str):
    """Send message via Telegram bot

    Set environment variables before using:
    - TELEGRAM_BOT_TOKEN: Your bot token
    - TELEGRAM_CHAT_ID: Your chat ID
    """
    if not TOKEN or not CHAT_ID:
        print("⚠️ Telegram credentials not set. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables.")
        return False

    try:
        # Initialize the bot
        bot = Bot(token=TOKEN)

        # Send the message
        await bot.send_message(chat_id=CHAT_ID, text=message)
        return True
    except Exception as e:
        print(f"❌ Failed to send Telegram message: {e}")
        return False


# direct https request
# import requests

# # Replace with your bot's token and chat ID
# TOKEN = '8265029896:AAGxJ0mOImHRCve_fN4ZUetYawHGv7dwFDs'
# CHAT_ID = '5055934055'
# MESSAGE = 'Hello from Python!'

# # Telegram API endpoint
# url = f'https://api.telegram.org/bot{TOKEN}/sendMessage'

# # Send the message
# response = requests.post(url, data={'chat_id': CHAT_ID, 'text': MESSAGE})

# # Check the response status
# if response.status_code == 200:
#     print('Message sent successfully!')
# else:
#     print('Failed to send message:', response.text)
