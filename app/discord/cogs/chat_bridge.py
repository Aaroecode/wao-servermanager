import discord
from discord.ext import commands
from app.services.minecraft_rcon import rcon
import aiohttp
import os, json



CHAT_CHANNEL_ID = int(os.getenv("DISCORD_CHAT_CHANNEL_ID", 1439299001487720609))
MC_WEBHOOK_URL = os.getenv("MINECRAFT_CHAT_WEBHOOK_URL")

class ChatBridge(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        
        if message.author.bot:
            return
        
        if str(message.channel.id) == str(CHAT_CHANNEL_ID):
            message_content = self.sanitize_discord_message(message)
            user_color = message.author.color if message.author.color.value != 0 else discord.Color.default()
            user_color = f"#{user_color.value:06X}"

            print(user_color)
            message = ["",{"text":"[","bold":True,"color":"dark_gray"},{"text":"ᴅɪꜱᴄᴏʀᴅ","bold":True,"color":"aqua"},{"text":"] ","bold":True,"color":"dark_gray"},
                       {"text":message.author.display_name,"color":user_color},{"text":": ","bold":True,"color":"dark_gray"},
                       {"text":message_content,"color":"white"}]
            await rcon.run_raw(f"tellraw @a {json.dumps(message)}") 
            return


    @staticmethod
    def sanitize_discord_message(message: discord.Message) -> str:
        text = message.content


        for user in message.mentions:
            text = text.replace(f"<@{user.id}>", f"@{user.display_name}")
            text = text.replace(f"<@!{user.id}>", f"@{user.display_name}")


        for role in message.role_mentions:
            text = text.replace(f"<@&{role.id}>", f"@{role.name}")


        for channel in message.channel_mentions:
            text = text.replace(f"<#{channel.id}>", f"#{channel.name}")

        return text

async def setup(bot):
    await bot.add_cog(ChatBridge(bot))
