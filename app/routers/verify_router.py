import aiohttp
import os

MINECRAFT_WEBHOOK_URL = os.getenv("MINECRAFT_CHAT_WEBHOOK_URL")

async def send_mc_message(message: str):
    if not MINECRAFT_WEBHOOK_URL:
        return
    async with aiohttp.ClientSession() as session:
        await session.post(MINECRAFT_WEBHOOK_URL, json={"message": message})
