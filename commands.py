import discord
from discord.ext import commands, tasks
import os
from datetime import datetime, timezone, timedelta
import logging
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import time
from util import (
    find_user,
    open_data,
    save_data,
    EMBED_BOT_USER,
    EMBED_ALREADY_TRACKED,
    EMBED_USER_NOT_FOUND,
    EMBED_NON_USER,
    EMBED_USER_TRACKED,
    EMBED_USER_NOT_TRACKED,
    EMBED_CURRENT_TIMEZONE,
    EMBED_CHANGED_TIMEZONE,
    STATE_LABELS,
    INV_STATE_LABELS,
    STATE_COLORS,
    HISTORY,
    STATUS_EMOJIS,
)
from dotenv import load_dotenv
import asyncio
import pytz, json, aiofiles

load_dotenv()
ID = 0
try: 
    ID = os.getenv("ID")
except:
    pass


class Commands(commands.Cog):
    def __init__(self, bot):
        self.file_lock = asyncio.Lock()
        self.bot = bot
        self.cleanup.start()
        self.size_limit.start()
        self.periodic_save.start()
        self.tz = pytz.timezone("Etc/UTC")
        self.need_saving = False;
        with open("config.json", "r") as conf:
            try:
                conf_json = json.load(conf)
                str_tz = conf_json["timezone"]
                if str_tz not in pytz.all_timezones_set:
                    logging.info("timezone in config file not valid")
                    str_tz = "Etc/UTC"
                self.tz = pytz.timezone(str_tz)
            except:
                with open("config.json","w") as conf:
                    conf.write(json.dumps({"timezone": str(self.tz)}))
            finally:
                logging.info(f"Timezone set to {self.tz}")

        self.tracked_users, self.users = open_data()

    def cog_unload(self):
        self.cleanup.cancel()
        self.size_limit.cancel()
        self.periodic_save.cancel()

    @commands.command()
    async def listen(self, ctx, *, query: str = None, call_all=False):
        """Listens to the presence of a user by mention or plain username."""
        if not call_all:
            author = ctx.author
            try:
                logging.info(f"author: {author.id}, {author.name}, {author.display_name} called !listen")
            except:
                pass

        embed = discord.Embed(color=discord.Colour.red())
        if query is None:
            await ctx.send(embed=EMBED_NON_USER)
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

        if member.name in self.users:
            embed = EMBED_ALREADY_TRACKED
            embed.title = f"I'm already tracking {member.display_name}!"
            await ctx.send(embed=embed)
            return

        # start tracking this username and userid
        if member.id not in self.tracked_users:
            self.tracked_users[member.id] = []
        self.users[member.name] = member.display_name
        embed.color = discord.Colour.green()
        embed.title = f"Now listening to {member.display_name}'s status changes!"
        embed.description = "Listening successful"
        self.need_saving = True       
        await ctx.send(embed=embed)

    @listen.error
    async def listen_error(self, ctx, error):
        await ctx.send(embed=EMBED_USER_NOT_FOUND)
        logging.error(error)

    @commands.command()
    async def show(self, ctx, *, query: str = None, show_all: bool = False):
        """Shows status changes for a user by mention or plain username."""
        if not show_all:
            author = ctx.author
            try:
                logging.info(f"author: {author.id}, {author.name}, {author.display_name} called !show")
            except:
                pass
        embed = discord.Embed(color=discord.Colour.red())
        if query is None:
            await ctx.send(embed=EMBED_NON_USER)
            return

        member = await find_user(ctx, query=query)
        if member is None:
            await ctx.send(embed=EMBED_USER_NOT_FOUND)
            return

        if member.name not in self.users:
            embed.title = f"I'm not tracking {member.display_name}. Use !listen first!"
            embed.description = "User not tracked"
            await ctx.send(embed=embed)
            return

        changes = self.tracked_users[member.id]
        if not changes:
            embed.color = discord.Colour.yellow()
            embed.title = f"No status changes recorded for {member.display_name}."
            embed.description = "No status changes found"
            await ctx.send(embed=embed)
            return

        embed = discord.Embed()
        message_lines = []
        for timestamp, old_status, new_status in changes:
            old_icon = STATUS_EMOJIS.get(old_status, "")
            new_icon = STATUS_EMOJIS.get(new_status, "")
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
        self.need_saving = True
        await ctx.send(embed=embed)

    @commands.command()
    async def daygraph(self, ctx, *, query):
        member = await find_user(ctx, query=query)
        if member is None:
            await ctx.send(embed=EMBED_USER_NOT_FOUND)
            return
        if member.bot:
            await ctx.send(embed=EMBED_BOT_USER)
            return
        await ctx.send(f"generating a graph might take a few seconds, current timezone is {str(self.tz)}")
        now = datetime.now(self.tz)
        one_day_ago = now - timedelta(days=1)
        entries = self.tracked_users.get(member.id, [])

        day_entries = [
            entry
            for entry in entries
            if datetime.strptime(entry[0], "%Y-%m-%d %H:%M:%S UTC%z").astimezone(self.tz) >= one_day_ago
        ]

        # if there are no entries, notify user
        if not day_entries or len(entries) == 0:
            await ctx.send(
                embed=discord.Embed(title="No status data for the last 24 hours.", color=discord.Colour.blurple()),
            )
            return

        # sorting precaution, data should be already sorted but we sort it anyways
        day_entries.sort(key=lambda x: datetime.strptime(x[0], "%Y-%m-%d %H:%M:%S UTC%z"))

        time_values = [
            datetime.strptime(entry[0], "%Y-%m-%d %H:%M:%S UTC%z").astimezone(self.tz) for entry in day_entries
        ]
        states = []
        for entry in day_entries:
            states.append(INV_STATE_LABELS[entry[2]])

        time_values.append(datetime.now().astimezone(self.tz))
        states.append(INV_STATE_LABELS[day_entries[-1][2]])

        plt.figure(figsize=(12, 5))
        plt.step(time_values, states, where="post", linestyle="--", color="black", alpha=0.7)

        # plot points
        for i in range(len(time_values)):
            plt.scatter(time_values[i], states[i], color=STATE_COLORS[states[i]], s=100, edgecolors="black", zorder=3)

        ax = plt.gca()
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M", tz=self.tz))
        ax.xaxis.set_major_locator(mdates.MinuteLocator(byminute=[0, 30]))
        plt.xticks(rotation=45)

        ytick_positions = sorted(STATE_LABELS.keys(), reverse=True)
        ytick_labels = [STATE_LABELS[k] for k in ytick_positions]
        plt.yticks(ytick_positions, ytick_labels)

        plt.xlabel("Time")
        plt.ylabel("Status")
        plt.title("Discord Status Changes Over 24 Hours")
        plt.grid(axis="y", linestyle="--", alpha=0.7)

        plt.savefig("fig.png")
        plt.close()

        file = discord.File("fig.png", filename="fig.png")
        await ctx.send(file=file)

    @daygraph.error
    async def daygraph_error(self, ctx, error):
        await ctx.send(embed=EMBED_USER_NOT_FOUND)
        logging.error(error)

    @commands.command()
    async def showall(self, ctx, *, query: str = None):
        """Shows the full status history of a user"""
        author = ctx.author
        try:
            logging.info(f"author: {author.id}, {author.name}, {author.display_name} called !stop")
        except:
            pass
        await self.show(ctx, query=query, show_all=True)

    @commands.command()
    async def stop(self, ctx, *, query: str = None):
        """stop listening to a user\nbut not erasing their history"""
        author = ctx.author
        logging.info(f"author: {author.id}, {author.name}, {author.display_name} called !stop")
        embed = discord.Embed()
        embed.color = discord.Colour.blurple()
        embed.title = "∅"
        embed.description = "only admins can use this command."
        if str(ctx.author.id) != ID:
            await ctx.send(embed=embed)
            return
        member = await find_user(ctx, query=query)
        if member is None:
            embed.color = discord.Colour.red()
            embed.title = "Failed to find user"
            embed.description = "failed to locate user"
            await ctx.send(embed=embed)
            return
        try:
            del self.users[member.name]
            await save_data(self.tracked_users, self.users)

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
    async def stop_error(self, ctx, error):
        await ctx.send(embed=EMBED_USER_NOT_FOUND)
        logging.error(error)

    @commands.Cog.listener()
    async def on_presence_update(self, before: discord.Member, after: discord.Member):
        if after.id not in self.tracked_users:
            return
        if after.name not in self.users:
            return
        if self.tracked_users[after.id]:
            last_status = self.tracked_users[after.id][-1][2]
            if last_status == str(after.status):
                return
        if before.status == after.status:
            return

        timestamp = datetime.now(timezone(timedelta(hours=3)))
        self.tracked_users[after.id].append(
            (timestamp.strftime("%Y-%m-%d %H:%M:%S %Z"), str(before.status), str(after.status))
        )
        logging.info(f"Recorded change for {after.display_name}: {before.status} -> {after.status} at {timestamp}")
        self.need_saving = True

    @commands.command()
    async def listenall(self, ctx):
        """Starts tracking status changes for all members in the server."""
        author = ctx.author
        try:
            logging.info(f"author: {author.id}, {author.name}, {author.display_name} called !listenall")
        except:
            pass
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
            if member.name not in self.users:
                await self.listen(ctx, query=member.name, call_all=True)
                count += 1

        embed = discord.Embed(
            color=discord.Colour.green(),
            title=f"Now tracking {count} new users in {guild.name}!",
            description=f"tracking {count} new users.",
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def list(self, ctx, server: str = None):
        """list all tracked users"""
        author = ctx.author
        try:
            logging.info(f"author: {author.id}, {author.name}, {author.display_name} called !list")
        except:
            pass
        embed = discord.Embed(
            title="Users currently tracked:",
            color=discord.Colour.blurple(),
        )
        str_to_send = ""
        if str(author.id) == ID and (server and server.lower() == "all"):
            for user0, user1 in self.users.items():
                str_to_send += f"{user0}, **AKA**: {user1}\n"
        else:
            members = str(ctx.guild.members)
            new_users = []
            for k, v in self.users.items():
                new_users.append([k, v])
            for user in (x for x in new_users if x[0] in members):
                str_to_send += f"{user[0]}, **AKA**: {user[1]}\n"

        if str_to_send == "":
            embed.title = "I'm not listening to anyone at the moment."
            await ctx.send(embed=embed)
            return
        embed.description = str_to_send
        await ctx.send(embed=embed)
    
    @commands.command()
    async def show_timezone(self,ctx):
        embed = EMBED_CURRENT_TIMEZONE
        embed.description = str(self.tz)
        await ctx.send(embed=embed)
    
    @commands.command()
    async def change_timezone(self, ctx, *, query: str = None):
        if query not in pytz.all_timezones_set:
            await ctx.send(f"Timezone {query} not valid")
            return
        last = self.tz
        self.tz = pytz.timezone(query)
        async with aiofiles.open("config.json","w") as conf:
            await conf.write(json.dumps({"timezone": str(self.tz)}))
        embed = EMBED_CHANGED_TIMEZONE
        embed.title = f"Changed timezone {last} to {self.tz}"
        await ctx.send(embed=embed)
                

    @commands.command()
    async def tracked(self, ctx, *, query: str = None):
        """Checks if a user is tracked"""
        author = ctx.author
        logging.info(f"author: {author.id}, {author.name}, {author.display_name} called !tracked")
        embed = discord.Embed()
        embed.color = discord.Colour.red()
        if query is None:
            await ctx.send(embed=EMBED_NON_USER)
            return

        member = await find_user(ctx, query=query)
        if member is None:
            await ctx.send(embed=EMBED_USER_NOT_FOUND)
            return
        if member in self.users:
            embed = EMBED_USER_TRACKED
            embed.description = f"{member.name} is tracked"
        else:
            embed = EMBED_USER_NOT_TRACKED
            embed.description = f"{member.name} is NOT tracked"

        await ctx.send(embed=embed)

    @tasks.loop(minutes=1)
    async def periodic_save(self):
        start = time.time()
        if not self.need_saving: 
            return
        async with self.file_lock:
            await save_data(self.tracked_users, self.users)
            self.need_saving = False
            now = time.time();
            if (now-start > 0.01):
                logging.warning(f"saving took longer than usual: {now-start} seconds")

    @tasks.loop(hours=24)
    async def cleanup(self):
        start = time.time()
        now = datetime.now(self.tz)
        three_days_ago = now - timedelta(days=3)
        async with self.file_lock:
            before_size = await asyncio.to_thread(os.path.getsize, HISTORY)
            for user_id, entries in self.tracked_users.items():
                self.tracked_users[user_id] = [
                    entry for entry in entries if datetime.strptime(entry[0], "%Y-%m-%d %H:%M:%S UTC%z") >= three_days_ago
                ]
            self.need_saving = True
            after_size = await asyncio.to_thread(os.path.getsize, HISTORY)
        diff = before_size - after_size
        now = time.time()
        if (now-start > 0.1):
            logging.warning(f"cleanup took longer than usual: {now-start} seconds")
        logging.info(f"Cleanup Finished, {diff} bytes deleted.")

    @tasks.loop(minutes=10)
    async def size_limit(self):
        """Limit history size to 20mb"""
        # if you're scaling this bot you can put your data limit check in on_presence_change
        # which will prevent a potential attacker from adding statuses and overflowing your history file
        start = time.time()
        twenty_megabytes = 20_000_000
        async with self.file_lock:
            file_size = await asyncio.to_thread(os.path.getsize, HISTORY)

            if file_size < twenty_megabytes:
                logging.info(f"[{datetime.now().astimezone(self.tz).strftime("%H:%M:%S UTC%z")}] No Size Limit needed, history is {(file_size / 1_000_000):.6f} megabytes")
                return

            before_size = file_size
            for user_id, entries in self.tracked_users.items():
                m = len(entries) // 2
                self.tracked_users[user_id] = entries[m:]

            self.need_saving = True
            after_size = await asyncio.to_thread(os.path.getsize, HISTORY)
            diff = before_size - after_size
            logging.info(f"Size Limit Finished, {diff} bytes deleted.")
            
        now = time.time()
        if (now-start > 0.1):
            logging.warning(f"size_limit took longer than usual: {now-start} seconds")
