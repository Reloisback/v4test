import discord
from discord.ext import commands
import sqlite3
from datetime import datetime

class LogSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings_db = sqlite3.connect('db/settings.sqlite', check_same_thread=False)
        self.settings_cursor = self.settings_db.cursor()
        
        self.alliance_db = sqlite3.connect('db/alliance.sqlite', check_same_thread=False)
        self.alliance_cursor = self.alliance_db.cursor()
        
        self.setup_database()

    def setup_database(self):
        try:
            self.settings_cursor.execute("""
                CREATE TABLE IF NOT EXISTS alliance_logs (
                    alliance_id INTEGER PRIMARY KEY,
                    channel_id INTEGER,
                    FOREIGN KEY (alliance_id) REFERENCES alliance_list (alliance_id)
                )
            """)
            
            self.settings_db.commit()
                
        except Exception as e:
            print(f"Error setting up log system database: {e}")

    def __del__(self):
        try:
            self.settings_db.close()
            self.alliance_db.close()
        except:
            pass

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not interaction.type == discord.InteractionType.component:
            return

        custom_id = interaction.data.get("custom_id", "")
        
        if custom_id == "log_system":
            try:
                self.settings_cursor.execute("SELECT is_initial FROM admin WHERE id = ?", (interaction.user.id,))
                result = self.settings_cursor.fetchone()
                
                if not result or result[0] != 1:
                    await interaction.response.send_message(
                        "❌ Only global administrators can access the log system.", 
                        ephemeral=True
                    )
                    return

                log_embed = discord.Embed(
                    title="📋 Alliance Log System",
                    description=(
                        "Select an option to manage alliance logs:\n\n"
                        "**Available Options**\n"
                        "━━━━━━━━━━━━━━━━━━━━━━\n"
                        "📝 **Set Log Channel**\n"
                        "└ Assign a log channel to an alliance\n\n"
                        "🗑️ **Remove Log Channel**\n"
                        "└ Remove alliance log channel\n\n"
                        "📊 **View Log Channels**\n"
                        "└ List all alliance log channels\n"
                        "━━━━━━━━━━━━━━━━━━━━━━"
                    ),
                    color=discord.Color.blue()
                )

                view = discord.ui.View()
                view.add_item(discord.ui.Button(
                    label="Set Log Channel",
                    emoji="📝",
                    style=discord.ButtonStyle.primary,
                    custom_id="set_log_channel",
                    row=0
                ))
                view.add_item(discord.ui.Button(
                    label="Remove Log Channel",
                    emoji="🗑️",
                    style=discord.ButtonStyle.danger,
                    custom_id="remove_log_channel",
                    row=0
                ))
                view.add_item(discord.ui.Button(
                    label="View Log Channels",
                    emoji="📊",
                    style=discord.ButtonStyle.secondary,
                    custom_id="view_log_channels",
                    row=1
                ))
                view.add_item(discord.ui.Button(
                    label="Back",
                    emoji="◀️",
                    style=discord.ButtonStyle.secondary,
                    custom_id="bot_operations",
                    row=2
                ))

                await interaction.response.send_message(
                    embed=log_embed,
                    view=view,
                    ephemeral=True
                )

            except Exception as e:
                print(f"Error in log system menu: {e}")
                await interaction.response.send_message(
                    "❌ An error occurred while accessing the log system.",
                    ephemeral=True
                )

        elif custom_id == "set_log_channel":
            try:
                self.settings_cursor.execute("SELECT is_initial FROM admin WHERE id = ?", (interaction.user.id,))
                result = self.settings_cursor.fetchone()
                
                if not result or result[0] != 1:
                    await interaction.response.send_message(
                        "❌ Only global administrators can set log channels.", 
                        ephemeral=True
                    )
                    return

                self.alliance_cursor.execute("""
                    SELECT alliance_id, name 
                    FROM alliance_list 
                    ORDER BY name
                """)
                alliances = self.alliance_cursor.fetchall()

                if not alliances:
                    await interaction.response.send_message(
                        "❌ No alliances found.", 
                        ephemeral=True
                    )
                    return

                alliance_embed = discord.Embed(
                    title="📝 Set Log Channel",
                    description=(
                        "Please select an alliance:\n\n"
                        "**Alliance List**\n"
                        "━━━━━━━━━━━━━━━━━━━━━━\n"
                        "Select an alliance from the list below:\n"
                    ),
                    color=discord.Color.blue()
                )

                alliance_select = discord.ui.Select(
                    placeholder="Select an alliance...",
                    options=[
                        discord.SelectOption(
                            label=f"{name[:50]}",
                            value=str(alliance_id),
                            description=f"Alliance ID: {alliance_id}",
                            emoji="🏰"
                        ) for alliance_id, name in alliances
                    ]
                )

                async def alliance_callback(select_interaction: discord.Interaction):
                    try:
                        alliance_id = int(alliance_select.values[0])
                        
                        channel_embed = discord.Embed(
                            title="📝 Set Log Channel",
                            description=(
                                "Please select a channel:\n\n"
                                "**Channel List**\n"
                                "━━━━━━━━━━━━━━━━━━━━━━\n"
                                "Select a channel from the list below:\n"
                            ),
                            color=discord.Color.blue()
                        )

                        channels = [
                            channel for channel in select_interaction.guild.channels 
                            if isinstance(channel, discord.TextChannel)
                        ]

                        if not channels:
                            await select_interaction.response.send_message(
                                "❌ No text channels found in the server.", 
                                ephemeral=True
                            )
                            return

                        channel_select = discord.ui.Select(
                            placeholder="Select a channel...",
                            options=[
                                discord.SelectOption(
                                    label=f"{channel.name[:50]}",
                                    value=str(channel.id),
                                    description=f"#{channel.name}",
                                    emoji="📝"
                                ) for channel in channels
                            ]
                        )

                        async def channel_callback(channel_interaction: discord.Interaction):
                            try:
                                channel_id = int(channel_select.values[0])
                                
                                self.settings_cursor.execute("""
                                    INSERT OR REPLACE INTO alliance_logs (alliance_id, channel_id)
                                    VALUES (?, ?)
                                """, (alliance_id, channel_id))
                                self.settings_db.commit()

                                self.alliance_cursor.execute("SELECT name FROM alliance_list WHERE alliance_id = ?", (alliance_id,))
                                alliance_name = self.alliance_cursor.fetchone()[0]

                                success_embed = discord.Embed(
                                    title="✅ Log Channel Set",
                                    description=(
                                        f"Successfully set log channel:\n\n"
                                        f"🏰 **Alliance:** {alliance_name}\n"
                                        f"📝 **Channel:** <#{channel_id}>\n"
                                    ),
                                    color=discord.Color.green()
                                )

                                await channel_interaction.response.edit_message(
                                    embed=success_embed,
                                    view=None
                                )

                            except Exception as e:
                                print(f"Error setting log channel: {e}")
                                await channel_interaction.response.send_message(
                                    "❌ An error occurred while setting the log channel.",
                                    ephemeral=True
                                )

                        channel_select.callback = channel_callback
                        
                        channel_view = discord.ui.View()
                        channel_view.add_item(channel_select)

                        await select_interaction.response.edit_message(
                            embed=channel_embed,
                            view=channel_view
                        )

                    except Exception as e:
                        print(f"Error in alliance selection: {e}")
                        await select_interaction.response.send_message(
                            "❌ An error occurred while processing your selection.",
                            ephemeral=True
                        )

                alliance_select.callback = alliance_callback
                
                alliance_view = discord.ui.View()
                alliance_view.add_item(alliance_select)

                await interaction.response.send_message(
                    embed=alliance_embed,
                    view=alliance_view,
                    ephemeral=True
                )

            except Exception as e:
                print(f"Error in set log channel: {e}")
                await interaction.response.send_message(
                    "❌ An error occurred while setting up the log channel.",
                    ephemeral=True
                )

        elif custom_id == "remove_log_channel":
            try:
                self.settings_cursor.execute("SELECT is_initial FROM admin WHERE id = ?", (interaction.user.id,))
                result = self.settings_cursor.fetchone()
                
                if not result or result[0] != 1:
                    await interaction.response.send_message(
                        "❌ Only global administrators can remove log channels.", 
                        ephemeral=True
                    )
                    return

                self.settings_cursor.execute("""
                    SELECT al.alliance_id, al.channel_id 
                    FROM alliance_logs al
                """)
                log_entries = self.settings_cursor.fetchall()

                if not log_entries:
                    await interaction.response.send_message(
                        "❌ No alliance log channels found.", 
                        ephemeral=True
                    )
                    return

                options = []
                for alliance_id, channel_id in log_entries:
                    self.alliance_cursor.execute("SELECT name FROM alliance_list WHERE alliance_id = ?", (alliance_id,))
                    alliance_result = self.alliance_cursor.fetchone()
                    alliance_name = alliance_result[0] if alliance_result else "Unknown Alliance"

                    channel = interaction.guild.get_channel(channel_id)
                    channel_name = channel.name if channel else "Unknown Channel"

                    option_label = f"{alliance_name[:50]}"
                    option_desc = f"Channel: #{channel_name}"
                    
                    options.append(discord.SelectOption(
                        label=option_label,
                        value=f"{alliance_id}",
                        description=option_desc,
                        emoji="🏰"
                    ))

                if not options:
                    await interaction.response.send_message(
                        "❌ No valid log channels found.", 
                        ephemeral=True
                    )
                    return

                remove_embed = discord.Embed(
                    title="🗑️ Remove Log Channel",
                    description=(
                        "Select an alliance to remove its log channel:\n\n"
                        "**Current Log Channels**\n"
                        "━━━━━━━━━━━━━━━━━━━━━━\n"
                        "Select an alliance from the list below:\n"
                    ),
                    color=discord.Color.red()
                )

                alliance_select = discord.ui.Select(
                    placeholder="Select an alliance...",
                    options=options
                )

                async def alliance_callback(select_interaction: discord.Interaction):
                    try:
                        alliance_id = int(alliance_select.values[0])
                        
                        self.alliance_cursor.execute("SELECT name FROM alliance_list WHERE alliance_id = ?", (alliance_id,))
                        alliance_name = self.alliance_cursor.fetchone()[0]
                        
                        self.settings_cursor.execute("SELECT channel_id FROM alliance_logs WHERE alliance_id = ?", (alliance_id,))
                        channel_id = self.settings_cursor.fetchone()[0]
                        
                        confirm_embed = discord.Embed(
                            title="⚠️ Confirm Removal",
                            description=(
                                f"Are you sure you want to remove the log channel for:\n\n"
                                f"🏰 **Alliance:** {alliance_name}\n"
                                f"📝 **Channel:** <#{channel_id}>\n\n"
                                "This action cannot be undone!"
                            ),
                            color=discord.Color.yellow()
                        )

                        confirm_view = discord.ui.View()
                        
                        async def confirm_callback(button_interaction: discord.Interaction):
                            try:
                                self.settings_cursor.execute("""
                                    DELETE FROM alliance_logs 
                                    WHERE alliance_id = ?
                                """, (alliance_id,))
                                self.settings_db.commit()

                                success_embed = discord.Embed(
                                    title="✅ Log Channel Removed",
                                    description=(
                                        f"Successfully removed log channel for:\n\n"
                                        f"🏰 **Alliance:** {alliance_name}\n"
                                        f"📝 **Channel:** <#{channel_id}>"
                                    ),
                                    color=discord.Color.green()
                                )

                                await button_interaction.response.edit_message(
                                    embed=success_embed,
                                    view=None
                                )

                            except Exception as e:
                                print(f"Error removing log channel: {e}")
                                await button_interaction.response.send_message(
                                    "❌ An error occurred while removing the log channel.",
                                    ephemeral=True
                                )

                        async def cancel_callback(button_interaction: discord.Interaction):
                            cancel_embed = discord.Embed(
                                title="❌ Removal Cancelled",
                                description="The log channel removal has been cancelled.",
                                color=discord.Color.red()
                            )
                            await button_interaction.response.edit_message(
                                embed=cancel_embed,
                                view=None
                            )

                        confirm_button = discord.ui.Button(
                            label="Confirm",
                            emoji="✅",
                            style=discord.ButtonStyle.danger,
                            custom_id="confirm_remove"
                        )
                        confirm_button.callback = confirm_callback

                        cancel_button = discord.ui.Button(
                            label="Cancel",
                            emoji="❌",
                            style=discord.ButtonStyle.secondary,
                            custom_id="cancel_remove"
                        )
                        cancel_button.callback = cancel_callback

                        confirm_view.add_item(confirm_button)
                        confirm_view.add_item(cancel_button)

                        await select_interaction.response.edit_message(
                            embed=confirm_embed,
                            view=confirm_view
                        )

                    except Exception as e:
                        print(f"Error in alliance selection: {e}")
                        await select_interaction.response.send_message(
                            "❌ An error occurred while processing your selection.",
                            ephemeral=True
                        )

                alliance_select.callback = alliance_callback
                
                alliance_view = discord.ui.View()
                alliance_view.add_item(alliance_select)

                await interaction.response.send_message(
                    embed=remove_embed,
                    view=alliance_view,
                    ephemeral=True
                )

            except Exception as e:
                print(f"Error in remove log channel: {e}")
                await interaction.response.send_message(
                    "❌ An error occurred while setting up the removal menu.",
                    ephemeral=True
                )

        elif custom_id == "view_log_channels":
            try:
                self.settings_cursor.execute("SELECT is_initial FROM admin WHERE id = ?", (interaction.user.id,))
                result = self.settings_cursor.fetchone()
                
                if not result or result[0] != 1:
                    await interaction.response.send_message(
                        "❌ Only global administrators can view log channels.", 
                        ephemeral=True
                    )
                    return

                self.settings_cursor.execute("""
                    SELECT alliance_id, channel_id 
                    FROM alliance_logs 
                    ORDER BY alliance_id
                """)
                log_entries = self.settings_cursor.fetchall()

                if not log_entries:
                    await interaction.response.send_message(
                        "❌ No alliance log channels found.", 
                        ephemeral=True
                    )
                    return

                list_embed = discord.Embed(
                    title="📊 Alliance Log Channels",
                    description="Current log channel assignments:\n\n",
                    color=discord.Color.blue()
                )

                for alliance_id, channel_id in log_entries:
                    self.alliance_cursor.execute("SELECT name FROM alliance_list WHERE alliance_id = ?", (alliance_id,))
                    alliance_result = self.alliance_cursor.fetchone()
                    alliance_name = alliance_result[0] if alliance_result else "Unknown Alliance"

                    channel = interaction.guild.get_channel(channel_id)
                    channel_name = channel.name if channel else "Unknown Channel"

                    list_embed.add_field(
                        name=f"🏰 Alliance ID: {alliance_id}",
                        value=(
                            f"**Name:** {alliance_name}\n"
                            f"**Log Channel:** <#{channel_id}>\n"
                            f"**Channel ID:** {channel_id}\n"
                            f"**Channel Name:** #{channel_name}\n"
                            "━━━━━━━━━━━━━━━━━━━━━━"
                        ),
                        inline=False
                    )

                view = discord.ui.View()
                view.add_item(discord.ui.Button(
                    label="Back",
                    emoji="◀️",
                    style=discord.ButtonStyle.secondary,
                    custom_id="log_system",
                    row=0
                ))

                await interaction.response.send_message(
                    embed=list_embed,
                    view=view,
                    ephemeral=True
                )

            except Exception as e:
                print(f"Error in view log channels: {e}")
                await interaction.response.send_message(
                    "❌ An error occurred while viewing log channels.",
                    ephemeral=True
                )

async def setup(bot):
    await bot.add_cog(LogSystem(bot))