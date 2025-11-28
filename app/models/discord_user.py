from app.database.orm import Model

# class NewTable(Model):
#     table = "new_table_name"
#     primary_key = "id"
#     json_fields = ["json_field1", "json_field2"]   # optional

class DiscordUser(Model):
    table = "discord_users"
    primary_key = "id"
    json_fields = ["roles_id", "status_list", "inventory", "settings"]   # optional

