from discord.ext import commands
import discord
import json
import logging
import aiofiles

EMBED_BOT_USER = discord.Embed(
    title="Cannot track a bot user",
    description="Bot user untrackable",
    color=discord.Colour.red(),
)
EMBED_ALREADY_TRACKED = discord.Embed(
    color=discord.Colour.dark_blue(),
    description="User already tracked",
)
EMBED_USER_NOT_FOUND = discord.Embed(
    title="Couldn't find that user!",
    description="User not found",
)
EMBED_NON_USER = discord.Embed(
    title="Yo, you gotta specify a valid member.",
    description="Member not specified",
)
EMBED_USER_TRACKED = discord.Embed(
    title="✅",
    color=discord.Colour.green(),
)
EMBED_USER_NOT_TRACKED = discord.Embed(
    title="❌",
    color=discord.Colour.red(),
)
EMBED_USER_NOT_TRACKED_DETAILED = discord.Embed(
    title="User not tracked by the bot,\nyou cannot access history without the bot listening to the user first",
    color=discord.Colour.red(),
)
EMBED_CURRENT_TIMEZONE = discord.Embed(
    title="The current timezone set for the bot is: ",
    color=discord.Colour.blue(),
)
EMBED_CHANGED_TIMEZONE = discord.Embed(
    color=discord.Colour.yellow(),
)
STATE_LABELS = {3: "online", 2: "idle", 1: "dnd", 0: "offline"}
INV_STATE_LABELS = {v: k for k, v in STATE_LABELS.items()}
STATE_COLORS = {3: "#3ba55d", 2: "#faa81a", 1: "#ed4245", 0: "#747f8d"}
HISTORY = "history.json"
STATUS_EMOJIS = {
    "online": "🟢",
    "idle": "🟡",
    "dnd": "🔴",
    "offline": "⚫",
}
WELCOME = r"""
__        __   _                          
\ \      / /__| | ___ ___  _ __ ___   ___ 
 \ \ /\ / / _ \ |/ __/ _ \| '_ ` _ \ / _ \
  \ V  V /  __/ | (_| (_) | | | | | |  __/
   \_/\_/ \___|_|\___\___/|_| |_| |_|\___|
"""


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

def open_data():
    try:
        with open(HISTORY, "r") as f:
            his_json = json.load(f)
            tracked_users = {int(k): v for k, v in his_json.get("tracked_users", {}).items()}
            users = his_json.get("users", {})

    except (FileNotFoundError, json.JSONDecodeError):
        tracked_users = {}
        users = {}

    return tracked_users, users

async def save_data(tracked_users, users):
    async with aiofiles.open(HISTORY, "w") as f:
        await f.write(json.dumps({"tracked_users": tracked_users, "users": users}))


# these operations are sync, not ideal
def sync_save_data(tracked_users, users):
    try:
        his_json = {"tracked_users": tracked_users, "users": users}
        with open(HISTORY, "w") as fp:
            json.dump(his_json, fp)
    except Exception as e:
        logging.CRITICAL(f"history was unable to save properly, {e}")
        print(f"CRITICAL: history was unable to save properly, {e}")
