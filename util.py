from discord.ext import commands
import discord

EMBED_BOT_USER = discord.Embed(
    title = "Cannot track a bot user",
    description = "Bot user untrackable",
    color=discord.Colour.red(),
)
EMBED_ALREADY_TRACKED = discord.Embed(
    color = discord.Colour.dark_blue(),
    description = "User already tracked"
)
EMBED_USER_NOT_FOUND = discord.Embed(
    title = "Couldn't find that user, bro!",
    description = "User not found"
)
EMBED_NON_USER = discord.Embed(
    title = "Yo, you gotta specify a valid member.",
    description = "Member not specified"
)
EMBED_USER_TRACKED = discord.Embed(
    title = "✅",
    color = discord.Colour.green()
)
EMBED_USER_NOT_TRACKED = discord.Embed(
    title = "❌",
    color = discord.Colour.red()
)

async def find_user(ctx, *, query: str = None):
    member = None
    try:
        member = await commands.MemberConverter().convert(ctx, query)
    except commands.BadArgument:
        # Conversion failed, so we'll try a manual lookup
        query_clean = query.strip()
        if query_clean.startswith("\\@"):
            query_clean = query_clean[2:]
        elif query_clean.startswith("@"):
            query_clean = query_clean[1:]
        member = discord.utils.find(
            lambda m: m.name.lower() == query_clean.lower() or m.display_name.lower() == query_clean.lower(),
            ctx.guild.members,
        )

    return member
