import aiohttp, os


class WebhookClient:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self.session: aiohttp.ClientSession | None = None

    async def start(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()

    async def stop(self):
        if self.session:
            await self.session.close()
            self.session = None

    async def send_message(
        self,
        content: str = None,
        username: str = None,
        avatar_url: str = None,
        embeds: list = None
    ):
        if self.session is None:
            raise RuntimeError("WebhookClient not started. Call .start() first.")

        payload = {}
        if content:
            payload["content"] = content
        if username:
            payload["username"] = username
        if avatar_url:
            payload["avatar_url"] = avatar_url
        if embeds:
            payload["embeds"] = embeds

        async with self.session.post(self.webhook_url, json=payload) as resp:
            return resp.status

discord_webhook_client = WebhookClient(os.getenv("DISCORD_WEBHOOK_URL"))