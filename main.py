import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from commands import Commands
import logging
from util import (
    WELCOME,
)

load_dotenv()
TOKEN = os.getenv("TOKEN")

logging.getLogger("discord").setLevel(logging.INFO)
logging.basicConfig(filename="app.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
# to disable log use logging.disable(logging.CRITICAL)

intents = discord.Intents.default()
intents.message_content = True
intents.dm_messages = True
intents.presences = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    try:
        await bot.add_cog(Commands(bot))
        print(WELCOME)
        print(f"Logged in as {bot.user}")
    except Exception as e:
        logging.error(f"Error in on_ready()\n{str(e)}")


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    try:
        await bot.process_commands(message)
    except Exception as e:
        logging.error(f"Error in on_message()\n{str(e)}")


# use bot.run(TOKEN,log_handler=None)
# to turn off session logs
bot.run(TOKEN)
