import aiohttp

async def get_uuid_from_username(username: str) -> str | None:
    """
    Returns the UUID (no hyphens) for a Minecraft username.
    Returns None if username does not exist.
    """

    url = f"https://api.mojang.com/users/profiles/minecraft/{username}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("id")  # UUID without hyphens
                else:
                    return None
    except:
        return None
