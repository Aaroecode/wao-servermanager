# app/services/db_service.py

import sqlite3
import threading
import queue
import asyncio
import time
import os
import json
from typing import Any, Dict, List, Optional, Tuple

from app.database.schema import SCHEMA  # your table definitions


# INTERNAL REQUEST TYPE
_Request = Tuple[str, Dict[str, Any], asyncio.Future]


class DBService:
    """
    Fully async SQLite service with:
    - persistent worker thread
    - queued operations
    - async API
    - auto-schema creation
    - auto-column migration
    - auto-backups
    - JSON field support
    """

    def __init__(
        self,
        db_path: str = "data.db",
        backup_dir: str = "backups",
        backup_interval_sec: int = 900
    ):  
        self.loop = None
        self.db_path = db_path
        self.backup_dir = backup_dir
        self.backup_interval = backup_interval_sec

        # Threading / queue
        self._q: queue.Queue[_Request] = queue.Queue()
        self._thread: Optional[threading.Thread] = None
        self._running = False

        # SQLite connection (lives in worker thread)
        self._conn: Optional[sqlite3.Connection] = None

        # JSON columns mapping (table -> set[column])
        self.json_columns = {
            "discord_users": {"roles_id", "status_list", "inventory", "settings"},
            "purchases": {"payload"}
        }

        # Ensure backup folder exists
        os.makedirs(self.backup_dir, exist_ok=True)

    # -------------------------------------------------------
    #                 PUBLIC ASYNC METHODS
    # -------------------------------------------------------
    async def insert(self, table: str, data: Dict[str, Any]) -> int:
        fut = asyncio.get_running_loop().create_future()
        self._q.put(("insert", {"table": table, "data": data}, fut))
        return await fut

    async def update(self, table: str, where: Dict[str, Any], updates: Dict[str, Any]) -> int:
        fut = asyncio.get_running_loop().create_future()
        self._q.put(("update", {"table": table, "filters": where, "updates": updates}, fut))
        return await fut

    async def select(
        self,
        table: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        order_by: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        fut = asyncio.get_running_loop().create_future()
        self._q.put((
            "select",
            {
                "table": table,
                "filters": filters or {},
                "limit": limit,
                "order_by": order_by
            },
            fut
        ))
        return await fut

    async def delete(self, table: str, filters: Dict[str, Any]) -> int:
        fut = asyncio.get_running_loop().create_future()
        self._q.put(("delete", {"table": table, "filters": filters}, fut))
        return await fut

    async def raw(self, sql: str, params: Optional[Tuple[Any, ...]] = None) -> Any:
        fut = asyncio.get_running_loop().create_future()
        self._q.put(("raw", {"sql": sql, "params": params}, fut))
        return await fut

    # -------------------------------------------------------
    #                WORKER THREAD CONTROL
    # -------------------------------------------------------
    def start(self, loop: Optional[asyncio.AbstractEventLoop] = None):
        """
        Start the DB worker thread.
    
        Call this from an async context:
            db.start(loop=asyncio.get_running_loop())
        """
        if self._running:
            return
    
        if loop is None:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError as e:
                raise RuntimeError(
                    "DBService.start() must be called from inside the running asyncio event loop "
                    "or pass loop=asyncio.get_running_loop()."
                ) from e
    
        self.loop = loop
        self._running = True
        self._thread = threading.Thread(target=self._worker_loop, name="DBWorker", daemon=True)
        self._thread.start()

    def stop(self):
        if not self._running:
            return
        self._running = False

        # Wake the worker with a shutdown request
        self._q.put(("shutdown", {}, None))

        if self._thread:
            self._thread.join(timeout=5)

    def _worker_loop(self):
        """Runs inside the worker thread."""

        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row

        try:
            self._conn.execute("PRAGMA journal_mode = WAL;")
            self._conn.execute("PRAGMA synchronous = NORMAL;")
        except:
            pass

        # Create tables + columns
        self._ensure_schema()

        # Start backup thread
        threading.Thread(target=self._backup_loop, daemon=True).start()

        while self._running:
            try:
                op_name, params, fut = self._q.get(timeout=0.5)
            except queue.Empty:
                continue

            if op_name == "shutdown":
                break

            try:
                if op_name == "insert":
                    result = self._do_insert(params["table"], params["data"])
                elif op_name == "update":
                    result = self._do_update(params["table"], params["filters"], params["updates"])
                elif op_name == "select":
                    result = self._do_select(
                        params["table"],
                        params["filters"],
                        params.get("limit"),
                        params.get("order_by")
                    )
                elif op_name == "delete":
                    result = self._do_delete(params["table"], params["filters"])
                elif op_name == "raw":
                    result = self._do_raw(params["sql"], params.get("params"))
                else:
                    result = None

                if fut:
                    try:
                        target_loop = fut.get_loop() 
                    except Exception:
                        target_loop = getattr(fut, "_loop", None)

                    if target_loop:
                        try:
                            target_loop.call_soon_threadsafe(fut.set_result, result)
                        except Exception as e:
                            try:
                                fut.cancel()
                            except Exception:
                                pass
                            print("DB worker: failed to set_result on target loop:", e)
                    else:
                        try:
                            fut.cancel()
                        except Exception:
                            pass
                        print("DB worker: no target loop found for future; cancelled future.")


            except Exception as e:
                if fut:
                    try:
                        target_loop = fut.get_loop()
                    except Exception:
                        target_loop = getattr(fut, "_loop", None)

                    if target_loop:
                        try:
                            target_loop.call_soon_threadsafe(fut.set_exception, e)
                        except Exception as inner_e:
                            try:
                                fut.cancel()
                            except Exception:
                                pass
                            print("DB worker: failed to set_exception on target loop:", inner_e)
                    else:
                        try:
                            fut.cancel()
                        except Exception:
                            pass
                        print("DB worker exception (no target loop):", e)



        # Cleanup
        try:
            self._conn.close()
        except:
            pass

    # -------------------------------------------------------
    #               AUTO SCHEMA / MIGRATION
    # -------------------------------------------------------
    def _ensure_schema(self):
        cur = self._conn.cursor()

        for table, columns in SCHEMA.items():

            # 1. Create table if not exists
            columns_sql = ", ".join(f"{col} {ctype}" for col, ctype in columns.items())
            cur.execute(f"CREATE TABLE IF NOT EXISTS {table} ({columns_sql});")

            # 2. Check existing columns
            cur.execute(f"PRAGMA table_info({table});")
            existing = {row[1] for row in cur.fetchall()}

            # 3. Auto-add missing columns
            for col_name, col_type in columns.items():
                if col_name not in existing:
                    cur.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type};")

        self._conn.commit()

    # -------------------------------------------------------
    #             INTERNAL DB OPERATIONS
    # -------------------------------------------------------
    def _normalize_for_db(self, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize JSON columns automatically."""
        result = {}
        json_cols = self.json_columns.get(table, set())

        for k, v in data.items():
            if k in json_cols:
                result[k] = json.dumps(v, ensure_ascii=False)
            else:
                result[k] = v

        return result

    def _row_to_dict(self, table: str, row: sqlite3.Row) -> Dict[str, Any]:
        d = dict(row)
        json_cols = self.json_columns.get(table, set())

        for col in json_cols:
            if col in d and d[col] is not None:
                try:
                    d[col] = json.loads(d[col])
                except:
                    pass
        return d

    # Insert
    def _do_insert(self, table: str, data: Dict[str, Any]) -> int:
        data = self._normalize_for_db(table, data)
        keys = list(data.keys())

        sql = f'INSERT INTO {table} ({", ".join(keys)}) VALUES ({", ".join(["?"]*len(keys))})'
        cur = self._conn.cursor()
        cur.execute(sql, tuple(data[k] for k in keys))
        self._conn.commit()
        return cur.lastrowid

    # Filters to WHERE
    def _filters(self, filters: Dict[str, Any]):
        if not filters:
            return "", []

        parts = []
        params = []
        for key, value in filters.items():
            if value is None:
                parts.append(f"{key} IS NULL")
            else:
                parts.append(f"{key} = ?")
                params.append(value)

        return "WHERE " + " AND ".join(parts), params

    # Update
    def _do_update(self, table: str, filters: Dict[str, Any], updates: Dict[str, Any]) -> int:
        updates = self._normalize_for_db(table, updates)
        set_expr = ", ".join(f"{k} = ?" for k in updates.keys())

        where_clause, params = self._filters(filters)
        cur = self._conn.cursor()
        cur.execute(
            f"UPDATE {table} SET {set_expr} {where_clause}",
            tuple(updates.values()) + tuple(params)
        )
        self._conn.commit()
        return cur.rowcount

    # Select
    def _do_select(self, table: str, filters: Dict[str, Any], limit: int, order_by: str):
        where_clause, params = self._filters(filters)
        sql = f"SELECT * FROM {table} {where_clause}"

        if order_by:
            sql += f" ORDER BY {order_by}"
        if limit:
            sql += f" LIMIT {limit}"

        cur = self._conn.cursor()
        cur.execute(sql, tuple(params))
        rows = cur.fetchall()

        return [self._row_to_dict(table, r) for r in rows]

    # Delete
    def _do_delete(self, table: str, filters: Dict[str, Any]) -> int:
        where_clause, params = self._filters(filters)
        cur = self._conn.cursor()
        cur.execute(f"DELETE FROM {table} {where_clause}", tuple(params))
        self._conn.commit()
        return cur.rowcount

    # Raw SQL
    def _do_raw(self, sql: str, params: Optional[Tuple[Any, ...]]):
        cur = self._conn.cursor()
        if params:
            cur.execute(sql, params)
        else:
            cur.execute(sql)

        try:
            rows = cur.fetchall()
            return rows
        except sqlite3.ProgrammingError:
            self._conn.commit()
            return None

    # -------------------------------------------------------
    #                  BACKUP LOOP
    # -------------------------------------------------------
    def _backup_loop(self):
        while self._running:
            try:
                ts = time.strftime("%Y%m%d_%H%M%S")
                backup_file = os.path.join(self.backup_dir, f"backup_{ts}.db")

                dest = sqlite3.connect(backup_file)
                with dest:
                    self._conn.backup(dest)
                dest.close()

            except Exception:
                pass

            time.sleep(self.backup_interval)


db = DBService(
    db_path=os.path.join(os.getcwd(), "app", "database", "data.db"),
    backup_dir="backups",
    backup_interval_sec=21600
)