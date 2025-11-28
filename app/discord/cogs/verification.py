import discord
from discord.ext import commands
from discord import app_commands

from app.utils.state import otp_cache
from app.utils.fetch_uuid import get_uuid_from_username
from app.models.discord_user import DiscordUser

import time

VERIFIED_ROLE_ID = 1439288303277965313  
COOLDOWN_SECONDS = 10                


last_used_sync = {}



class ConfirmSyncView(discord.ui.View):
    def __init__(self, mc_username: str, interaction: discord.Interaction):
        super().__init__(timeout=120)
        self.mc_username = mc_username
        self.interaction = interaction
        self.value = None

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.interaction.user:
            await interaction.response.send_message(
                "❌ This confirmation is not for you.", ephemeral=True)
            return

        self.value = True
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.interaction.user:
            await interaction.response.send_message(
                "❌ This confirmation is not for you.", ephemeral=True)
            return

        self.value = False
        self.stop()
        await interaction.response.defer()




class VerificationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot



    @app_commands.command(name="sync", description="Link your Minecraft account with Discord")
    @app_commands.guilds(discord.Object(id=1114580786176348231))
    @app_commands.describe(code="Verification code from Minecraft")
    async def sync(self, interaction: discord.Interaction, code: str):

        mc_username = None
        for user, token in otp_cache.items():
            if token == code:
                mc_username = user
                break

        if mc_username is None:
            await interaction.response.send_message(
                "❌ Invalid or expired **verification code**.",
                ephemeral=True
            )
            return

        uuid = await get_uuid_from_username(mc_username)
        avatar_url = f"https://minotar.net/helm/{uuid}/128.png"


        embed = discord.Embed(
            title="Confirm Minecraft Account Link",
            description=f"Details of Minecraft account to be linked:\n\n"
                        f"Minecraft Username:\n"
                        f"**{mc_username}**\n"
                        f"UUID:\n"
                        f"**`{uuid}`**\n\n"
                        f"Click **Confirm** if this is correct.",
            color=discord.Color.blurple()
        )
        embed.set_thumbnail(url=avatar_url)

        view = ConfirmSyncView(mc_username, interaction)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        await view.wait()

        # timeout
        if view.value is None:
            await interaction.followup.send("⏳ Timeout. Please run `/sync` again.", ephemeral=True)
            return

        # cancelled
        if view.value is False:
            await interaction.followup.send("❌ Sync cancelled.", ephemeral=True)
            return

        discord_id = interaction.user.id
        username = interaction.user.name

        existing = await DiscordUser.get(discord_id)

        if existing:
            existing.mc_username = mc_username
            existing.mc_uuid = uuid
            existing.verified = 1
            existing.mc_token = code
            await existing.save()
        else:
            await DiscordUser.create(
                id=discord_id,
                username=username,
                mc_uuid=uuid,
                mc_username=mc_username,
                mc_token=code,
                verified=1,
                roles_id=[],
                status_list=[],
                inventory={},
                settings={},
                is_banned=0,
                is_muted=0
            )


        role = interaction.guild.get_role(VERIFIED_ROLE_ID)
        if role:
            await interaction.user.add_roles(role, reason="Account verified")


        try:
            embed_dm = discord.Embed(
                title="🎉 Account Linked Successfully!",
                description=f"Your Discord account is now linked to **{mc_username}**!",
                color=discord.Color.green()
            )
            embed_dm.set_thumbnail(url=avatar_url)
            await interaction.user.send(embed=embed_dm)
        except discord.Forbidden:
            embed = discord.Embed(
                title="🎉 Account Linked Successfully!",
                description=f"Your Discord account is now linked to **{mc_username}**!",
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=avatar_url)
            await interaction.followup.send(embed=embed, ephemeral=True)


        del otp_cache[mc_username]

        # await interaction.followup.send(
        #     f"✅ Successfully linked with **{mc_username}**!",
        #     ephemeral=True
        # )

    @app_commands.command(name="unsync", description="Unlink your Minecraft account with Discord")
    @app_commands.guilds(discord.Object(id=1114580786176348231))
    # @app_commands.describe(code="Verification code from Minecraft")
    async def unsync(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        discord_id = interaction.user.id
        now = time.time()
        existing = await DiscordUser.get(discord_id)
        print(time.time()-now)

        if not existing or existing.verified == 0:
            await interaction.followup.send(
                "❌ Your Discord account is not linked to any Minecraft account.",
                ephemeral=True
            )
            return

        mc_username = existing.mc_username

        existing.mc_username = ""
        existing.verified = 0
        await existing.save()

        role = interaction.guild.get_role(VERIFIED_ROLE_ID)
        if role:
            await interaction.user.remove_roles(role, reason="Account unlinked")

        await interaction.followup.send(
            f"✅ Successfully unlinked from **{mc_username}**!",
            ephemeral=True
        )




async def setup(bot):
    await bot.add_cog(VerificationCog(bot))
