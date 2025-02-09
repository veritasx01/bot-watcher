import discord
import random
from discord.ext import commands
import os
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
import json

load_dotenv()
token = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.dm_messages = True
intents.presences = True
intents.members = True

ron_copypasta = [
    "Listen up Ron, you little twerp. I don’t know who you think you’re messing with, but let me make one thing clear. I’ve been through more than you could ever imagine. I’m talking secret missions, high-stakes negotiations, and a body count that would make the toughest people on this planet quiver in fear.",
    "Ron You think you’re tough? You think your words sting? Buddy, I’ve heard it all. I’ve *seen* it all. And you? You’re just a blip, a speck on the radar, a shadow of someone who might’ve been worth something if they weren’t so damn predictable.",
    "Ron, Don’t come at me with your weak insults and overinflated ego. I’ve been in situations that would have broken you into a thousand pieces. But me? I’m still here. And I’m not going anywhere.",
    "Ron, do yourself a favor, back up, and recognize who you're dealing with. Because if you don’t, you’ll regret it. You have no idea what’s coming your way.",
    "Ron, listen up, kid. I've been through hell and back, and I'm still standing. You might think you're tough, but you're just another face in the crowd. Step aside before you get crushed.",
    "Ron always says that if you're gonna challenge him, you'd better be ready for a world of hurt. He's outwitted the worst of them, and your feeble attempts won't even scratch the surface.",
    "Ron has fought battles that would make your blood run cold. He doesn't take kindly to weaklings who think they can intimidate him—so keep dreaming, kid.",
    "Ron carries a story in every scar on his body. If you keep pushing your luck, you'll add one of your own. He warns you: don't test his patience.",
    "Ron doesn't play games. He's built a legacy of toughness and relentless action. If you're looking for a fight, prepare to be schooled.",
    "Ron considers this your one and only warning.\nHe's seen threats come and go, and you're nothing but a minor nuisance. Back off now.",
    "Ron wants you to remember this moment, kid.\nToday, you almost crossed paths with someone forged in the fires of real combat. Next time, it won't be so forgiving—get lost before you face his full wrath.",
    "What the hell did you just say about me, you little Ron? I’ll have you know I graduated top of my class in the Navy SEALs...",
    "According to all known laws of aviation, there is no way that a Ron should be able to fly...",
    "I used to be a Ron like you, but then I took an arrow to the knee.",
    "You see, Ron, in this world, it’s all about survival. The rich get richer, and the poor get stepped on...",
    "They are rage, Ron. Brutal, without mercy. But you. You will be worse. Rip and tear, until it is done.",
    "Control, we have a Code Ron. I repeat, we have a Code Ron. The target is spamming memes in general chat. Requesting immediate air support, over.",
    "Average Ron hater: 😡📉📉📉  Average Ron enjoyer: 🗿📈📈📈",
    "No Rons? 😐",
    "Ron didn’t wake up at 4 AM to watch motivational videos. Ron **is** the motivation. Keep grinding, King. 💰😤",
    "I am not in danger, Ron. I AM the danger. A guy opens his door and gets shot, and you think that of me? No, Ron. I am the one who knocks.",
    "The FitnessGram™ Pacer Test is a multistage aerobic capacity test that progressively gets more difficult as Ron continues...",
    "Did you ever hear the tragedy of Darth Ron the Wise? I thought not. It’s not a story the Jedi would tell you...",
    "When the Ron is **sus**. 🚨🚨😳",
    "Ron... my beloved. 😩❤️",
    "It’s so over, Ron. 😔💀\nWait… we’re so back. 🔥💪",
    "We live in a society, Ron.\nA society that laughs at people like you and me. But not anymore…",
    "No matter how strong you think you are, you are not immune to Ron.",
    "Bro, go outside and touch some Ron. 🌿✨",
    "It's Ronbin’ time. 💀💸",
    "This post was made by the **Ron Gang**. 💪🔥",
    "Ron is too dangerous to be kept alive. His power is… unnatural.",
    "99% of people will scroll past this without realizing the true power of Ron.",
    "Scientists fear the day we uncover Ron’s true potential.",
    "Some say Ron has no weaknesses. Others are too afraid to ask.",
    "You don’t meet Ron… Ron meets you.",
    "Long ago, the elders spoke of a being known only as… Ron.",
]

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Process commands so that the !commands work
    await bot.process_commands(message)


@bot.command()
async def ron(ctx):
    """Send a random Ron copypasta."""
    await ctx.send(random.choice(ron_copypasta))

HISTORY = "history.json"

try:
    with open(HISTORY, "r") as f:  # Open in read mode
        his_json = json.load(f)
        #tracked_users = his_json.get("tracked_users", {})  # Use .get() to avoid KeyError
        tracked_users = {int(k): v for k, v in his_json.get("tracked_users", {}).items()}
        users = his_json.get("users", [])
except (FileNotFoundError, json.JSONDecodeError):  # Handle missing file or bad JSON
    tracked_users = {}
    users = []

print(tracked_users)
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

    if member.id in tracked_users:
        embed.color = discord.Colour.dark_blue()
        embed.title = f"I'm already tracking {member.display_name}!"
        embed.description = "User already tracked"
        await ctx.send(embed=embed)
    else:
        # start tracking this username and userid
        tracked_users[member.id] = []
        users.append([member.name, member.display_name])
        embed.color = discord.Colour.green()
        embed.title = f"Now listening to {member.display_name}'s status changes!"
        embed.description = "Listening successful"
        await ctx.send(embed=embed)


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
        embed.title = "Couldn't find that user, bro!"
        embed.description = "User not found"
        await ctx.send(embed=embed)
        return

    if member.id not in tracked_users:
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
        #time_str = timestamp.strftime("%Y-%m-%d %H:%M:%S %Z")
        time_str = timestamp
        message_lines.append(f"{time_str}: {old_status} -> {new_status}")
    message_lines = reversed(message_lines)
    message_str = "\n".join(message_lines)
    message_send = message_str
    embed.color=0x61DBFB
    if not all:
        message_send = "\n".join(message_str.split("\n")[:10])
        embed.title=f"Showing last 10 status changes for {member.display_name}"
    else:
        embed.title=f"Showing all status changes for {member.display_name}"
    embed.description=message_send
    await ctx.send(embed=embed)
    his_json = {"tracked_users": tracked_users,"users": users}
    with open(HISTORY,"w") as fp:
        print("saved")
        json.dump(his_json,fp)

@bot.command()
async def showall(ctx,*,query:str = None):
    """Shows the full status history of a user"""
    await show(ctx,query=query,show_all=True)

@bot.event
async def on_presence_update(before: discord.Member, after: discord.Member):
    if after.id in tracked_users:
        if before.status != after.status:
            if tracked_users[after.id]:
                last_timestamp, last_before, last_after = tracked_users[after.id][-1]
                if last_before == before.status and last_after == after.status:
                    # weird fix because two events at the same time
                    return

            timestamp = datetime.now(timezone(timedelta(hours=2)))
            tracked_users[after.id].append((timestamp.strftime("%Y-%m-%d %H:%M:%S %Z"), before.status, after.status))
            print(f"Recorded change for {after.display_name}: {before.status} -> {after.status} at {timestamp}")
            his_json = {"tracked_users": tracked_users,"users": users}
            with open(HISTORY,"w") as fp:
                print("saved")
                json.dump(his_json,fp)


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
        if member.id not in tracked_users:
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


bot.run(token)
