import discord
from discord.ext import commands
import random, time, os
from dotenv import load_dotenv

load_dotenv()

with open("ronpasta.txt", "r", encoding="utf-8") as fr:
    ron_copypasta = fr.read().strip().split("\n")

SPAM_USER = os.getenv("SPAM_USER")

class Miscellaneous(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def freddy(self, ctx):
        with open("freddy.jpg", "rb") as f:
            file = discord.File(f)
        await ctx.send(file=file)

    @commands.command()
    async def ron(self, ctx):
        """Send a random Ron copypasta."""
        await ctx.send(random.choice(ron_copypasta))
    
    @commands.command()
    async def spam(self, ctx):
        username = SPAM_USER
        user = discord.utils.get(ctx.guild.members, name=username)

        if user:
            for i in range(10):
                time.sleep(0.5)
                await ctx.send(f"{user.mention} answer dog")
        else:
            await ctx.send(embed=discord.Embed(title="User not found!", description="User not found!"))
