

import os, aiohttp, discord, asyncio, json
from typing import Union
from discord_client import client
from app.utils import state



from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv("MCAPI_KEY")
BASE_URL = "http://85.202.160.193:7000"

async def api_request(endpoint: str, method: str = "GET", data: dict = None, params: dict = None):
    url = f"{BASE_URL}{endpoint}"
    headers = {
        "accept": "application/json",
        "Authorization": API_KEY
    }
    async with aiohttp.ClientSession() as session:
        async with session.request(method=method.upper(), url=url, headers=headers, json=data, params=params) as response:
            response.raise_for_status()
            return await response.json()



async def send_message(username: str, message: Union[str, list]):
    command = f"tellraw {username} {json.dumps(message)}"
    # command = json.dumps(command)
    print(command)
    response = await api_request("/v1/server/exec", method="POST", params={"command": command})
    print(response)


async def players():
    response = await api_request("/v1/server", method="GET")
    playersOnline = response.get("onlinePlayers", 0)
    maxPlayers = response.get("maxPlayers", 20)

    return playersOnline, maxPlayers





async def update_discord_activity():
    activity = discord.Activity(
        type=discord.ActivityType.streaming,
        name=f"🟢 {state.players_online}/{state.max_players} Players",
        state=f"🌍 play.weaponart.online",
        platform="Twitch",
        url="https://weaponart.online/",
    )

    await client.change_presence(
        status=discord.Status.online,
        activity=activity
        )


async def track_player_count():
    try:
        state.players_online, state.max_players = await players()
        await update_discord_activity()
        print(f"✅ Presence updated: {state.players_online}/{state.max_players} players online")
    except Exception as e:
        print(f"⚠️ Player tracker error: {e}")
        offline_activity = discord.Activity(
            type=discord.ActivityType.playing,
            name="Weapon Art Online 🔴",
            state="Server Offline",
        )
        await client.change_presence(
            status=discord.Status.idle,
            activity=offline_activity
        )
        print("🔴 Server appears offline. Stopping tracker loop.")


        