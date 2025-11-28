# app/database/orm.py
import json
from typing import Any, Dict, List, Optional, Type, TypeVar
from app.database.db_service import db
from app.database.schema import SCHEMA

T = TypeVar("T", bound="Model")

class Model:
    table: str = ""
    json_fields: List[str] = []
    primary_key: str = "id"

    def __init__(self, **kwargs):
        """Load data into attributes from a DB row."""
        self._data = {}
        self._dirty = set()  # fields that changed
        for col in SCHEMA[self.table].keys():
            val = kwargs.get(col)
            self._data[col] = val

        # Track whether this object exists in DB
        self._exists = self._data.get(self.primary_key) is not None

    # ------------------------------
    # Attribute access magic
    # ------------------------------
    def __getattr__(self, item):
        if item in self._data:
            return self._data[item]
        raise AttributeError(item)

    def __setattr__(self, key, value):
        if key in ("_data", "_dirty", "_exists", "table", "json_fields", "primary_key"):
            super().__setattr__(key, value)
        else:
            # Mark dirty only if changed
            if key in self._data and self._data[key] != value:
                self._dirty.add(key)
            self._data[key] = value

    # ------------------------------
    # CRUD methods
    # ------------------------------
    @classmethod
    async def get(cls: Type[T], pk: Any) -> Optional[T]:
        """Get one row by primary key."""
        rows = await db.select(cls.table, {cls.primary_key: pk}, limit=1)
        if not rows:
            return None
        return cls(**rows[0])
    
    @classmethod
    async def get_by(cls: Type[T], **filters) -> Optional[T]:
        """
        Get a single row by any column(s).
        Example:
            user = await DiscordUser.get_by(mc_username="Aaroegun")
        """
        rows = await db.select(cls.table, filters, limit=1)
        if not rows:
            return None
        return cls(**rows[0])


    @classmethod
    async def filter(cls: Type[T], **filters) -> List[T]:
        """Return list of objects matching filters."""
        rows = await db.select(cls.table, filters)
        return [cls(**row) for row in rows]

    @classmethod
    async def all(cls: Type[T]) -> List[T]:
        rows = await db.select(cls.table, {})
        return [cls(**row) for row in rows]

    @classmethod
    async def create(cls: Type[T], **kwargs) -> T:
        """Insert new row and return object."""
        # Insert only provided columns
        pk = await db.insert(cls.table, kwargs)
        kwargs[cls.primary_key] = pk
        obj = cls(**kwargs)
        obj._exists = True
        return obj

    async def save(self):
        """Update only changed fields."""
        if not self._exists:
            # Insert new entry
            pk = await db.insert(self.table, self._data)
            self._data[self.primary_key] = pk
            self._exists = True
            self._dirty.clear()
            return

        if not self._dirty:
            return  # nothing to save

        updates = {k: self._data[k] for k in self._dirty}
        await db.update(self.table, {self.primary_key: self._data[self.primary_key]}, updates)
        self._dirty.clear()

    async def delete(self):
        """Delete this row from DB."""
        if not self._exists:
            return
        await db.delete(self.table, {self.primary_key: self._data[self.primary_key]})
        self._exists = False

    # ------------------------------
    # Helpers
    # ------------------------------
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a plain dictionary."""
        return dict(self._data)
