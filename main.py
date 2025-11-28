from app.services.minecraft_webhooks import event_handler
from app.services.minecraft_commands import event_handler
from app.services.discord_webhook import discord_webhook_client
from app.services.minecraft_rcon import rcon
from app.database.db_service import db
from fastapi import FastAPI
from app.services.minecraft_webhooks import server_start


import asyncio, os, uvicorn, threading
from dotenv import load_dotenv
load_dotenv()

from discord_client import client
from discord_client import load_cogs, ready_event
from app.routers.mc_router import router as mc_router
# from app.mc.store_router import router as store_router
# from routers.verify_router import router as verify_router
# from app.core.database import init_db

app = FastAPI(title="Minecraft-Discord Bridge")

from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Register FastAPI routes
app.include_router(mc_router, tags=["Minecraft Webhooks"])
# app.include_router(store_router, prefix="/store", tags=["Store"])
# app.include_router(verify_router, prefix="/verify", tags=["Verification"])








async def start_discord():
    await load_cogs()
    await client.start(os.getenv("DISCORD_BOT_TOKEN"))

def _run_discord():
    asyncio.run(start_discord())


@app.on_event("startup")
async def on_startup():
    db.start(loop=asyncio.get_running_loop())
    threading.Thread(target=_run_discord, daemon=True).start()
    asyncio.create_task(ready_event.wait())
    await rcon.start()
    await discord_webhook_client.start()
    asyncio.create_task(server_start({})) 



@app.on_event("shutdown")
async def on_shutdown():
    await rcon.stop()
    db.stop()
    try:
        await client.close()
    except:
        pass




if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=7001)
