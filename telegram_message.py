import asyncio
from telegram import Bot
# from telegram.ext import Application

# Replace with your bot token
TOKEN = '8265029896:AAGxJ0mOImHRCve_fN4ZUetYawHGv7dwFDs'
CHAT_ID = '5055934055'

async def send_message(message: str):
    # Initialize the bot
    bot = Bot(token=TOKEN)
    
    # Send the message
    await bot.send_message(chat_id=CHAT_ID, text=message)


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
