import discord
from discord.ext import commands, tasks
import os
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
import json
import time
from misc import Miscellaneous

load_dotenv()
TOKEN = os.getenv("TOKEN")
HISTORY = "history.json"

intents = discord.Intents.default()
intents.message_content = True
intents.dm_messages = True
intents.presences = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)
bot.remove_command("help")


@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")
    cleanup.start()
    size_limit.start()
    await bot.add_cog(Miscellaneous(bot))


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Process commands so that the !commands work
    await bot.process_commands(message)


try:
    with open(HISTORY, "r") as f:  # Open in read mode
        his_json = json.load(f)
        tracked_users = {int(k): v for k, v in his_json.get("tracked_users", {}).items()}
        users = his_json.get("users", [])

except (FileNotFoundError, json.JSONDecodeError):  # Handle missing file or bad JSON
    tracked_users = {}
    users = []

print(users)


@bot.command()
async def listen(ctx, *, query: str = None):
    """Listens to the presence of a user by mention or plain username."""
    embed = discord.Embed(color=discord.Colour.red())
    if query is None:
        embed.title = "Yo, you gotta specify a valid member to listen to!"
        embed.description = "invalid member"
        await ctx.send(embed=embed)
        return

    member = None
    try:
        member = await commands.MemberConverter().convert(ctx, query)
    except commands.BadArgument:
        # conversion failed, manual lookup
        query_clean = query.strip()
        if query_clean.startswith("\\@"):
            query_clean = query_clean[2:]
        elif query_clean.startswith("@"):
            query_clean = query_clean[1:]
        member = discord.utils.find(
            lambda m: m.name.lower() == query_clean.lower() or m.display_name.lower() == query_clean.lower(),
            ctx.guild.members,
        )

    if member is None:
        embed.title = "Couldn't find that user, bro!"
        embed.description = "User not found"
        await ctx.send(embed=embed)
        return

    if member.bot:
        # we refuse to listen to bots because they open up the possibility of a bot status spam attack
        # and who the hell would want to track a bot's status anyways XD
        embed.title = "Cannot track a bot user"
        embed.description = "Bot user untrackable"
        await ctx.send(embed=embed)
        return

    if member.name in users:
        embed.color = discord.Colour.dark_blue()
        embed.title = f"I'm already tracking {member.display_name}!"
        embed.description = "User already tracked"
        await ctx.send(embed=embed)
    else:
        # start tracking this username and userid
        if member.id not in tracked_users:
            tracked_users[member.id] = []
        users.append([member.name, member.display_name])
        embed.color = discord.Colour.green()
        embed.title = f"Now listening to {member.display_name}'s status changes!"
        embed.description = "Listening successful"
        his_json = {"tracked_users": tracked_users, "users": users}
        with open(HISTORY, "w") as fp:
            json.dump(his_json, fp)
        await ctx.send(embed=embed)


@listen.error
async def listen_error(ctx, error):
    # if listen fails to find user raise this error
    embed = discord.Embed(
        title="Member not found. Please mention a valid member!",
        color=discord.Colour.red(),
        description="Member not found",
    )
    if isinstance(error, commands.BadArgument):
        await ctx.send(embed=embed)
    else:
        raise error


status_emojis = {
    "online": "🟢",
    "idle": "🟡",
    "dnd": "🔴",
    "offline": "⚫",
}


@bot.command()
async def show(ctx, *, query: str = None, show_all: bool = False):
    """Shows status changes for a user by mention or plain username."""
    embed = discord.Embed(color=discord.Colour.red())
    if query is None:
        embed.title = "Specify a member to show their status changes!"
        embed.description = "Member not specified"
        await ctx.send(embed=embed)
        return

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

    if member is None:
        embed.title = "Couldn't find that user!"
        embed.description = "User not found"
        await ctx.send(embed=embed)
        return

    if not any(member.name == user[0] for user in users):
        embed.title = f"I'm not tracking {member.display_name}. Use !listen first!"
        embed.description = "User not tracked"
        await ctx.send(embed=embed)
        return

    changes = tracked_users[member.id]
    if not changes:
        embed.color = discord.Colour.yellow()
        embed.title = f"No status changes recorded for {member.display_name}."
        embed.description = "No status changes found"
        await ctx.send(embed=embed)
        return

    embed = discord.Embed()
    message_lines = []
    for timestamp, old_status, new_status in changes:
        old_icon = status_emojis.get(old_status, "")
        new_icon = status_emojis.get(new_status, "")
        timestamp_clean = timestamp.replace("UTC", "").strip()
        dt = datetime.strptime(timestamp_clean, "%Y-%m-%d %H:%M:%S %z")
        formatted_timestamp = dt.strftime("%Y-%m-%d %H:%M")
        line = f"{formatted_timestamp}: {old_icon} {old_status} → {new_icon} {new_status}"
        message_lines.append(line)

    message_lines = reversed(message_lines)
    message_str = "\n".join(message_lines)
    message_send = message_str
    embed.color = 0x61DBFB

    if not show_all:
        message_send = "\n".join(message_str.split("\n")[:10])
        embed.title = f"Showing last 10 status changes for {member.display_name}"
    else:
        embed.title = f"Showing all status changes for {member.display_name}"

    embed.description = message_send
    await ctx.send(embed=embed)
    his_json = {"tracked_users": tracked_users, "users": users}
    with open(HISTORY, "w") as fp:
        json.dump(his_json, fp)


@bot.command()
async def showall(ctx, *, query: str = None):
    """Shows the full status history of a user"""
    await show(ctx, query=query, show_all=True)


