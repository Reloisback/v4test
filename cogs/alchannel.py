import discord
from discord.ext import commands
from discord import app_commands
import sqlite3

class AlChannel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn = sqlite3.connect('db/alliance.sqlite')
        self.c = self.conn.cursor()
        self._create_tables()

    def _create_tables(self):
        self.c.execute('''
            CREATE TABLE IF NOT EXISTS alliance_list (
                alliance_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        ''')
        self.conn.commit()

        self.c.execute('''
            CREATE TABLE IF NOT EXISTS alliancesettings (
                alliance_id INTEGER,
                channel_id INTEGER,
                interval INTEGER,
                FOREIGN KEY (alliance_id) REFERENCES alliance_list (alliance_id)
            )
        ''')
        self.conn.commit()

    async def alliance_autocomplete(self, interaction: discord.Interaction, current: str):
        self.c.execute("SELECT alliance_id, name FROM alliance_list")
        alliances = self.c.fetchall()
        return [
            app_commands.Choice(name=f"{name} (ID: {alliance_id})", value=str(alliance_id))
            for alliance_id, name in alliances if current.lower() in name.lower()
        ][:25]

    async def channel_autocomplete(self, interaction: discord.Interaction, current: str):
        channels = interaction.guild.text_channels
        return [
            app_commands.Choice(name=channel.name, value=str(channel.id))
            for channel in channels if current.lower() in channel.name.lower()
        ][:25]

    @app_commands.command(name="alchannel", description="Set a channel and interval for an alliance.")
    @app_commands.describe(alliance="Select an alliance", channel="Select a channel", interval="Set the interval in minutes (0 to disable)")
    @app_commands.autocomplete(alliance=alliance_autocomplete, channel=channel_autocomplete)
    async def set_channel_interval(self, interaction: discord.Interaction, alliance: str, channel: str, interval: int):
        alliance_id = int(alliance)
        channel_id = int(channel)

        self.c.execute("SELECT name FROM alliance_list WHERE alliance_id = ?", (alliance_id,))
        alliance_name = self.c.fetchone()

        if interval == 0:
            self.c.execute("DELETE FROM alliancesettings WHERE alliance_id = ?", (alliance_id,))
            self.conn.commit()
            await interaction.response.send_message(f"Automatic control disabled for alliance ID {alliance_id}.", ephemeral=True)
        else:
            if alliance_name is None:
                self.c.execute("INSERT INTO alliance_list (alliance_id, name) VALUES (?, ?)", (alliance_id, "Unknown"))
                self.conn.commit()
                alliance_name = ("Unknown",)

            self.c.execute("INSERT OR REPLACE INTO alliancesettings (alliance_id, channel_id, interval) VALUES (?, ?, ?)", (alliance_id, channel_id, interval))
            self.conn.commit()

            embed = discord.Embed(title="Alliance Channel Settings", color=discord.Color.green())
            embed.add_field(name="Alliance", value=f"{alliance_name[0]} (ID: {alliance_id})", inline=False)
            embed.add_field(name="Channel", value=f"<#{channel_id}>", inline=False)
            embed.add_field(name="Interval", value=f"{interval} minutes", inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(AlChannel(bot))
