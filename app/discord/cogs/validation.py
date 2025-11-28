import discord
from discord import app_commands
from discord.ext import commands
from app.models.discord_user import DiscordUser
import time




class ValidationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    

    @app_commands.command(name="validate", description="Integrate database for whole server")
    @app_commands.guilds(discord.Object(id=1114580786176348231))  
    @app_commands.describe(roles="Verify roles integrity")
    @app_commands.checks.has_permissions(administrator=True)
    async def validate(self, interaction: discord.Interaction, roles: str = None):
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send("Validation process started...")

        try:

            for member in interaction.guild.members:
                if member.bot:
                    continue

                user = await DiscordUser.get(member.id)
                if not user:
                    await DiscordUser.create(
                        id = member.id,
                        username = member.name,
                        mc_username = None,
                        mc_uuid = None,
                        mc_token = None,
                        verified = 0,
                        date_joined = time.time(),
                        last_seen = None,
                        is_banned = 0,
                        is_muted = 0,
                        roles_id = [],
                        status_list = [],
                        inventory = {},
                        settings = {},
                        notes = ""

                    )
                    user = await DiscordUser.get(member.id)


                # Validate roles
                if roles == "check":
                    if roles == "check":
                        current_roles = set(user.roles_id)
                        member_roles = {role.id for role in member.roles}
                        updated = current_roles | member_roles
                        user.roles_id = list(updated)

                    await user.save()

            await interaction.followup.send("Validation process completed.", ephemeral=True)
        except Exception as e:
            print(e)


async def setup(bot):
    await bot.add_cog(ValidationCog(bot))