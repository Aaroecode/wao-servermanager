from cachetools import TTLCache

toke_timeout = 60  # seconds

otp_cache = TTLCache(maxsize=100, ttl=toke_timeout)

roles = {}

players_online = 0
max_players = 20