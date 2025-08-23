import os
import sqlite3
import subprocess
from typing import List, Tuple


class RepairDB:
    def __init__(
        self,
        local_db_path: str = "pkscreener.db",
    ):
        self.local_db_path = local_db_path
        self.local_conn = None

    def rebuild_all_indexes(self) -> bool:
        """
        Drops and recreates all indexes in a SQLite database to fix corruption.
        Returns True if successful, False if any errors occurred.
        """
        conn = None
        try:
            # Connect with aggressive error detection
            conn = sqlite3.connect(
    f"file:{
        self.local_db_path}?mode=rw",
         uri=True)
            # Disable FK checks during rebuild
            conn.execute("PRAGMA foreign_keys=OFF")
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")

            # Step 1: Get all indexes and their creation SQL
            indexes: List[Tuple[str, str]] = conn.execute("""
                SELECT name, sql FROM sqlite_master
                WHERE type = 'index'
                AND name NOT LIKE 'sqlite_%'  -- Skip system indexes
                AND sql IS NOT NULL          -- Skip auto-created indexes
            """).fetchall()

            if not indexes:
                print("No indexes found to rebuild")
                return True

            # Step 2: Drop and recreate in a single transaction
            with conn:
                for name, create_sql in indexes:
                    try:
                        print(f"Rebuilding index: {name}")
                        conn.execute(f"DROP INDEX IF EXISTS {name}")

                        # Handle unique/indexed columns properly
                        create_sql = create_sql.replace(
                            "CREATE INDEX", "CREATE INDEX IF NOT EXISTS"
                        )
                        create_sql = create_sql.replace(
                            "CREATE UNIQUE INDEX", "CREATE UNIQUE INDEX IF NOT EXISTS"
                        )

                        conn.execute(create_sql)
                    except sqlite3.Error as e:
                        print(f"Failed to rebuild {name}: {e}")
                        raise  # Will rollback entire transaction

            # Step 3: Verify integrity
            if conn.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise RuntimeError("Post-rebuild integrity check failed")
            conn.execute("PRAGMA optimize")
            conn.execute("PRAGMA incremental_vacuum")
            return True

        except Exception as e:
            print(f"Index rebuild failed: {e}")
            return False
        finally:
            if conn:
                conn.execute("PRAGMA foreign_keys=ON")  # Restore FK checks
                conn.close()

    def pre_sync_check(self):
        conn = sqlite3.connect(f"file:{self.local_db_path}?mode=rw", uri=True)
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA integrity_check(1)")  # Fast partial check
        if cursor.fetchone()[0] != "ok":
            raise RuntimeError("Pre-sync corruption detected")

    def repair_database(self):
        try:
            # Attempt quick recovery
            temp_db = f"{self.local_db_path}.recovered"
            conn = sqlite3.connect(
    f"file:{
        self.local_db_path}?mode=rw",
         uri=True)
            conn.execute("PRAGMA wal_checkpoint(FULL)")

            if "ok" not in conn.execute("PRAGMA quick_check").fetchone()[0]:
                # Full rebuild if quick check fails
                with sqlite3.connect(temp_db) as new_db:
                    conn.backup(new_db)
                conn.close()
                os.replace(temp_db, self.local_db_path)
            return True
        except Exception as e:
            print(f"Repair failed: {e}")
            return False

    def emergency_repair(self):
        subprocess.run(
            ["sqlite3", self.local_db_path, ".recover | sqlite3 repaired.db"]
        )
        os.replace("repaired.db", self.local_db_path)
