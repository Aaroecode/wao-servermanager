import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DISCORD_CHAT_CHANNEL_ID = int(os.getenv("DISCORD_CHAT_CHANNEL_ID", 0))
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data.db")
