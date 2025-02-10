import discord
from discord.ext import commands
import random

with open("ronpasta.txt", "r", encoding="utf-8") as fr:
    ron_copypasta = fr.read().strip().split("\n")


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
