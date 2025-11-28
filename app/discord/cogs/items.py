from app.models.items import Item
from discord import app_commands
from discord.ext import commands
import discord


class ItemsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    

    @app_commands.command(name="list_items", description="List all available items")
    @app_commands.guilds(discord.Object(id=1114580786176348231))
    async def list_items(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        items = await Item.all()
        if not items:
            await interaction.followup.send("No items available.")
            return

        item_list = "\n".join([f"{item.item_id}- {item.item_name}: {item.item_lore}" for item in items])
        await interaction.followup.send(f"Available Items:\n{item_list}", ephemeral=True)
    

    @app_commands.command(name="build_item", description="build an item")
    @app_commands.guilds(discord.Object(id=1114580786176348231))
    @app_commands.describe(name="Name of the item", lore="Lore/description of the item", command="Minecraft command to grant the item")
    @app_commands.checks.has_permissions(administrator=True)
    async def build_item(self, interaction: discord.Interaction, name: str, lore: str = None, command: str =None):
        await interaction.response.defer(ephemeral=True)

        item = await Item.create(
            item_name=name,
            item_lore=lore,
            item_meta="{}",
            mc_command=command
        )

        await interaction.followup.send(f"Item '{item.item_name}' created successfully.", ephemeral=True)
    

    @app_commands.command(name="remove_item", description="Remove an item by its ID")
    @app_commands.guilds(discord.Object(id=1114580786176348231))
    @app_commands.describe(item_id="ID of the item to remove")
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_item(self, interaction: discord.Interaction, item_id: int):
        await interaction.response.defer(ephemeral=True)

        item = await Item.get(item_id)
        if not item:
            await interaction.followup.send(f"No item found with ID {item_id}.", ephemeral=True)
            return

        await item.delete()
        await interaction.followup.send(f"Item '{item.item_name}' removed successfully.", ephemeral=True)
    

    @app_commands.command(name="view_item", description="View details of an item by its ID")
    @app_commands.guilds(discord.Object(id=1114580786176348231))
    @app_commands.describe(item_name="Name of the item to view")
    async def view_item(self, interaction: discord.Interaction, item_name: str):
        await interaction.response.defer(ephemeral=True)

        item = await Item.get_by(item_name=item_name)
        if not item:
            await interaction.followup.send(f"No item found with name '{item_name}'.", ephemeral=True)
            return

        item_info = f"Item Name: {item.item_name}\nItem Lore: {item.item_lore}\nMinecraft Command: {item.mc_command}"
        await interaction.followup.send(item_info, ephemeral=True)
    









async def setup(bot):
    await bot.add_cog(ItemsCog(bot))