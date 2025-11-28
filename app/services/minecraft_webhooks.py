from app.utils import state
from app.utils.decorators import event_handler
from app.utils.mcapi import track_player_count, update_discord_activity
from app.utils.fetch_uuid import get_uuid_from_username
from app.services.discord_webhook import discord_webhook_client
from app.models.discord_user import DiscordUser
import discord
from discord_client import client

import time



start_time = time.time()

@event_handler.mc_webhook("server_start")
async def server_start(data):
    await track_player_count()



@event_handler.mc_webhook("player_login")
async def player_login(data):
    state.players_online += 1
    await update_discord_activity()

    embed = discord.Embed(
        title=f"➕ **{data.get('player')}** has joined the server.", color=discord.Color.green())
    await discord_webhook_client.send_message(
        avatar_url="https://avatarfiles.alphacoders.com/361/thumb-350-361759.webp",
        embeds=[embed.to_dict()])

@event_handler.mc_webhook("player_quit")
async def player_leave(data):
    state.players_online -= 1
    await update_discord_activity()

    embed = discord.Embed(
        title=f"➖ **{data.get('player')}** has left the server.", color=discord.Color.red())
    await discord_webhook_client.send_message(
        avatar_url="https://avatarfiles.alphacoders.com/361/thumb-350-361759.webp",
        embeds=[embed.to_dict()])

@event_handler.mc_webhook("server_stop")
async def server_stop(data):
    offline_activity = discord.Activity(
        type=discord.ActivityType.playing,
        name="Weapon Art Online 🔴",
        state="Server Offline",
    )
    await client.change_presence(
        status=discord.Status.idle,
        activity=offline_activity
    )

@event_handler.mc_webhook("player_command")
async def player_command(data):
    username = data.get("player")
    command = data.get("command")
    print(f"{username} executed command: {command}")
    await event_handler.call_command(data)

    
@event_handler.mc_webhook("player_chat")
async def player_chat(data):
    username = data.get("player")
    message = data.get("message")
    discord_user = await DiscordUser.get_by(mc_username=username)
    if discord_user and discord_user.id:
        discord_member = client.get_user(discord_user.id)
        if discord_member:
            name = discord_member.display_name
            avatar_url = discord_member.display_avatar.url
            await discord_webhook_client.send_message(
                content=message,
                username=name,
                avatar_url=avatar_url
            )
    else:
        uuid = await get_uuid_from_username(username)
        await discord_webhook_client.send_message(
            content=message,
            username=username,
            avatar_url=f"https://minotar.net/helm/{uuid}/128.png"
        )

            


