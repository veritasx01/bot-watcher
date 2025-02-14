import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from commands import Commands
from util import (
    WELCOME,
)

load_dotenv()
TOKEN = os.getenv("TOKEN")

# logging.getLogger("discord").setLevel(logging.CRITICAL)
# logging.basicConfig(filename="app.log", level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
# to disable log use logging.disable(logging.CRITICAL)
# logging.disable(logging.CRITICAL)

intents = discord.Intents.default()
intents.message_content = True
intents.dm_messages = True
intents.presences = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    await bot.add_cog(Commands(bot))
    print(WELCOME)
    print(f"Logged in as {bot.user}")


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    await bot.process_commands(message)


# use bot.run(TOKEN,log_handler=None)
# to turn off session logs
bot.run(TOKEN)
