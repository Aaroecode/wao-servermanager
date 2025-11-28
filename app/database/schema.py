# app/database/schema.py

SCHEMA = {
    "discord_users": {
        "id": "INTEGER PRIMARY KEY",             # Discord user ID
        "username": "TEXT",                      # Discord username
        "mc_username": "TEXT",                   # Minecraft username
        "mc_uuid": "TEXT",                       # Minecraft UUID
        "mc_token": "TEXT",                      # Link token used during verification
        "verified": "INTEGER DEFAULT 0",         # Whether linked to MC (0/1)
        "date_joined": "TEXT",                   # ISO datetime string                # Last active timestamp
        "is_banned": "INTEGER DEFAULT 0",        # Ban flag (0/1)
        "is_muted": "INTEGER DEFAULT 0",         # Mute flag (0/1) ← NEW FIELD
        
        "roles_id": "TEXT",                      # JSON list of role IDs
        "status_list": "TEXT",                   # JSON list of statuses
        "inventory": "TEXT",                     # JSON dict (items, tokens, etc.)
        "settings": "TEXT",                      # JSON dict (preferences)
        
        "notes": "TEXT"                          # Admin/moderator notes
    },

    "purchases": {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "player_name": "TEXT",                   # buyer
        "item": "TEXT",                          # purchased item
        "payload": "TEXT",                       # JSON (extra info)
        "status": "TEXT",                        # pending / completed / failed
        "created_at": "TEXT"                     # ISO timestamp
    },

    "items": {
        "item_id": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "item_name": "TEXT",                     # Name of the item
        "item_lore": "TEXT",                     # Lore/description of the item
        "item_meta": "TEXT",                     # Additional metadata (JSON)
        "mc_command": "TEXT"                     # Minecraft command to grant the item

    },
    "inventory": {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",                 # Minecraft username
        "item_id": "TEXT",                         # JSON list of items in inventory
        "quantity": "INTEGER",                   # Quantity of the item
        "acquired_at": "TEXT",                    # ISO timestamp when acquired
    },
    # Add more tables here as needed
    # "warnings": {...}
    # "guild_data": {...}
    # "verify_tokens": {...}
}
