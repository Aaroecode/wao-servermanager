import discord
from discord.ext import commands
from discord import app_commands

from app.utils.state import otp_cache
from app.utils.fetch_uuid import get_uuid_from_username
from app.models.discord_user import DiscordUser

import time

VERIFIED_ROLE_ID = 1439288303277965313   
COOLDOWN_SECONDS = 10                






class Test(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="test", description="Test")
    @app_commands.guilds(discord.Object(id=1114580786176348231))
    async def test(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        role = interaction.guild.get_role(VERIFIED_ROLE_ID)

        try:
            if role:
                await interaction.user.add_roles(role, reason="Testing")
        except Exception as e:
            print(f"Error adding role: {e}")

        await interaction.followup.send(
            f"Added role ID {role.name} to user {interaction.user.mention}.",
            ephemeral=True
        )




async def setup(bot):
    await bot.add_cog(Test(bot))
