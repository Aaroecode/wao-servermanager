from app.database.orm import Model

class Inventory(Model):
    table = "inventory"
    primary_key = "id"
    