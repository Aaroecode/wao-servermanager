from app.database.orm import Model


class Item(Model):
    table = "items"
    primary_key = "item_id"
