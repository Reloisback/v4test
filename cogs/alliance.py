import discord
from discord import app_commands
from discord.ext import commands
import sqlite3  
import asyncio

class Alliance(commands.Cog):
    def __init__(self, bot, conn):
        self.bot = bot
        self.conn = conn
        self.conn_users = sqlite3.connect('db/users.sqlite')
        self.conn_settings = sqlite3.connect('db/settings.sqlite')
        self.c = self.conn.cursor()
        self.c_users = self.conn_users.cursor()
        self.c_settings = self.conn_settings.cursor()
        self._create_table()
        self._check_and_add_column()

    def _create_table(self):
        self.c.execute("""
            CREATE TABLE IF NOT EXISTS alliance_list (
                alliance_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                discord_server_id INTEGER
            )
        """)
        self.conn.commit()

    def _check_and_add_column(self):
        self.c.execute("PRAGMA table_info(alliance_list)")
        columns = [info[1] for info in self.c.fetchall()]
        if "discord_server_id" not in columns:
            self.c.execute("ALTER TABLE alliance_list ADD COLUMN discord_server_id INTEGER")
            self.conn.commit()

    async def view_alliances(self, interaction: discord.Interaction):
        
        user_id = interaction.user.id
        self.c_settings.execute("SELECT id, is_initial FROM admin WHERE id = ?", (user_id,))
        admin = self.c_settings.fetchone()

        if admin is None:
            await interaction.response.send_message("You do not have permission to view alliances.", ephemeral=True)
            return

        is_initial = admin[1]
        guild_id = interaction.guild.id

        try:
            if is_initial == 1:
                query = """
                    SELECT a.alliance_id, a.name, COALESCE(s.interval, 0) as interval
                    FROM alliance_list a
                    LEFT JOIN alliancesettings s ON a.alliance_id = s.alliance_id
                    ORDER BY a.alliance_id ASC
                """
                self.c.execute(query)
            else:
                query = """
                    SELECT a.alliance_id, a.name, COALESCE(s.interval, 0) as interval
                    FROM alliance_list a
                    LEFT JOIN alliancesettings s ON a.alliance_id = s.alliance_id
                    WHERE a.discord_server_id = ?
                    ORDER BY a.alliance_id ASC
                """
                self.c.execute(query, (guild_id,))

            alliances = self.c.fetchall()

            alliance_list = ""
            for alliance_id, name, interval in alliances:
                
                self.c_users.execute("SELECT COUNT(*) FROM users WHERE alliance = ?", (alliance_id,))
                member_count = self.c_users.fetchone()[0]
                
                interval_text = f"{interval} minutes" if interval > 0 else "No automatic control"
                alliance_list += f"🛡️ **{alliance_id}: {name}**\n👥 Members: {member_count}\n⏱️ Control Interval: {interval_text}\n\n"

            if not alliance_list:
                alliance_list = "No alliances found."

            embed = discord.Embed(
                title="Existing Alliances",
                description=alliance_list,
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(
                "An error occurred while fetching alliances.", 
                ephemeral=True
            )

    async def alliance_autocomplete(self, interaction: discord.Interaction, current: str):
        self.c.execute("SELECT alliance_id, name FROM alliance_list")
        alliances = self.c.fetchall()
        return [
            app_commands.Choice(name=f"{name} (ID: {alliance_id})", value=str(alliance_id))
            for alliance_id, name in alliances if current.lower() in name.lower()
        ][:25]

    @app_commands.command(name="settings", description="Open settings menu.")
    async def settings(self, interaction: discord.Interaction):
        try:
            self.c_settings.execute("SELECT COUNT(*) FROM admin")
            admin_count = self.c_settings.fetchone()[0]

            user_id = interaction.user.id

            if admin_count == 0:
                self.c_settings.execute("""
                    INSERT INTO admin (id, is_initial) 
                    VALUES (?, 1)
                """, (user_id,))
                self.conn_settings.commit()

                first_use_embed = discord.Embed(
                    title="🎉 First Time Setup",
                    description=(
                        "This command has been used for the first time and no administrators were found.\n\n"
                        f"**{interaction.user.name}** has been added as the Global Administrator.\n\n"
                        "You can now access all administrative functions."
                    ),
                    color=discord.Color.green()
                )
                await interaction.response.send_message(embed=first_use_embed, ephemeral=True)
                
                await asyncio.sleep(3)
                
            self.c_settings.execute("SELECT id, is_initial FROM admin WHERE id = ?", (user_id,))
            admin = self.c_settings.fetchone()

            if admin is None:
                await interaction.response.send_message(
                    "You do not have permission to access this menu.", 
                    ephemeral=True
                )
                return

            embed = discord.Embed(
                title="⚙️ Settings Menu",
                description=(
                    "Please select a category:\n\n"
                    "**Menu Categories**\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\n"
                    "🏰 **Alliance Operations**\n"
                    "└ Manage alliances and settings\n\n"
                    "👥 **Alliance Member Operations**\n"
                    "└ Add, remove, and view members\n\n"
                    "🤖 **Bot Operations**\n"
                    "└ Configure bot settings\n\n"
                    "🎁 **Gift Code Operations**\n"
                    "└ Manage gift codes and rewards\n\n"
                    "📜 **Alliance History**\n"
                    "└ View alliance changes and history\n\n"
                    "🆘 **Support Operations**\n"
                    "└ Access support features\n"
                    "━━━━━━━━━━━━━━━━━━━━━━"
                ),
                color=discord.Color.blue()
            )
            
            view = discord.ui.View()
            view.add_item(discord.ui.Button(
                label="Alliance Operations",
                emoji="🏰",
                style=discord.ButtonStyle.primary,
                custom_id="alliance_operations",
                row=0
            ))
            view.add_item(discord.ui.Button(
                label="Member Operations",
                emoji="👥",
                style=discord.ButtonStyle.primary,
                custom_id="member_operations",
                row=0
            ))
            view.add_item(discord.ui.Button(
                label="Bot Operations",
                emoji="🤖",
                style=discord.ButtonStyle.primary,
                custom_id="bot_operations",
                row=1
            ))
            view.add_item(discord.ui.Button(
                label="Gift Operations",
                emoji="🎁",
                style=discord.ButtonStyle.primary,
                custom_id="gift_code_operations",
                row=1
            ))
            view.add_item(discord.ui.Button(
                label="Alliance History",
                emoji="📜",
                style=discord.ButtonStyle.primary,
                custom_id="alliance_history",
                row=2
            ))
            view.add_item(discord.ui.Button(
                label="Support Operations",
                emoji="🆘",
                style=discord.ButtonStyle.primary,
                custom_id="support_operations",
                row=2
            ))
            view.add_item(discord.ui.Button(
                label="Other Features",
                emoji="🔧",
                style=discord.ButtonStyle.primary,
                custom_id="other_features",
                row=3
            ))

            if admin_count == 0:
                await interaction.edit_original_response(embed=embed, view=view)
            else:
                await interaction.response.send_message(embed=embed, view=view)

        except Exception as e:
            print(f"Settings command error: {e}")
            error_message = "An error occurred while processing your request."
            if not interaction.response.is_done():
                await interaction.response.send_message(error_message, ephemeral=True)
            else:
                await interaction.followup.send(error_message, ephemeral=True)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type == discord.InteractionType.component:
            custom_id = interaction.data.get("custom_id")
            user_id = interaction.user.id
            self.c_settings.execute("SELECT id, is_initial FROM admin WHERE id = ?", (user_id,))
            admin = self.c_settings.fetchone()

            if admin is None:
                await interaction.response.send_message("You do not have permission to perform this action.", ephemeral=True)
                return

            try:
                if custom_id == "alliance_operations":
                    embed = discord.Embed(
                        title="🏰 Alliance Operations",
                        description=(
                            "Please select an operation:\n\n"
                            "**Available Operations**\n"
                            "━━━━━━━━━━━━━━━━━━━━━━\n"
                            "➕ **Add Alliance**\n"
                            "└ Create a new alliance\n\n"
                            "✏️ **Edit Alliance**\n"
                            "└ Modify existing alliance settings\n\n"
                            "🗑️ **Delete Alliance**\n"
                            "└ Remove an existing alliance\n\n"
                            "👀 **View Alliances**\n"
                            "└ List all available alliances\n"
                            "━━━━━━━━━━━━━━━━━━━━━━"
                        ),
                        color=discord.Color.blue()
                    )
                    
                    view = discord.ui.View()
                    view.add_item(discord.ui.Button(
                        label="Add Alliance", 
                        emoji="➕",
                        style=discord.ButtonStyle.success, 
                        custom_id="add_alliance", 
                        disabled=admin[1] != 1
                    ))
                    view.add_item(discord.ui.Button(
                        label="Edit Alliance", 
                        emoji="✏️",
                        style=discord.ButtonStyle.primary, 
                        custom_id="edit_alliance", 
                        disabled=admin[1] != 1
                    ))
                    view.add_item(discord.ui.Button(
                        label="Delete Alliance", 
                        emoji="🗑️",
                        style=discord.ButtonStyle.danger, 
                        custom_id="delete_alliance", 
                        disabled=admin[1] != 1
                    ))
                    view.add_item(discord.ui.Button(
                        label="View Alliances", 
                        emoji="👀",
                        style=discord.ButtonStyle.primary, 
                        custom_id="view_alliances"
                    ))
                    view.add_item(discord.ui.Button(
                        label="Main Menu", 
                        emoji="🏠",
                        style=discord.ButtonStyle.secondary, 
                        custom_id="main_menu"
                    ))

                    await interaction.response.edit_message(embed=embed, view=view)

                elif custom_id == "edit_alliance":
                    if admin[1] != 1:
                        await interaction.response.send_message("You do not have permission to perform this action.", ephemeral=True)
                        return
                    await self.edit_alliance(interaction)

                elif custom_id == "member_operations":
                    await self.bot.get_cog("AllianceMemberOperations").handle_member_operations(interaction)

                elif custom_id == "bot_operations":
                    try:
                        bot_ops_cog = interaction.client.get_cog("BotOperations")
                        if bot_ops_cog:
                            await bot_ops_cog.show_bot_operations_menu(interaction)
                        else:
                            await interaction.response.send_message(
                                "❌ Bot Operations module not found.",
                                ephemeral=True
                            )
                    except Exception as e:
                        print(f"Bot operations error: {e}")
                        if not interaction.response.is_done():
                            await interaction.response.send_message("An error occurred while loading Bot Operations.", ephemeral=True)
                        else:
                            await interaction.followup.send("An error occurred while loading Bot Operations.", ephemeral=True)

                elif custom_id == "gift_code_operations":
                    try:
                        gift_ops_cog = interaction.client.get_cog("GiftOperations")
                        if gift_ops_cog:
                            await gift_ops_cog.show_gift_menu(interaction)
                        else:
                            await interaction.response.send_message(
                                "❌ Gift Operations module not found.",
                                ephemeral=True
                            )
                    except Exception as e:
                        print(f"Gift operations error: {e}")
                        if not interaction.response.is_done():
                            await interaction.response.send_message(
                                "An error occurred while loading Gift Operations.",
                                ephemeral=True
                            )
                        else:
                            await interaction.followup.send(
                                "An error occurred while loading Gift Operations.",
                                ephemeral=True
                            )

                elif custom_id == "add_alliance":
                    if admin[1] != 1:
                        await interaction.response.send_message("You do not have permission to perform this action.", ephemeral=True)
                        return
                    await self.add_alliance(interaction)

                elif custom_id == "delete_alliance":
                    if admin[1] != 1:
                        await interaction.response.send_message("You do not have permission to perform this action.", ephemeral=True)
                        return
                    await self.delete_alliance(interaction)

                elif custom_id == "view_alliances":
                    await self.view_alliances(interaction)

                elif custom_id == "support_operations":
                    try:
                        support_ops_cog = interaction.client.get_cog("SupportOperations")
                        if support_ops_cog:
                            await support_ops_cog.show_support_menu(interaction)
                        else:
                            await interaction.response.send_message(
                                "❌ Destek Operasyonları modülü bulunamadı.",
                                ephemeral=True
                            )
                    except Exception as e:
                        print(f"Support operations error: {e}")
                        if not interaction.response.is_done():
                            await interaction.response.send_message(
                                "An error occurred while loading Support Operations.", 
                                ephemeral=True
                            )
                        else:
                            await interaction.followup.send(
                                "An error occurred while loading Support Operations.",
                                ephemeral=True
                            )

                elif custom_id == "alliance_history":
                    try:
                        changes_cog = interaction.client.get_cog("Changes")
                        if changes_cog:
                            await changes_cog.show_alliance_history_menu(interaction)
                        else:
                            await interaction.response.send_message(
                                "❌ Alliance History module not found.",
                                ephemeral=True
                            )
                    except Exception as e:
                        print(f"Alliance history error: {e}")
                        if not interaction.response.is_done():
                            await interaction.response.send_message(
                                "An error occurred while loading Alliance History.",
                                ephemeral=True
                            )
                        else:
                            await interaction.followup.send(
                                "An error occurred while loading Alliance History.",
                                ephemeral=True
                            )

                elif custom_id == "other_features":
                    try:
                        other_features_cog = interaction.client.get_cog("OtherFeatures")
                        if other_features_cog:
                            await other_features_cog.show_other_features_menu(interaction)
                        else:
                            await interaction.response.send_message(
                                "❌ Other Features module not found.",
                                ephemeral=True
                            )
                    except Exception as e:
                        print(f"Other features error: {e}")
                        if not interaction.response.is_done():
                            await interaction.response.send_message(
                                "An error occurred while loading Other Features menu.",
                                ephemeral=True
                            )
                        else:
                            await interaction.followup.send(
                                "An error occurred while loading Other Features menu.",
                                ephemeral=True
                            )

            except Exception as e:
                print(f"Error processing interaction with custom_id '{custom_id}': {e}")
                await interaction.response.send_message(
                    "An error occurred while processing your request. Please try again.",
                    ephemeral=True
                )

    async def add_alliance(self, interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message("Please perform this action in a Discord channel.", ephemeral=True)
            return

        modal = AllianceModal(title="Add Alliance")
        await interaction.response.send_modal(modal)
        await modal.wait()

        try:
            alliance_name = modal.name.value.strip()
            interval = int(modal.interval.value.strip())

            embed = discord.Embed(
                title="Channel Selection",
                description="Please select a channel for the alliance:",
                color=discord.Color.blue()
            )

            channels = interaction.guild.text_channels
            channel_options = [discord.SelectOption(label=channel.name, value=str(channel.id)) for channel in channels]

            select = discord.ui.Select(placeholder="Select a channel", options=channel_options)
            view = discord.ui.View()
            view.add_item(select)

            async def select_callback(select_interaction: discord.Interaction):
                try:
                    self.c.execute("SELECT alliance_id FROM alliance_list WHERE name = ?", (alliance_name,))
                    existing_alliance = self.c.fetchone()
                    
                    if existing_alliance:
                        error_embed = discord.Embed(
                            title="Error",
                            description="An alliance with this name already exists.",
                            color=discord.Color.red()
                        )
                        await select_interaction.response.edit_message(embed=error_embed, view=None)
                        return

                    channel_id = int(select.values[0])

                    self.c.execute("INSERT INTO alliance_list (name, discord_server_id) VALUES (?, ?)", 
                                 (alliance_name, interaction.guild.id))
                    alliance_id = self.c.lastrowid
                    self.c.execute("INSERT INTO alliancesettings (alliance_id, channel_id, interval) VALUES (?, ?, ?)", 
                                 (alliance_id, channel_id, interval))
                    self.conn.commit()

                    result_embed = discord.Embed(title="Alliance Created", color=discord.Color.green())
                    result_embed.add_field(name="Alliance", value=alliance_name, inline=False)
                    result_embed.add_field(name="Alliance ID", value=alliance_id, inline=False)
                    result_embed.add_field(name="Channel", value=f"<#{channel_id}>", inline=False)
                    result_embed.add_field(name="Interval", value=f"{interval} minutes", inline=False)
                    
                    await select_interaction.response.edit_message(embed=result_embed, view=None)
                except Exception as e:
                    error_embed = discord.Embed(
                        title="Error",
                        description=f"Error creating alliance: {str(e)}",
                        color=discord.Color.red()
                    )
                    await select_interaction.response.edit_message(embed=error_embed, view=None)

            select.callback = select_callback
            await modal.interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        except ValueError:
            error_embed = discord.Embed(
                title="Error",
                description="Invalid interval value. Please enter a number.",
                color=discord.Color.red()
            )
            await modal.interaction.response.send_message(embed=error_embed, ephemeral=True)
        except Exception as e:
            error_embed = discord.Embed(
                title="Error",
                description=f"Error: {str(e)}",
                color=discord.Color.red()
            )
            await modal.interaction.response.send_message(embed=error_embed, ephemeral=True)

    async def edit_alliance(self, interaction: discord.Interaction):
        self.c.execute("""
            SELECT a.alliance_id, a.name, s.interval, s.channel_id 
            FROM alliance_list a 
            LEFT JOIN alliancesettings s ON a.alliance_id = s.alliance_id
        """)
        alliances = self.c.fetchall()
        
        alliance_options = [
            discord.SelectOption(
                label=f"{name} (ID: {alliance_id})",
                value=f"{alliance_id}",
                description=f"Interval: {interval} minutes"
            ) for alliance_id, name, interval, _ in alliances
        ]
        
        select = discord.ui.Select(
            placeholder="Select alliance to edit", 
            options=alliance_options
        )
        view = discord.ui.View()
        view.add_item(select)

        async def select_callback(select_interaction: discord.Interaction):
            alliance_id = int(select.values[0])
            alliance_data = next(a for a in alliances if a[0] == alliance_id)
            
            modal = AllianceModal(
                title="Edit Alliance",
                default_name=alliance_data[1],
                default_interval=str(alliance_data[2])
            )
            await select_interaction.response.send_modal(modal)
            await modal.wait()

            try:
                alliance_name = modal.name.value.strip()
                interval = int(modal.interval.value.strip())

                embed = discord.Embed(
                    title="🔄 Channel Selection",
                    description=(
                        "**Current Channel Information**\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"📢 Current channel: <#{alliance_data[3]}>\n"
                        f"ℹ️ Select a new channel below\n"
                        "━━━━━━━━━━━━━━━━━━━━━━"
                    ),
                    color=discord.Color.blue()
                )

                channels = interaction.guild.text_channels
                channel_options = [
                    discord.SelectOption(
                        label=channel.name,
                        value=str(channel.id),
                        description="Current channel" if channel.id == alliance_data[3] else None,
                        emoji="📢" if channel.id == alliance_data[3] else "📝"
                    ) for channel in channels
                ]

                channel_select = discord.ui.Select(
                    placeholder="Select a new channel",
                    options=channel_options
                )
                channel_view = discord.ui.View()
                channel_view.add_item(channel_select)

                async def channel_select_callback(channel_interaction: discord.Interaction):
                    try:
                        channel_id = int(channel_select.values[0])

                        self.c.execute("UPDATE alliance_list SET name = ? WHERE alliance_id = ?", 
                                     (alliance_name, alliance_id))
                        self.c.execute("UPDATE alliancesettings SET channel_id = ?, interval = ? WHERE alliance_id = ?", 
                                     (channel_id, interval, alliance_id))
                        self.conn.commit()

                        result_embed = discord.Embed(
                            title="✅ Alliance Successfully Updated",
                            description="The alliance details have been updated as follows:",
                            color=discord.Color.green()
                        )
                        
                        info_section = (
                            f"**🛡️ Alliance Name**\n{alliance_name}\n\n"
                            f"**🔢 Alliance ID**\n{alliance_id}\n\n"
                            f"**📢 Channel**\n<#{channel_id}>\n\n"
                            f"**⏱️ Control Interval**\n{interval} minutes"
                        )
                        result_embed.add_field(name="Alliance Details", value=info_section, inline=False)
                        
                        result_embed.set_footer(text="Alliance settings have been successfully saved")
                        result_embed.timestamp = discord.utils.utcnow()
                        
                        await channel_interaction.response.edit_message(embed=result_embed, view=None)
                    except Exception as e:
                        error_embed = discord.Embed(
                            title="❌ Error",
                            description=(
                                "An error occurred while updating the alliance:\n"
                                f"```{str(e)}```"
                            ),
                            color=discord.Color.red()
                        )
                        error_embed.set_footer(text="Please try again later")
                        await channel_interaction.response.edit_message(embed=error_embed, view=None)

                channel_select.callback = channel_select_callback
                await modal.interaction.response.send_message(embed=embed, view=channel_view, ephemeral=True)

            except ValueError:
                error_embed = discord.Embed(
                    title="Error",
                    description="Invalid interval value. Please enter a number.",
                    color=discord.Color.red()
                )
                await modal.interaction.response.send_message(embed=error_embed, ephemeral=True)
            except Exception as e:
                error_embed = discord.Embed(
                    title="Error",
                    description=f"Error: {str(e)}",
                    color=discord.Color.red()
                )
                await modal.interaction.response.send_message(embed=error_embed, ephemeral=True)

        select.callback = select_callback
        await interaction.response.send_message("Select an alliance to edit:", view=view, ephemeral=True)

    async def delete_alliance(self, interaction: discord.Interaction):
        self.c.execute("SELECT alliance_id, name FROM alliance_list")
        alliances = self.c.fetchall()
        alliance_options = [discord.SelectOption(label=name, value=str(alliance_id)) for alliance_id, name in alliances]

        select = discord.ui.Select(placeholder="Select an alliance to delete", options=alliance_options)
        view = discord.ui.View()
        view.add_item(select)

        async def select_callback(select_interaction: discord.Interaction):
            try:
                alliance_id = int(select.values[0])
                self.c_users.execute("SELECT fid FROM users WHERE alliance = ?", (alliance_id,))
                members = self.c_users.fetchall()
                member_count = len(members)
                member_fids = [str(member[0]) for member in members]

                if member_count == 0:
                    embed = discord.Embed(
                        title="Confirm Deletion",
                        description="This alliance has no members. Do you want to delete it?",
                        color=discord.Color.red()
                    )
                    view = discord.ui.View()
                    view.add_item(discord.ui.Button(label="Confirm", style=discord.ButtonStyle.success, custom_id="confirm_delete"))
                    view.add_item(discord.ui.Button(label="Cancel", style=discord.ButtonStyle.danger, custom_id="cancel_delete"))

                    async def button_callback(button_interaction: discord.Interaction):
                        try:
                            if button_interaction.data["custom_id"] == "confirm_delete":
                                self.c.execute("DELETE FROM alliance_list WHERE alliance_id = ?", (alliance_id,))
                                self.c.execute("DELETE FROM alliancesettings WHERE alliance_id = ?", (alliance_id,))
                                self.conn.commit()
                                embed = discord.Embed(
                                    title="Alliance Deleted",
                                    description="The alliance has been successfully deleted.",
                                    color=discord.Color.green()
                                )
                                await button_interaction.response.edit_message(embed=embed, view=None)
                            elif button_interaction.data["custom_id"] == "cancel_delete":
                                embed = discord.Embed(
                                    title="Deletion Cancelled",
                                    description="The alliance deletion has been cancelled.",
                                    color=discord.Color.orange()
                                )
                                await button_interaction.response.edit_message(embed=embed, view=None)
                        except Exception as e:
                            print(f"Error in button_callback: {e}")
                            await button_interaction.response.send_message("An error occurred while processing your request.", ephemeral=True)

                    view.children[0].callback = button_callback
                    view.children[1].callback = button_callback
                    await select_interaction.response.send_message(embed=embed, view=view, ephemeral=True)
                else:
                    embed = discord.Embed(
                        title="Confirm Deletion",
                        description=f"This alliance has {member_count} members. If you confirm, these members will be deleted.",
                        color=discord.Color.red()
                    )
                    view = discord.ui.View()
                    view.add_item(discord.ui.Button(label="Confirm", style=discord.ButtonStyle.success, custom_id="confirm_delete"))
                    view.add_item(discord.ui.Button(label="Cancel", style=discord.ButtonStyle.danger, custom_id="cancel_delete"))

                    async def button_callback(button_interaction: discord.Interaction):
                        try:
                            if button_interaction.data["custom_id"] == "confirm_delete":
                                self.c_users.execute("DELETE FROM users WHERE alliance = ?", (alliance_id,))
                                self.conn_users.commit()
                                self.c.execute("DELETE FROM alliance_list WHERE alliance_id = ?", (alliance_id,))
                                self.c.execute("DELETE FROM alliancesettings WHERE alliance_id = ?", (alliance_id,))
                                self.conn.commit()
                                embed = discord.Embed(
                                    title="Alliance Deleted",
                                    description=f"The alliance and its members have been successfully deleted.\n\nTotal members: {member_count}\nMember FIDs: {', '.join(member_fids)}",
                                    color=discord.Color.green()
                                )
                                await button_interaction.response.edit_message(embed=embed, view=None)
                            elif button_interaction.data["custom_id"] == "cancel_delete":
                                embed = discord.Embed(
                                    title="Deletion Cancelled",
                                    description="The alliance deletion has been cancelled.",
                                    color=discord.Color.orange()
                                )
                                await button_interaction.response.edit_message(embed=embed, view=None)
                        except Exception as e:
                            print(f"Error in button_callback: {e}")
                            await button_interaction.response.send_message("An error occurred while processing your request.", ephemeral=True)

                    view.children[0].callback = button_callback
                    view.children[1].callback = button_callback
                    await select_interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            except Exception as e:
                print(f"Error in select_callback: {e}")
                await select_interaction.response.send_message("An error occurred while processing your request. Please try again.", ephemeral=True)

        select.callback = select_callback
        await interaction.response.send_message("Please select an alliance to delete:", view=view, ephemeral=True)

    async def handle_button_interaction(self, interaction: discord.Interaction):
        custom_id = interaction.data["custom_id"]
        
        if custom_id == "main_menu":
            embed = discord.Embed(
                title="⚙️ Settings Menu",
                description=(
                    "Please select a category:\n\n"
                    "**Menu Categories**\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\n"
                    "🏰 **Alliance Operations**\n"
                    "└ Manage alliances and settings\n\n"
                    "👥 **Alliance Member Operations**\n"
                    "└ Add, remove, and view members\n\n"
                    "🤖 **Bot Operations**\n"
                    "└ Configure bot settings\n\n"
                    "🎁 **Gift Code Operations**\n"
                    "└ Manage gift codes and rewards\n\n"
                    "📜 **Alliance History**\n"
                    "└ View alliance changes and history\n\n"
                    "🆘 **Support Operations**\n"
                    "└ Access support features\n"
                    "━━━━━━━━━━━━━━━━━━━━━━"
                ),
                color=discord.Color.blue()
            )
            
            view = discord.ui.View()
            view.add_item(discord.ui.Button(
                label="Alliance Operations",
                emoji="🏰",
                style=discord.ButtonStyle.primary,
                custom_id="alliance_operations",
                row=0
            ))
            view.add_item(discord.ui.Button(
                label="Member Operations",
                emoji="👥",
                style=discord.ButtonStyle.primary,
                custom_id="member_operations",
                row=0
            ))
            view.add_item(discord.ui.Button(
                label="Bot Operations",
                emoji="🤖",
                style=discord.ButtonStyle.primary,
                custom_id="bot_operations",
                row=1
            ))
            view.add_item(discord.ui.Button(
                label="Gift Operations",
                emoji="🎁",
                style=discord.ButtonStyle.primary,
                custom_id="gift_code_operations",
                row=1
            ))
            view.add_item(discord.ui.Button(
                label="Alliance History",
                emoji="📜",
                style=discord.ButtonStyle.primary,
                custom_id="alliance_history",
                row=2
            ))
            view.add_item(discord.ui.Button(
                label="Support Operations",
                emoji="🆘",
                style=discord.ButtonStyle.primary,
                custom_id="support_operations",
                row=2
            ))
            view.add_item(discord.ui.Button(
                label="Other Features",
                emoji="🔧",
                style=discord.ButtonStyle.primary,
                custom_id="other_features",
                row=3
            ))


            await interaction.response.edit_message(embed=embed, view=view)

        elif custom_id == "other_features":
            try:
                other_features_cog = interaction.client.get_cog("OtherFeatures")
                if other_features_cog:
                    await other_features_cog.show_other_features_menu(interaction)
                else:
                    await interaction.response.send_message(
                        "❌ Other Features module not found.",
                        ephemeral=True
                    )
            except Exception as e:
                print(f"Other features error: {e}")
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "An error occurred while loading Other Features menu.",
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        "An error occurred while loading Other Features menu.",
                        ephemeral=True
                    )

    async def show_main_menu(self, interaction: discord.Interaction):
        try:
            embed = discord.Embed(
                title="⚙️ Settings Menu",
                description=(
                    "Please select a category:\n\n"
                    "**Menu Categories**\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\n"
                    "🏰 **Alliance Operations**\n"
                    "└ Manage alliances and settings\n\n"
                    "👥 **Alliance Member Operations**\n"
                    "└ Add, remove, and view members\n\n"
                    "🤖 **Bot Operations**\n"
                    "└ Configure bot settings\n\n"
                    "🎁 **Gift Code Operations**\n"
                    "└ Manage gift codes and rewards\n\n"
                    "📜 **Alliance History**\n"
                    "└ View alliance changes and history\n\n"
                    "🆘 **Support Operations**\n"
                    "└ Access support features\n\n"
                    "🔧 **Other Features**\n"
                    "└ Access other features\n"
                    "━━━━━━━━━━━━━━━━━━━━━━"
                ),
                color=discord.Color.blue()
            )
            
            view = discord.ui.View()
            view.add_item(discord.ui.Button(
                label="Alliance Operations",
                emoji="🏰",
                style=discord.ButtonStyle.primary,
                custom_id="alliance_operations",
                row=0
            ))
            view.add_item(discord.ui.Button(
                label="Member Operations",
                emoji="👥",
                style=discord.ButtonStyle.primary,
                custom_id="member_operations",
                row=0
            ))
            view.add_item(discord.ui.Button(
                label="Bot Operations",
                emoji="🤖",
                style=discord.ButtonStyle.primary,
                custom_id="bot_operations",
                row=1
            ))
            view.add_item(discord.ui.Button(
                label="Gift Operations",
                emoji="🎁",
                style=discord.ButtonStyle.primary,
                custom_id="gift_code_operations",
                row=1
            ))
            view.add_item(discord.ui.Button(
                label="Alliance History",
                emoji="📜",
                style=discord.ButtonStyle.primary,
                custom_id="alliance_history",
                row=2
            ))
            view.add_item(discord.ui.Button(
                label="Support Operations",
                emoji="🆘",
                style=discord.ButtonStyle.primary,
                custom_id="support_operations",
                row=2
            ))
            view.add_item(discord.ui.Button(
                label="Other Features",
                emoji="🔧",
                style=discord.ButtonStyle.primary,
                custom_id="other_features",
                row=3
            ))

            try:
                await interaction.response.edit_message(embed=embed, view=view)
            except discord.InteractionResponded:
                pass
                
        except Exception as e:
            pass

    @discord.ui.button(label="Bot Operations", emoji="🤖", style=discord.ButtonStyle.primary, custom_id="bot_operations", row=1)
    async def bot_operations_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            bot_ops_cog = interaction.client.get_cog("BotOperations")
            if bot_ops_cog:
                await bot_ops_cog.show_bot_operations_menu(interaction)
            else:
                await interaction.response.send_message(
                    "❌ Bot Operations module not found.",
                    ephemeral=True
                )
        except Exception as e:
            print(f"Bot operations button error: {e}")
            await interaction.response.send_message(
                "❌ An error occurred. Please try again.",
                ephemeral=True
            )

class AllianceModal(discord.ui.Modal):
    def __init__(self, title: str, default_name: str = "", default_interval: str = "0"):
        super().__init__(title=title)
        
        self.name = discord.ui.TextInput(
            label="Alliance Name",
            placeholder="Enter alliance name",
            default=default_name,
            required=True
        )
        self.add_item(self.name)
        
        self.interval = discord.ui.TextInput(
            label="Control Interval (minutes)",
            placeholder="Enter interval (0 to disable)",
            default=default_interval,
            required=True
        )
        self.add_item(self.interval)

    async def on_submit(self, interaction: discord.Interaction):
        self.interaction = interaction

class AllianceView(discord.ui.View):
    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    @discord.ui.button(
        label="Main Menu",
        emoji="🏠",
        style=discord.ButtonStyle.secondary,
        custom_id="main_menu"
    )
    async def main_menu_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.show_main_menu(interaction)

class MemberOperationsView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    async def get_admin_alliances(self, user_id, guild_id):
        self.cog.c_settings.execute("SELECT id, is_initial FROM admin WHERE id = ?", (user_id,))
        admin = self.cog.c_settings.fetchone()
        
        if admin is None:
            return []
            
        is_initial = admin[1]
        
        if is_initial == 1:
            self.cog.c.execute("SELECT alliance_id, name FROM alliance_list ORDER BY name")
        else:
            self.cog.c.execute("""
                SELECT alliance_id, name 
                FROM alliance_list 
                WHERE discord_server_id = ? 
                ORDER BY name
            """, (guild_id,))
            
        return self.cog.c.fetchall()

    @discord.ui.button(label="Add Member", emoji="➕", style=discord.ButtonStyle.primary, custom_id="add_member")
    async def add_member_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            alliances = await self.get_admin_alliances(interaction.user.id, interaction.guild.id)
            if not alliances:
                await interaction.response.send_message("İttifak üyesi ekleme yetkiniz yok.", ephemeral=True)
                return

            options = [
                discord.SelectOption(
                    label=f"{name}",
                    value=str(alliance_id),
                    description=f"İttifak ID: {alliance_id}"
                ) for alliance_id, name in alliances
            ]

            select = discord.ui.Select(
                placeholder="Bir ittifak seçin",
                options=options,
                custom_id="alliance_select"
            )

            view = discord.ui.View()
            view.add_item(select)

            await interaction.response.send_message(
                "Üye eklemek istediğiniz ittifakı seçin:",
                view=view,
                ephemeral=True
            )

        except Exception as e:
            print(f"Error in add_member_button: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "An error occurred during the process of adding a member.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "An error occurred during the process of adding a member.",
                    ephemeral=True
                )

    @discord.ui.button(label="Remove Member", emoji="➖", style=discord.ButtonStyle.danger, custom_id="remove_member")
    async def remove_member_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            alliances = await self.get_admin_alliances(interaction.user.id, interaction.guild.id)
            if not alliances:
                await interaction.response.send_message("You are not authorized to delete alliance members.", ephemeral=True)
                return

            options = [
                discord.SelectOption(
                    label=f"{name}",
                    value=str(alliance_id),
                    description=f"Alliance ID: {alliance_id}"
                ) for alliance_id, name in alliances
            ]

            select = discord.ui.Select(
                placeholder="Choose an alliance",
                options=options,
                custom_id="alliance_select_remove"
            )

            view = discord.ui.View()
            view.add_item(select)

            await interaction.response.send_message(
                "Select the alliance you want to delete members from:",
                view=view,
                ephemeral=True
            )

        except Exception as e:
            print(f"Error in remove_member_button: {e}")
            await interaction.response.send_message(
                "An error occurred during the member deletion process.",
                ephemeral=True
            )

    @discord.ui.button(label="View Members", emoji="👥", style=discord.ButtonStyle.primary, custom_id="view_members")
    async def view_members_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            alliances = await self.get_admin_alliances(interaction.user.id, interaction.guild.id)
            if not alliances:
                await interaction.response.send_message("You are not authorized to screen alliance members.", ephemeral=True)
                return

            options = [
                discord.SelectOption(
                    label=f"{name}",
                    value=str(alliance_id),
                    description=f"Alliance ID: {alliance_id}"
                ) for alliance_id, name in alliances
            ]

            select = discord.ui.Select(
                placeholder="Choose an alliance",
                options=options,
                custom_id="alliance_select_view"
            )

            view = discord.ui.View()
            view.add_item(select)

            await interaction.response.send_message(
                "Select the alliance whose members you want to view:",
                view=view,
                ephemeral=True
            )

        except Exception as e:
            print(f"Error in view_members_button: {e}")
            await interaction.response.send_message(
                "An error occurred while viewing the member list.",
                ephemeral=True
            )

    @discord.ui.button(label="Main Menu", emoji="🏠", style=discord.ButtonStyle.secondary, custom_id="main_menu")
    async def main_menu_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await self.cog.show_main_menu(interaction)
        except Exception as e:
            print(f"Error in main_menu_button: {e}")
            await interaction.response.send_message(
                "An error occurred during return to the main menu.",
                ephemeral=True
            )

async def setup(bot):
    conn = sqlite3.connect('db/alliance.sqlite')
    await bot.add_cog(Alliance(bot, conn))