@bot.command()
async def stop(ctx, *, query: str = None):
    """stop listening to a user"""
    embed = discord.Embed()
    embed.color = discord.Colour.blurple()
    embed.title = "∅"
    embed.description = "leo will call this for sure"
    await ctx.send(embed=embed)
    return
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

    if member is None:
        embed.color = discord.Colour.red()
        embed.title = "Failed to find user"
        embed.description = "failed to locate user"
        await ctx.send(embed=embed)
        return

    global users
    try:
        users = [user for user in users if user[0] != str(member.name)]
        his_json = {"tracked_users": tracked_users, "users": users}
        with open(HISTORY, "w") as fp:
            json.dump(his_json, fp)

    except Exception as e:
        embed.color = discord.Colour.red()
        embed.title = "Failed to find user"
        embed.description = f"save error\n{e}"
        await ctx.send(embed=embed)
        return

    embed.color = discord.Colour.yellow()
    embed.title = "removed user"
    embed.description = "successfully to removed user"
    await ctx.send(embed=embed)


@stop.error
async def stop_error(ctx, error):
    embed = discord.Embed()
    embed.color = discord.Colour.red()
    embed.title = "Failed to find user"
    embed.description = "invalid user"
    await ctx.send(embed=embed)


@bot.event
async def on_presence_update(before: discord.Member, after: discord.Member):
    if after.id not in tracked_users:
        return
    if tracked_users[after.id]:
        last_status = tracked_users[after.id][-1][2]
        if last_status == str(after.status):
            return

    if before.status != after.status:
        timestamp = datetime.now(timezone(timedelta(hours=2)))
        tracked_users[after.id].append(
            (timestamp.strftime("%Y-%m-%d %H:%M:%S %Z"), str(before.status), str(after.status))
        )
        print(tracked_users[after.id][-1])
        print(f"Recorded change for {after.display_name}: {before.status} -> {after.status} at {timestamp}")
        his_json = {"tracked_users": tracked_users, "users": users}
        with open(HISTORY, "w") as fp:
            json.dump(his_json, fp)


@bot.command()
async def listenall(ctx):
    """Starts tracking status changes for all members in the server."""
    guild = ctx.guild
    embed = discord.Embed(color=discord.Colour.red())
    if not guild:
        embed.title = "This command must be used in a server!"
        await ctx.send(embed)
        return

    count = 0
    for member in guild.members:
        if member.bot:  # Skip bots
            continue
        if not any(member.name == user[0] for user in users):
            await listen(ctx, query=member.name)
            count += 1

    embed = discord.Embed(
        color=discord.Colour.green(),
        title=f"Now tracking {count} new users in {guild.name}!",
        description=f"tracking {count} new users.",
    )
    await ctx.send(embed=embed)


@bot.command()
async def list(ctx):
    """list all tracked users"""
    embed = discord.Embed(
        title="Users currently tracked:",
        color=0x61DBFB,
    )
    str_to_send = ""
    for user in users:
        str_to_send += f"{user[0]}, **AKA**: {user[1]}\n"
    if str_to_send == "":
        embed.title = "I'm not listening to anyone at the moment."
        await ctx.send(embed=embed)
        return
    embed.description = str_to_send
    await ctx.send(embed=embed)


@bot.command()
async def tracked(ctx, *, query: str = None):
    """Checks if a user is tracked"""
    embed = discord.Embed()
    embed.color = discord.Colour.red()
    if query is None:
        embed.title = "Specify a member to show their status changes!"
        embed.description = "Member not specified"
        await ctx.send(embed=embed)
        return

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

    if member is None:
        embed.title = "Couldn't find that user."
        await ctx.send(embed=embed)
        return
    if any(str(member) in sublist for sublist in users):
        embed.title = "✅"
        embed.description = f"{member.name} is tracked"
        embed.color = discord.Colour.green()
    else:
        embed.title = "❌"
        embed.description = f"{member.name} is NOT tracked"
        embed.color = discord.Colour.red()

    await ctx.send(embed=embed)


@tasks.loop(hours=6)
async def cleanup():
    tz = timezone(timedelta(hours=2))
    now = datetime.now(tz)
    three_days_ago = now - timedelta(days=3)
    before_size = os.path.getsize(HISTORY)
    for user_id, entries in tracked_users.items():
        tracked_users[user_id] = [
            entry for entry in entries if datetime.strptime(entry[0], "%Y-%m-%d %H:%M:%S UTC%z") >= three_days_ago
        ]
    his_json = {"tracked_users": tracked_users, "users": users}
    with open(HISTORY, "w") as fp:
        json.dump(his_json, fp)
    after_size = os.path.getsize(HISTORY)
    diff = before_size - after_size
    print(f"Cleanup Finished, {diff} bytes deleted.")


@tasks.loop(minutes=15)
async def size_limit():
    """Limit history size to 20mb"""
    # if you're scaling this bot you can put your data limit check in on_presence_change
    # which will prevent a potential attacker from adding statuses and overflowing your history file
    file_size = os.path.getsize(HISTORY)
    twenty_megabytes = 20_000_000
    if file_size < twenty_megabytes:
        print(f"No Size Limit needed, history is {file_size/1_000_000} megabytes")
        return

    before_size = os.path.getsize(HISTORY)
    for user_id, entries in tracked_users.items():
        m = len(entries) // 2
        tracked_users[user_id] = [entries[m:]]

    his_json = {"tracked_users": tracked_users, "users": users}
    with open(HISTORY, "w") as fp:
        json.dump(his_json, fp)
    after_size = os.path.getsize(HISTORY)
    diff = before_size - after_size
    print(f"Size Limit Finished, {diff} bytes deleted.")


bot.run(TOKEN)
