from app.utils.decorators import event_handler
from app.services.minecraft_rcon import rcon
from app.utils.state import otp_cache, toke_timeout
from app.models.discord_user import DiscordUser
import os, json, random, string



discord_invite = os.getenv("DISCORD_INVITE")


@event_handler.command_event("syncdiscord")
async def syncdiscord(data):

    user = await DiscordUser.get_by(mc_username=data.get("player"))
    if user:
        
        message = f"&7Your Minecraft account is already linked to your Discord\naccount &b&l@{user.username}&r&7"
        command = f'tellraw {data.get("player")} {json.dumps(["",{"text":" "},{"text":"\n"},{"text":" "},{"text":"\n"},{"text":message,"color":"gray"},{"text":"\n"},{"text":" "},{"text":"\n"},{"text":" "}])}'
        print(command)
        res = await rcon.run_raw(command)
        return None
    
    username = data.get("player")
    otp = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    otp_cache[username] = otp
    print(otp)
    message = ["",{"text":" "},
               {"text":"\n"},
               {"text":" "},
               {"text":"\n"},
               {"text":"ʏᴏᴜʀ ᴛᴏᴋᴇɴ ɪꜱ:  ","color":"gray"},{"text":otp,"bold":True,"color":"dark_red"},{"text":"\n"},
               {"text":"ᴄʟɪᴄᴋ ʜᴇʀᴇ","bold":True,"underlined":True,"color":"dark_green","clickEvent":{"action":"copy_to_clipboard","value":otp}},{"text":" ᴛᴏ ᴄᴏᴘʏ ᴛᴏᴋᴇɴ ᴛᴏ ᴄʟɪᴘʙᴏᴀʀᴅ","color":"gray"},{"text":"\n"},
               {"text":"ᴛʜɪꜱ ᴛᴏᴋᴇɴ ɪꜱ ᴠᴀʟɪᴅ ꜰᴏʀ ","color":"gray"},{"text":str(toke_timeout)+" ꜱᴇᴄᴏɴᴅꜱ.","color":"blue"},{"text":"\n"},
               {"text":"ᴄʟɪᴄᴋ ʜᴇʀᴇ","bold":True,"underlined":True,"color":"dark_green","clickEvent":{"action":"open_url","value":discord_invite}},{"text":" ᴛᴏ ᴊᴏɪɴ ᴏᴜʀ ᴅɪꜱᴄᴏʀᴅ ꜱᴇʀᴠᴇʀ.","color":"gray"},
               {"text":"\n"},
               {"text":" "},
               {"text":"\n"},
               {"text":" "}]
    command = f"tellraw {username} {json.dumps(message)}"
    
    res = await rcon.run_raw(command)
    print(res)

    
