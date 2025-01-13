import discord
from discord.ext import commands
import sqlite3

class OtherFeatures(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def show_other_features_menu(self, interaction: discord.Interaction):
        try:
            embed = discord.Embed(
                title="🔧 Other Features",
                description=(
                    "**Upcoming Features**\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    "This section will be filled with features you request, "
                    "new features will be gradually added here through automatic updates.\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━"
                ),
                color=discord.Color.blue()
            )

            view = OtherFeaturesView(self)
            
            if interaction.response.is_done():
                await interaction.message.edit(embed=embed, view=view)
            else:
                await interaction.response.edit_message(embed=embed, view=view)

        except Exception as e:
            print(f"Error showing other features menu: {e}")
            error_message = "An error occurred while displaying the menu."
            if not interaction.response.is_done():
                await interaction.response.send_message(error_message, ephemeral=True)
            else:
                await interaction.followup.send(error_message, ephemeral=True)

class OtherFeaturesView(discord.ui.View):
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
        try:
            alliance_cog = self.cog.bot.get_cog("Alliance")
            if alliance_cog:
                await alliance_cog.show_main_menu(interaction)
            else:
                await interaction.response.send_message(
                    "Error: Alliance module not found.",
                    ephemeral=True
                )
        except Exception as e:
            print(f"Error in main menu button: {e}")
            await interaction.response.send_message(
                "An error occurred while returning to the main menu.",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(OtherFeatures(bot)) 