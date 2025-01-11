import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiohttp
import hashlib
import time
import sqlite3
import asyncio
from datetime import datetime
from colorama import Fore, Style
import os
from aiohttp_socks import ProxyConnector

SECRET = 'tB87#kPtkxqOS2'


level_mapping = {
    31: "30-1", 32: "30-2", 33: "30-3", 34: "30-4",
    35: "FC 1", 36: "FC 1 - 1", 37: "FC 1 - 2", 38: "FC 1 - 3", 39: "FC 1 - 4",
    40: "FC 2", 41: "FC 2 - 1", 42: "FC 2 - 2", 43: "FC 2 - 3", 44: "FC 2 - 4",
    45: "FC 3", 46: "FC 3 - 1", 47: "FC 3 - 2", 48: "FC 3 - 3", 49: "FC 3 - 4",
    50: "FC 4", 51: "FC 4 - 1", 52: "FC 4 - 2", 53: "FC 4 - 3", 54: "FC 4 - 4",
    55: "FC 5", 56: "FC 5 - 1", 57: "FC 5 - 2", 58: "FC 5 - 3", 59: "FC 5 - 4",
    60: "FC 6", 61: "FC 6 - 1", 62: "FC 6 - 2", 63: "FC 6 - 3", 64: "FC 6 - 4",
    65: "FC 7", 66: "FC 7 - 1", 67: "FC 7 - 2", 68: "FC 7 - 3", 69: "FC 7 - 4",
    70: "FC 8", 71: "FC 8 - 1", 72: "FC 8 - 2", 73: "FC 8 - 3", 74: "FC 8 - 4",
    75: "FC 9", 76: "FC 9 - 1", 77: "FC 9 - 2", 78: "FC 9 - 3", 79: "FC 9 - 4",
    80: "FC 10", 81: "FC 10 - 1", 82: "FC 10 - 2", 83: "FC 10 - 3", 84: "FC 10 - 4"
}

