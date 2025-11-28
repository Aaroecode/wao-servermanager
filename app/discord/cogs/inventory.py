from discord.ext import commands
from discord import app_commands
from app.models.discord_user import DiscordUser
from app.models.inventory import Inventory
from app.models.items import Item
import discord
import os



class InventoryCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    
    @app_commands.command(name="inventory", description="View your inventory")
    @app_commands.guilds(discord.Object(id=1114580786176348231))
    async def inventory(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        embed = discord.Embed(title="Inventory", color=discord.Color.blue())
        user_inventory = await Inventory.all(interaction.user.id)
        if not user_inventory:
            await interaction.followup.send("Your inventory is empty.", ephemeral=True)
            return
        await interaction.followup.send(user_inventory, ephemeral=True)
    

    @app_commands.command(name="give", description="give item to a user")
    @app_commands.guilds(discord.Object(id=1114580786176348231))
    @app_commands.describe(user="The user to give the item to", item_name="The name of the item", quantity="The quantity to give")
    @app_commands.checks.has_permissions(administrator=True)
    async def give(self, interaction: discord.Interaction, user: discord.Member, item_name: str, quantity: int = 1):
        await interaction.response.defer(ephemeral=True)

        item = await Item.get_by(item_name=item_name)
        if not item:
            await interaction.followup.send(f"Item '{item_name}' not found.", ephemeral=True)
            return

        discord_user = await DiscordUser.get(user.id)
        if not discord_user:
            await interaction.followup.send(f"User '{user.display_name}' not found in the database.", ephemeral=True)
            return

        user_inventory = Inventory.get(user.id)
        if item.item_name in user_inventory:
            user_inventory[item.item_name]["quantity"] += quantity
        else:
            user_inventory[item.item_name] = {
                "item_id": item.item_id,
                "quantity": quantity,
                "item_lore": item.item_lore,
                "item_meta": item.item_meta,
                "mc_command": item.mc_command
            }
        
        discord_user.inventory = user_inventory
        await discord_user.save()

        await interaction.followup.send(f"Gave {quantity} '{item.item_name}' to {user.display_name}.", ephemeral=True)







async def setup(bot):
    await bot.add_cog(InventoryCog(bot))