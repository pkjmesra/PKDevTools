# -*- coding: utf-8 -*-
"""
The MIT License (MIT)

Copyright (c) 2023 pkjmesra

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

"""

import asyncio
import hashlib
import json
import logging
import os

# from libsql import SyncCallback
from collections import deque
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp
import aiosqlite
import libsql
import pytz
from tenacity import retry, stop_after_attempt, wait_exponential

from PKDevTools.classes import Archiver

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TursoHybridClient")

LOCAL_TEST_QUERY = "SELECT 1 FROM users"


class TursoHybridClient:
    def __init__(
        self,
        local_path: str,
        remote_url: str,
        auth_token: str,
        telegram_bot_token: Optional[str] = None,
        telegram_chat_id: Optional[str] = None,
        sync_interval: int = 3000,
    ):
        """
        Args:
            local_path: Path to local SQLite file (e.g., "app.db")
            remote_url: libSQL URL (e.g., "libsql://your-db.turso.io")
            auth_token: Turso authentication token
            telegram_bot_token: Optional Telegram bot token for alerts
            telegram_chat_id: Optional Telegram chat ID for alerts
            sync_interval: Sync frequency in seconds (default: 30)
        """
        self.local_path = local_path
        self.remote_url = remote_url
        self.auth_token = auth_token
        self.telegram_bot_token = telegram_bot_token
        self.telegram_chat_id = telegram_chat_id
        self.sync_interval = sync_interval
        # self.sync_queue = deque()
        self.remote_online = True
        self.local_conn = None
        self.remote_conn = None
        self.initial_sync_done = False
        self.mismatch_counts = {}

    async def sync_callback(
        self, success: bool, time_taken=None, error: Optional[Exception] = None
    ):
        if success:
            logger.info(f"Sync completed successfully in {time_taken} s")
            self.initial_sync_done = True
        else:
            logger.error(f"Sync failed: {str(error)}")
        # Send alert via Telegram/Email etc.
        message = (
            f"🟢 Sync successful at {datetime.now()} in {time_taken} s"
            if success
            else f"🔴 Sync failed: {str(error)} in {time_taken} s"
        )
        await self._send_telegram_alert(message)

    async def connect(self):
        """Establish database connections"""

        if not self.local_conn:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.local_path), exist_ok=True)

            # Local SQLite connection
            self.local_conn = await aiosqlite.connect(self.local_path)
            # await self.local_conn.execute("PRAGMA journal_mode=WAL") # Crash-safe writes
            # await self.local_conn.execute("PRAGMA synchronous=NORMAL") #
            # Balanced durability

        if not self.remote_conn:
            try:
                # Remote libSQL connection
                self.remote_conn = libsql.connect(
                    database=self.local_path,
                    auth_token=self.auth_token,
                    sync_url=self.remote_url,
                    sync_interval=self.sync_interval,
                    # pragmas={
                    #     "journal_mode": "WAL",
                    #     "synchronous": "NORMAL",
                    #     "busy_timeout": 5000  # ms
                    # }
                    # sync_verify = True
                    # sync_callback=self.sync_callback,  # Register callback
                    # auto_sync=True  # Optional: automatic periodic sync
                )
                # await self.remote_conn.execute("PRAGMA journal_mode=WAL") # Crash-safe writes
                # await self.remote_conn.execute("PRAGMA synchronous=NORMAL") #
                # Balanced durability
            except Exception as e:
                logger.error(f"connect:Sync failed: {e}")
                await self._send_telegram_alert(f"connect:Sync failed: {e}")
            # self.remote_conn.sync()

    async def close(self):
        """Close database connections"""
        if self.local_conn:
            await self.local_conn.close()
            self.local_conn = None
        if self.remote_conn:
            self.remote_conn.close()
            self.remote_conn = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    async def _send_telegram_alert(self, message: str):
        """Send alert via Telegram bot."""
        if not self.telegram_bot_token or not self.telegram_chat_id:
            return

        try:
            async with aiohttp.ClientSession() as session:
                url = (
                    f"https://api.telegram.org/bot{
    self.telegram_bot_token}/sendMessage"
                )
                await session.post(
                    url,
                    json={
                        "chat_id": self.telegram_chat_id,
                        "text": f"🚨 Turso Sync Alert\n{message}",
                    },
                )
        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {e}")

    async def _get_remote_tables(self) -> List[str]:
        """Fetch all user tables from remote."""
        cursor = self.remote_conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_schema
            WHERE type='table'
            AND name NOT LIKE 'sqlite_%'
            AND name NOT LIKE '_sync_%'
        """)
        return [row[0] for row in cursor.fetchall()]

    # async def _get_table_schema(self, table_name: str) -> str:
    #     """Fetch CREATE TABLE statement for a table."""
    #     cursor = self.remote_conn.cursor()
    #     cursor.execute("""
    #         SELECT sql FROM sqlite_schema
    #         WHERE type='table' AND name = ?
    #     """, (table_name,))
    #     return cursor.fetchone()[0]

    # async def _ensure_local_schemas(self):
    #     """Create missing tables locally by cloning remote schemas."""
    #     if not self.local_conn:
    #         await self.connect()
    #     for table in await self._get_remote_tables():
    #         # Check if table exists locally
    #         cursor = await self.local_conn.execute("""
    #             SELECT name FROM sqlite_schema
    #             WHERE type='table' AND name = ?
    #         """, (table,))

    #         if not await cursor.fetchone():
    #             schema = await self._get_table_schema(table)
    #             await self.local_conn.execute(schema)
    #             logger.info(f"Created local table: {table}")

    # async def initial_sync(self):
    #     """Full sync: pull all remote tables to local."""
    #     await self._ensure_local_schemas()

    #     for table in await self._get_remote_tables():
    #         try:
    #             # Fetch remote data
    #             cursor = self.remote_conn.cursor()
    #             cursor.execute(f"SELECT * FROM {table}")
    #             rows = cursor.fetchall()
    #             cols = [col[0] for col in cursor.description]
    #             if not self.local_conn:
    #                 await self.connect()
    #             # Clear and repopulate local
    #             await self.local_conn.execute(f"DELETE FROM {table}")
    #             if rows:
    #                 query = f"""
    #                     INSERT INTO {table} ({','.join(cols)})
    #                     VALUES ({','.join(['?']*len(cols))})
    #                 """
    #                 await self.local_conn.executemany(query, rows)
    #             await self.local_conn.commit()
    #             logger.info(f"Synced table: {table}")

    #         except Exception as e:
    #             await self._send_telegram_alert(f"Initial sync failed for {table}: {str(e)}")
    #             raise

    async def _sync_remote_to_local(self, retry=False):
        """Pull changes from remote to local using libSQL sync."""
        if not self.remote_online:
            return

        try:
            # libSQL's built-in sync
            self.remote_conn.sync()

            # # Verify critical tables
            # for table in await self._get_remote_tables():
            #     remote_hash = await self._get_table_hash(table, remote=True)
            #     local_hash = await self._get_table_hash(table)

            #     if remote_hash != local_hash:
            #         if not retry:
            #             await self._sync_remote_to_local(retry=True)
            #         else:
            #             logger.error(f"Sync failed. Hash did not match even after retrying")
            #             await self._send_telegram_alert(f"_sync_remote_to_local: sync failed for {table}: {str(e)}")
            #         # await self._merge_table(table)

        except Exception as e:
            logger.error(f"Remote→Local sync failed: {str(e)}")
            self.remote_online = False
            await self._send_telegram_alert(
                f"_sync_remote_to_local:Remote→Local sync failed: {str(e)}"
            )

    # async def _get_table_hash(self, table_name: str, remote: bool = False) -> str:
    #     """Compute SHA-256 hash of table data for change detection."""
    #     if remote:
    #         cursor = self.remote_conn.cursor()
    #         cursor.execute(f"SELECT * FROM {table_name} ORDER BY rowid")
    #         data = cursor.fetchall()
    #     else:
    #         if not self.local_conn:
    #             await self.connect()
    #         cursor = await self.local_conn.execute(f"SELECT * FROM {table_name} ORDER BY rowid")
    #         data = await cursor.fetchall()

    #     return hashlib.sha256(json.dumps(data).encode()).hexdigest()

    # async def _merge_table(self, table_name: str):
    #     """Merge remote table changes into local using UPSERT."""
    #     cursor = self.remote_conn.cursor()
    #     cursor.execute(f"SELECT * FROM {table_name}")
    #     remote_data = cursor.fetchall()
    #     cols = [col[0] for col in cursor.description]

    #     # Assume first column is primary key
    #     pk_column = cols[0]
    #     updates = ", ".join([f"{col}=excluded.{col}" for col in cols[1:]])

    #     query = f"""
    #         INSERT INTO {table_name} ({','.join(cols)})
    #         VALUES ({','.join(['?']*len(cols))})
    #         ON CONFLICT({pk_column}) DO UPDATE SET {updates}
    #     """
    #     if not self.local_conn:
    #         await self.connect()
    #     await self.local_conn.executemany(query, remote_data)
    #     await self.local_conn.commit()

    # async def _sync_local_to_remote(self):
    #     """Push queued local changes to remote in batches."""
    #     if not self.remote_online or not self.sync_queue:
    #         return

    #     try:
    #         # Process batch of 50 changes
    #         batch_size = min(50, len(self.sync_queue))
    #         batch = [self.sync_queue.popleft() for _ in range(batch_size)]

    #         # Build transaction
    #         queries = []
    #         for op, table, row_id, data in batch:
    #             if op == "DELETE":
    #                 queries.append(f"DELETE FROM {table} WHERE rowid = ?")
    #             elif op == "INSERT":
    #                 cols = list(data.keys())
    #                 queries.append(
    #                     f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join(['?']*len(data))})"
    #                 )
    #             elif op == "UPDATE":
    #                 updates = ", ".join([f"{k}=?" for k in data.keys()])
    #                 queries.append(
    #                     f"UPDATE {table} SET {updates} WHERE rowid = ?"
    #                 )

    #         # Execute batch remotely
    #         self.remote_conn.execute("BEGIN")
    #         for query in queries:
    #             self.remote_conn.execute(query)
    #         self.remote_conn.execute("COMMIT")

    #         if not self.local_conn:
    #             await self.connect()
    #         # Clear processed queue items
    #         await self.local_conn.execute("""
    #             DELETE FROM _sync_queue
    #             WHERE id IN (SELECT id FROM _sync_queue ORDER BY id LIMIT ?)
    #         """, (batch_size,))
    #         await self.local_conn.commit()

    #     except Exception as e:
    #         logger.error(f"Local→Remote sync failed: {str(e)}")
    #         await self._send_telegram_alert(f"Local→Remote sync failed: {str(e)}")
    # self.sync_queue.extendleft(reversed(batch))  # Requeue failed items

    # async def _start_background_sync(self):
    #     """Run continuous bidirectional sync."""
    #     while True:
    #         try:
    #             await self._sync_remote_to_local()
    #             # await self._sync_local_to_remote()
    #             await asyncio.sleep(self.sync_interval)
    #         except Exception as e:
    #             logger.error(f"Background sync error: {str(e)}")
    #             await asyncio.sleep(60)  # Backoff on failure

    async def execute_local(self, query: str, params=None):
        """Execute query locally and queue for sync."""
        if not self.local_conn:
            await self.connect()
        cursor = None
        try:
            cursor = await self.local_conn.execute(query, params or ())
            await self.local_conn.commit()
        except aiosqlite.OperationalError as e:
            message = f"🔴 execute_local: Sync/Execution failed: {
    str(query)}:\n{e}"
            await self._send_telegram_alert(message)

        """
        # Detect operation type
        op = self._detect_operation_type(query)
        if op:
            table = self._extract_table_name(query)
            row_id = cursor.lastrowid
            data = params if params else self._extract_data(query, op)
            await self._queue_for_sync(op, table, row_id, data)
        """
        return cursor

    # def _detect_operation_type(self, query: str) -> Optional[str]:
    #     """Detect SQL operation type."""
    #     query = query.strip().upper()
    #     if "INSERT" in query:
    #         return "INSERT"
    #     elif "UPDATE" in query:
    #         return "UPDATE"
    #     elif "DELETE" in query:
    #         return "DELETE"
    #     return None

    # def _extract_table_name(self, query: str) -> Optional[str]:
    #     """Extract table name from SQL query."""
    #     query = query.upper()
    #     if "INSERT" in query:
    #         return query.split("INTO")[1].split()[0].strip()
    #     elif "UPDATE" in query:
    #         return query.split("UPDATE")[1].split()[0].strip()
    #     elif "DELETE" in query:
    #         return query.split("FROM")[1].split()[0].strip()
    #     return None

    # def _extract_data(self, query: str, op: str) -> Dict:
    #     """Extract data from query for sync logging (simplistic)."""
    #     # Implement proper parsing for your queries
    #     return {"raw_query": query}

    # async def _queue_for_sync(self, op: str, table: str, row_id: int, data: Dict):
    #     """Queue change for background sync."""
    #     if not self.local_conn:
    #         await self.connect()
    #     await self.local_conn.execute("""
    #         INSERT INTO _sync_queue (operation, table_name, row_id, data)
    #         VALUES (?, ?, ?, ?)
    #     """, (op, table, row_id, json.dumps(data)))
    #     self.sync_queue.append((op, table, row_id, data))
    #     await self.local_conn.commit()

    async def _verify_trigger_sync(self, trigger_name: str):
        """Check if trigger exists on both DBs"""
        local_exists = await self.local_conn.execute_fetchall(
            "SELECT 1 FROM sqlite_master WHERE type='trigger' AND name=?",
            (trigger_name,),
        )

        remote_exists = self.remote_conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='trigger' AND name=?",
            (trigger_name,),
        ).fetchone()

        return bool(local_exists) and bool(remote_exists)

    async def _verify_initial_sync_done(self, mismatch_counts={}):
        """Check if trigger exists on both DBs"""
        local_exists = await self.local_conn.execute_fetchall(
            "SELECT name FROM sqlite_schema WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )

        exists = os.path.exists(self.local_path)
        modifiedDateTime = (
            Archiver.get_last_modified_datetime(
                self.local_path) if exists else None
        )
        curr = datetime.now(pytz.timezone("Asia/Kolkata"))
        # print(curr - modifiedDateTime)
        should_match_counts = (
            bool(local_exists)
            and (curr - modifiedDateTime).seconds >= self.sync_interval
        )
        still_mismatched = False
        if should_match_counts:
            if len(mismatch_counts.keys()) > 0:
                local_counts = mismatch_counts["local"]
                remote_counts = mismatch_counts["remote"]
                for table in remote_counts.keys():
                    result = await self.local_conn.execute_fetchall(
                        f"SELECT COUNT(1) FROM {table};"
                    )
                    still_mismatched = result[0][0] != remote_counts[table]
                    if still_mismatched:
                        break
            self.initial_sync_done = not still_mismatched
        return self.initial_sync_done  # [row[0] for row in local_exists]

    async def _check_trigger_health(self):
        cursor = self.remote_conn.cursor()
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='trigger'")
        rows = cursor.fetchall()
        triggers = [row[0] for row in rows]
        for trigger in triggers:
            if not await self._verify_trigger_sync(trigger):
                logger.warning(f"Trigger out of sync: {trigger}")
                await self._send_telegram_alert(
                    f"_check_trigger_health: Trigger out of sync: {trigger}"
                )

    async def _monitor_remote_health(self):
        """Check if remote DB is back online."""
        while True:
            try:
                self.remote_conn.execute("SELECT 1")
                if not self.remote_online:
                    logger.info("Remote DB is back online!")
                    self.remote_online = True
                    await self._send_telegram_alert(
                        f"_monitor_remote_health: Remote DB is back online!"
                    )
            except Exception:
                self.remote_online = False
                await self._send_telegram_alert(
                    f"_monitor_remote_health: Remote DB is offline!"
                )
            await asyncio.sleep(60)

    async def run(self, mismatch_counts={}):
        """Start all services."""
        # await self.initial_sync()
        self.mismatch_counts = mismatch_counts
        await self.connect()
        # asyncio.create_task(self._start_background_sync())
        asyncio.create_task(self._monitor_remote_health())
        await self._check_trigger_health()
        import time

        start_sync_time = time.time()
        sync_done_time = 0
        while not await self._verify_initial_sync_done(mismatch_counts):
            sync_done_time = time.time()
        sync_done_time = time.time()
        if self.initial_sync_done:
            await self.sync_callback(
                success=True, time_taken=("%.2f" % (sync_done_time - start_sync_time))
            )


async def main():
    import os

    from PKDevTools.classes import Archiver
    from PKDevTools.classes.DatabaseSyncChecker import DatabaseSyncChecker
    from PKDevTools.classes.Environment import PKEnvironment

    env = PKEnvironment()
    local_path = os.path.join(Archiver.get_user_data_dir(), "pkscreener.db")
    # Initialize with your Turso credentials
    checker = DatabaseSyncChecker(
        local_db_path=local_path,
        turso_url=env.TDU,  # Replace with your Turso URL
        turso_auth_token=env.TAT,  # Replace with your auth token
    )

    # Check if sync is needed
    needs_sync, messages = checker.check_sync_status()

    # Print detailed comparison
    checker.print_counts()

    messages.append(
    f"\nSync needed:{
        '🔴 ' if needs_sync else '🟢 '} {needs_sync}")

    client = TursoHybridClient(
        local_path=local_path,
        remote_url=env.TDU,
        auth_token=env.TAT,
        telegram_bot_token=env.TOKEN,
        telegram_chat_id=f"-{env.CHAT_ID}",
    )
    await client._send_telegram_alert("\n".join(messages))
    # Start sync services
    await client.run(checker.mismatch_counts)

    # # Use normally (all operations go to local first)
    # await client.execute_local(
    #     "INSERT INTO users (name, email) VALUES (?, ?)",
    #     ("Alice", "alice@example.com")
    # )

    # Queries work offline
    # cursor = await client.execute_local("SELECT 1 FROM users")
    # print(await cursor.fetchall())


# asyncio.run(main())