class Control(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn_alliance = sqlite3.connect('db/alliance.sqlite')
        self.conn_users = sqlite3.connect('db/users.sqlite')
        self.conn_changes = sqlite3.connect('db/changes.sqlite')
        self.cursor_alliance = self.conn_alliance.cursor()
        self.cursor_users = self.conn_users.cursor()
        self.cursor_changes = self.conn_changes.cursor()
        self.db_lock = asyncio.Lock()
        self.proxies = self.load_proxies()
        self.monitor_alliance_changes.start()

    def load_proxies(self):
        proxies = []
        if os.path.exists('proxy.txt'):
            with open('proxy.txt', 'r') as f:
                proxies = [f"socks4://{line.strip()}" for line in f if line.strip()]
        return proxies

    async def fetch_user_data(self, fid, proxy=None):
        url = 'https://wos-giftcode-api.centurygame.com/api/player'
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        current_time = int(time.time() * 1000)
        form = f"fid={fid}&time={current_time}"
        sign = hashlib.md5((form + SECRET).encode('utf-8')).hexdigest()
        form = f"sign={sign}&{form}"

        try:
            connector = ProxyConnector.from_url(proxy) if proxy else None
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.post(url, headers=headers, data=form, ssl=False) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        print(f"[LOG] API Error - Status Code: {response.status}")
                        return response.status
        except Exception as e:
            print(f"[LOG] Network Error: {e}")
            return None

    async def process_user(self, fid, old_nickname, old_furnace_lv, old_stove_lv_content, old_kid, proxies):
        
        data = await self.fetch_user_data(fid)
        if data and data != 429:
            return data

        
        for proxy in proxies:
            data = await self.fetch_user_data(fid, proxy=proxy)
            if data and data != 429:
                return data

        
        return None

    async def check_agslist(self, channel, alliance_id):
        async with self.db_lock:
            self.cursor_users.execute("SELECT fid, nickname, furnace_lv, stove_lv_content, kid FROM users WHERE alliance = ?", (alliance_id,))
            users = self.cursor_users.fetchall()

        total_users = len(users)
        checked_users = 0

        self.cursor_alliance.execute("SELECT name FROM alliance_list WHERE alliance_id = ?", (alliance_id,))
        alliance_name = self.cursor_alliance.fetchone()[0]

        start_time = datetime.now()
        embed = discord.Embed(title=f"{alliance_name} Alliance Control", color=discord.Color.orange())
        embed.add_field(name="Status", value=f"Control started at {start_time.strftime('%Y-%m-%d %H:%M:%S')}", inline=False)
        embed.add_field(name="Control Progress", value=f"({checked_users}/{total_users})", inline=False)
        message = await channel.send(embed=embed)

        print(f"{alliance_name} Alliance Control started at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Control Progress: ({checked_users}/{total_users})")

        furnace_changes, nickname_changes, kid_changes = [], [], []

        for i in range(0, total_users, 20):
            tasks = []
            for fid, old_nickname, old_furnace_lv, old_stove_lv_content, old_kid in users[i:i+20]:
                tasks.append(self.process_user(fid, old_nickname, old_furnace_lv, old_stove_lv_content, old_kid, self.proxies))

            results = await asyncio.gather(*tasks)

            for result, (fid, old_nickname, old_furnace_lv, old_stove_lv_content, old_kid) in zip(results, users[i:i+20]):
                if isinstance(result, dict):
                    user_data = result['data']
                    new_furnace_lv = user_data['stove_lv']
                    new_nickname = user_data['nickname'].strip()
                    new_kid = user_data.get('kid', 0)
                    new_stove_lv_content = user_data['stove_lv_content']
                    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    async with self.db_lock:
                        if new_stove_lv_content != old_stove_lv_content:
                            self.cursor_users.execute("UPDATE users SET stove_lv_content = ? WHERE fid = ?", (new_stove_lv_content, fid))
                            self.conn_users.commit()

                        if old_kid != new_kid:
                            kid_changes.append(f"{old_nickname} has transferred to a new state. Old State: {old_kid}, New State: {new_kid}")
                            self.cursor_users.execute("UPDATE users SET kid = ? WHERE fid = ?", (new_kid, fid))
                            self.conn_users.commit()

                        if new_furnace_lv != old_furnace_lv:
                            new_furnace_display = level_mapping.get(new_furnace_lv, new_furnace_lv)
                            old_furnace_display = level_mapping.get(old_furnace_lv, old_furnace_lv)
                            self.cursor_changes.execute("INSERT INTO furnace_changes (fid, old_furnace_lv, new_furnace_lv, change_date) VALUES (?, ?, ?, ?)",
                                                         (fid, old_furnace_lv, new_furnace_lv, current_time))
                            self.conn_changes.commit()
                            self.cursor_users.execute("UPDATE users SET furnace_lv = ? WHERE fid = ?", (new_furnace_lv, fid))
                            self.conn_users.commit()
                            furnace_changes.append(f"{old_nickname}: {old_furnace_display} -> {new_furnace_display}")

                        if new_nickname.lower() != old_nickname.lower().strip():
                            self.cursor_changes.execute("INSERT INTO nickname_changes (fid, old_nickname, new_nickname, change_date) VALUES (?, ?, ?, ?)",
                                                         (fid, old_nickname, new_nickname, current_time))
                            self.conn_changes.commit()
                            self.cursor_users.execute("UPDATE users SET nickname = ? WHERE fid = ?", (new_nickname, fid))
                            self.conn_users.commit()
                            nickname_changes.append(f"{old_nickname} -> {new_nickname}")

                checked_users += 1
                embed.set_field_at(1, name="Control Progress", value=f"({checked_users}/{total_users})", inline=False)
                await message.edit(embed=embed)

                print(f"Control Progress: ({checked_users}/{total_users})")

        end_time = datetime.now()
        duration = end_time - start_time

        if furnace_changes or nickname_changes or kid_changes:
            if furnace_changes:
                await self.send_embed(channel, "Furnace Level Changes", "\n".join(furnace_changes), discord.Color.orange())
            if nickname_changes:
                await self.send_embed(channel, "Nickname Changes", "\n".join(nickname_changes), discord.Color.blue())
            if kid_changes:
                await self.send_embed(channel, "State Transfer Notifications", "\n".join(kid_changes), discord.Color.green())
            embed.color = discord.Color.green()
            embed.set_field_at(0, name="Status", value=f"Control completed with changes at {end_time.strftime('%Y-%m-%d %H:%M:%S')}", inline=False)
            embed.add_field(name="Total Duration", value=str(duration), inline=False)
            embed.add_field(name="Total Changes", value=f"{len(furnace_changes) + len(nickname_changes) + len(kid_changes)}", inline=False)
            await message.edit(embed=embed)
        else:
            embed.color = discord.Color.green()
            embed.set_field_at(0, name="Status", value=f"Control completed, no changes found at {end_time.strftime('%Y-%m-%d %H:%M:%S')}", inline=False)
            embed.add_field(name="Total Duration", value=str(duration), inline=False)
            await message.edit(embed=embed)
            print("Control completed, no changes found")

        print(f"Control completed at {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total Duration: {duration}")
        print("Control over!")

    async def send_embed(self, channel, title, description, color):
        embed = discord.Embed(title=title, description=description, color=color)
        await channel.send(embed=embed)

    async def schedule_alliance_check(self, channel, alliance_id, interval):
        while True:
            try:
                if channel is not None:
                    await self.check_agslist(channel, alliance_id)
                await asyncio.sleep(interval * 60)
            except Exception as e:
                print(f"Error in alliance check: {e}")
                await asyncio.sleep(60)

    @tasks.loop(minutes=1)
    async def monitor_alliance_changes(self):
        async with self.db_lock:
            self.cursor_alliance.execute("SELECT alliance_id, channel_id, interval FROM alliancesettings WHERE interval > 0")
            current_alliances = frozenset(self.cursor_alliance.fetchall())

            if not hasattr(self.monitor_alliance_changes, 'previous_alliances'):
                self.monitor_alliance_changes.previous_alliances = current_alliances
                return

            if current_alliances != self.monitor_alliance_changes.previous_alliances:
                print(Fore.GREEN + "Alliance configuration changed. Restarting checks..." + Style.RESET_ALL)
                self.monitor_alliance_changes.previous_alliances = current_alliances
                await self.start_alliance_checks()

    async def start_alliance_checks(self):
        async with self.db_lock:
            self.cursor_alliance.execute("SELECT alliance_id, channel_id, interval FROM alliancesettings WHERE interval > 0")
            alliances = self.cursor_alliance.fetchall()

        for alliance_id, channel_id, interval in alliances:
            channel = self.bot.get_channel(channel_id)
            if channel is not None:
                self.bot.loop.create_task(self.schedule_alliance_check(channel, alliance_id, interval))

    @monitor_alliance_changes.before_loop
    async def before_monitor_alliance_changes(self):
        await self.bot.wait_until_ready()
        await self.start_alliance_checks()

async def setup(bot):
    await bot.add_cog(Control(bot))