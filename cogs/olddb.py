import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import os

class DatabaseTransfer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def olddatabase(self, interaction: discord.Interaction):
        embed = discord.Embed(title="Database Transfer", color=discord.Color.orange())

        if not os.path.exists('gift_db.sqlite'):
            embed.add_field(name="Status", value="gift_db.sqlite not found.", inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        embed.add_field(name="Status", value="Database transfer in progress...", inline=False)
        message = await interaction.response.send_message(embed=embed, ephemeral=True)
        message = await interaction.original_response()

        transfer_steps = [
            ("gift_db.sqlite", "admin", "settings.sqlite"),
            ("gift_db.sqlite", "alliance_channels", "alliance.sqlite"),
            ("gift_db.sqlite", "alliance_intervals", "alliance.sqlite"),
            ("gift_db.sqlite", "alliance_list", "alliance.sqlite"),
            ("gift_db.sqlite", "botsettings", "settings.sqlite"),
            ("gift_db.sqlite", "furnace_changes", "changes.sqlite"),
            ("gift_db.sqlite", "nickname_changes", "changes.sqlite"),
            ("gift_db.sqlite", "gift_codes", "giftcode.sqlite"),
            ("gift_db.sqlite", "user_giftcodes", "giftcode.sqlite"),
            ("gift_db.sqlite", "users", "users.sqlite")
        ]
        db_connections = {}
        
        for source, table, destination in transfer_steps:
            source_path = f'db/{source}' if source != 'gift_db.sqlite' else source
            destination_path = f'db/{destination}'
            
            if source_path not in db_connections:
                db_connections[source_path] = sqlite3.connect(source_path)
            if destination_path not in db_connections:
                db_connections[destination_path] = sqlite3.connect(destination_path)

            try:
                source_conn = db_connections[source_path]
                destination_conn = db_connections[destination_path]
                
                source_cursor = source_conn.cursor()
                destination_cursor = destination_conn.cursor()
                
                source_cursor.execute(f"SELECT * FROM {table}")
                rows = source_cursor.fetchall()
                row_count = len(rows)

                if table == "admin":
                    for row in rows:
                        destination_cursor.execute("INSERT OR REPLACE INTO admin (id, is_initial) VALUES (?, ?)", row)
                elif table == "alliance_channels":
                    destination_cursor.executemany("INSERT OR REPLACE INTO alliancesettings (alliance_id, channel_id) VALUES (?, ?)", rows)
                elif table == "alliance_intervals":
                    for alliance_id, interval in rows:
                        destination_cursor.execute("UPDATE alliancesettings SET interval = ? WHERE alliance_id = ?", (interval, alliance_id))
                elif table == "alliance_list":
                    destination_cursor.executemany("INSERT OR REPLACE INTO alliance_list (alliance_id, name) VALUES (?, ?)", rows)
                elif table == "botsettings":
                    for row in rows:
                        destination_cursor.execute("INSERT OR REPLACE INTO botsettings (id, channelid) VALUES (?, ?)", (row[0], row[1]))
                elif table == "furnace_changes":
                    destination_cursor.executemany("INSERT OR REPLACE INTO furnace_changes (id, fid, old_furnace_lv, new_furnace_lv, change_date) VALUES (?, ?, ?, ?, ?)", rows)
                elif table == "nickname_changes":
                    destination_cursor.executemany("INSERT OR REPLACE INTO nickname_changes (id, fid, old_nickname, new_nickname, change_date) VALUES (?, ?, ?, ?, ?)", rows)
                elif table == "gift_codes":
                    destination_cursor.executemany("INSERT OR REPLACE INTO gift_codes (giftcode, date) VALUES (?, ?)", rows)
                elif table == "user_giftcodes":
                    destination_cursor.executemany("INSERT OR REPLACE INTO user_giftcodes (fid, giftcode, status) VALUES (?, ?, ?)", rows)
                elif table == "users":
                    destination_cursor.executemany("INSERT OR REPLACE INTO users (fid, nickname, furnace_lv, kid, stove_lv_content, alliance) VALUES (?, ?, ?, ?, ?, ?)", rows)

                embed.add_field(name=f"Step {table}", value=f"Transferred {row_count} rows ✔", inline=False)
                await message.edit(embed=embed)
                destination_conn.commit()

            except Exception as e:
                embed.add_field(name=f"Error at {table}", value=f"{str(e)}", inline=False)
                await message.edit(embed=embed)
            
        for conn in db_connections.values():
            conn.close()

        embed.color = discord.Color.green()
        embed.add_field(name="Status", value="All database transfers completed successfully!", inline=False)
        await message.edit(embed=embed)

async def setup(bot):
    await bot.add_cog(DatabaseTransfer(bot))