import discord
from discord.ext import commands, tasks
import os
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
import json
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from misc import Miscellaneous
from util import (
    find_user,
    EMBED_BOT_USER,
    EMBED_ALREADY_TRACKED,
    EMBED_USER_NOT_FOUND,
    EMBED_NON_USER,
    EMBED_USER_TRACKED,
    EMBED_USER_NOT_TRACKED,
)

load_dotenv()
TOKEN = os.getenv("TOKEN")
HISTORY = "history.json"

intents = discord.Intents.default()
intents.message_content = True
intents.dm_messages = True
intents.presences = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)
# bot.remove_command("help")

status_emojis = {
    "online": "🟢",
    "idle": "🟡",
    "dnd": "🔴",
    "offline": "⚫",
}

state_labels = {3: "online", 2: "idle", 1: "dnd", 0: "offline"}
inv_state_labels = {v: k for k, v in state_labels.items()}
state_colors = {3: "#3ba55d", 2: "#faa81a", 1: "#ed4245", 0: "#747f8d"}

try:
    with open(HISTORY, "r") as f:  # Open in read mode
        his_json = json.load(f)
        tracked_users = {int(k): v for k, v in his_json.get("tracked_users", {}).items()}
        users = his_json.get("users", [])

except (FileNotFoundError, json.JSONDecodeError):  # Handle missing file or bad JSON
    tracked_users = {}
    users = []

print(users)


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


@bot.command()
async def listen(ctx, *, query: str = None):
    """Listens to the presence of a user by mention or plain username."""
    embed = discord.Embed(color=discord.Colour.red())
    if query is None:
        await ctx.send(embed=EMBED_INVALID_USER)
        return

    member = await find_user(ctx, query=query)
    if member is None:
        await ctx.send(embed=EMBED_USER_NOT_FOUND)
        return

    if member.bot:
        # we refuse to listen to bots because they open up the possibility of a bot status spam attack
        # and who the hell would want to track a bot's status anyways XD
        await ctx.send(embed=EMBED_BOT_USER)
        return

    if any(member.name == user[0] for user in users):
        embed = EMBED_ALREADY_TRACKED
        embed.title = f"I'm already tracking {member.display_name}!"
        await ctx.send(embed=embed)
        return

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
    await ctx.send(embed=EMBED_USER_NOT_FOUND)


@bot.command()
async def show(ctx, *, query: str = None, show_all: bool = False):
    """Shows status changes for a user by mention or plain username."""
    embed = discord.Embed(color=discord.Colour.red())
    if query is None:
        await ctx.send(embed=EMBED_NON_USER)
        return

    member = await find_user(ctx, query=query)
    if member is None:
        await ctx.send(embed=EMBED_USER_NOT_FOUND)
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
    embed.color = discord.Colour.blurple()

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
async def daygraph(ctx, *, query):
    member = await find_user(ctx, query=query)
    if member.bot:
        await ctx.send(embed=EMBED_BOT_USER)
        return
    if member is None:
        await ctx.send(embed=EMBED_USER_NOT_FOUND)
        return

    tz = timezone(timedelta(hours=2))
    now = datetime.now(tz)
    one_day_ago = now - timedelta(days=1)
    entries = tracked_users.get(member.id, [])
    day_entries = [entry for entry in entries if datetime.strptime(entry[0], "%Y-%m-%d %H:%M:%S UTC%z") >= one_day_ago]

    day_entries = [
        entry
        for entry in entries
        if datetime.strptime(entry[0], "%Y-%m-%d %H:%M:%S UTC%z").astimezone(tz) >= one_day_ago
    ]

    # if there are no entries, notify user
    if not day_entries:
        await ctx.send(
            embed=discord.Embed(title="No status data for the last 24 hours.", color=discord.Colour.blurple),
        )
        return

    # sorting precaution, data should be already sorted but we sort it anyways
    day_entries.sort(key=lambda x: datetime.strptime(x[0], "%Y-%m-%d %H:%M:%S UTC%z"))

    time_values = [datetime.strptime(entry[0], "%Y-%m-%d %H:%M:%S UTC%z").astimezone(tz) for entry in day_entries]
    states = []
    for entry in day_entries:
        states.append(inv_state_labels[entry[2]])

    plt.figure(figsize=(12, 5))
    plt.step(time_values, states, where="post", linestyle="--", color="black", alpha=0.7)

    # plot points
    for i in range(len(time_values)):
        plt.scatter(time_values[i], states[i], color=state_colors[states[i]], s=100, edgecolors="black", zorder=3)

    ax = plt.gca()
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M", tz=tz))
    #ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
    ax.xaxis.set_major_locator(mdates.MinuteLocator(byminute=[0, 30]))
    plt.xticks(rotation=45)

    ytick_positions = sorted(state_labels.keys(), reverse=True)
    ytick_labels = [state_labels[k] for k in ytick_positions]
    plt.yticks(ytick_positions, ytick_labels)

    plt.xlabel("Time")
    plt.ylabel("Status")
    plt.title("Discord Status Changes Over 24 Hours")
    plt.grid(axis="y", linestyle="--", alpha=0.7)

    plt.savefig("fig.png")
    plt.close()

    file = discord.File("fig.png", filename="fig.png")
    await ctx.send(file=file)


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

    member = await find_user(ctx, query=query)
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
    await ctx.send(embed=EMBED_USER_NOT_FOUND)


@bot.event
async def on_presence_update(before: discord.Member, after: discord.Member):
    if after.id not in tracked_users:
        return
    if tracked_users[after.id]:
        last_status = tracked_users[after.id][-1][2]
        if last_status == str(after.status):
            return

    if before.status == after.status:
        return

    timestamp = datetime.now(timezone(timedelta(hours=2)))
    tracked_users[after.id].append((timestamp.strftime("%Y-%m-%d %H:%M:%S %Z"), str(before.status), str(after.status)))
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
        color=discord.Colour.blurple(),
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
        await ctx.send(embed=EMBED_NON_USER)
        return

    member = await find_user(ctx, query=query)
    if member is None:
        await ctx.send(embed=EMBED_USER_NOT_FOUND)
        return
    if any(str(member) in sublist for sublist in users):
        embed = EMBED_USER_TRACKED
        embed.description = f"{member.name} is tracked"
    else:
        embed = EMBED_USER_NOT_TRACKED
        embed.description = f"{member.name} is NOT tracked"

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
