import discord
import asyncio
from discord.ext import commands
from discord import app_commands
from app.discord.cogs.tickets import TicketPanel
import os

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True
intents.message_content = True

client = commands.Bot(
    command_prefix="!",
    intents=intents,
)

tree = client.tree
ready_event = asyncio.Event()  


async def load_cogs():
    print("Loading Discord cogs...")

    cogs_folder = os.path.join(os.getcwd(), "app", "discord", "cogs")

    for file in os.listdir(cogs_folder):
        if file.endswith(".py") and not file.startswith("_"):
            module_path = f"app.discord.cogs.{file[:-3]}"
            await client.load_extension(module_path)


@client.event
async def on_ready():
    guild_id = 1114580786176348231  
    synced = await tree.sync(guild=discord.Object(id=guild_id))
    print(f"Synced {len(synced)} slash commands")
    print(f"Discord bot logged in as {client.user}")
    
    
    
    


    ready_event.set()  # tell FastAPI that Discord bot is ready
