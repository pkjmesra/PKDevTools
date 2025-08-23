import sqlite3
from typing import Dict, Optional

import libsql


class DatabaseSyncChecker:
    def __init__(
        self,
        local_db_path: str = "pkscreener.db",
        turso_url: Optional[str] = None,
        turso_auth_token: Optional[str] = None,
    ):
        """
        Initialize the database checker with local SQLite and remote Turso connections.

        Args:
            local_db_path: Path to the local SQLite database file.
            turso_url: Turso database URL (e.g., "libsql://your-db.turso.io").
            turso_auth_token: Turso authentication token.
        """
        self.local_db_path = local_db_path
        self.turso_url = turso_url
        self.turso_auth_token = turso_auth_token
        self.local_counts: Dict[str, int] = {}
        self.remote_counts: Dict[str, int] = {}
        self.mismatch_counts = {"local": {}, "remote": {}}
        self.needs_sync = False

    def _get_local_table_counts(self) -> Dict[str, int]:
        """Get row counts for all tables in the local SQLite database."""
        counts = {}
        try:
            with sqlite3.connect(self.local_db_path) as conn:
                cursor = conn.cursor()

                # Get all tables (excluding sqlite_ system tables)
                cursor.execute("""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                """)
                tables = [row[0] for row in cursor.fetchall()]

                # Get row counts for each table
                for table in tables:
                    cursor.execute(f"SELECT COUNT(1) FROM {table};")
                    counts[table] = cursor.fetchone()[0]

        except sqlite3.Error as e:
            print(f"Error reading local database: {e}")
            if "SQLITE_CORRUPT" in str(e.sqlite_errorname):
                from PKDevTools.classes.RepairDB import RepairDB

                db_repair = RepairDB(self.local_db_path)
                db_repair.rebuild_all_indexes()  # Implement recovery logic
        return counts

    def _get_remote_table_counts(self) -> Dict[str, int]:
        """Get row counts for all tables in the remote Turso database using libsql."""
        counts = {}
        if not self.turso_url or not self.turso_auth_token:
            print("Turso URL or auth token not provided. Skipping remote check.")
            return counts

        try:
            # Create libsql client
            client = libsql.connect(
                database=self.turso_url,
                auth_token=self.turso_auth_token,
            )
            # Get all tables (excluding sqlite_ system tables)
            result = client.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """).fetchall()
            tables = [row[0] for row in result]

            # Get row counts for each table
            for table in tables:
                result = client.execute(
    f"SELECT COUNT(1) FROM {table};").fetchall()
                counts[table] = result[0][0]

            client.close()
        except Exception as e:
            print(f"Error reading remote Turso database: {e}")
        return counts

    def check_sync_status(self) -> bool:
        """
        Compare local and remote table counts.
        Returns True if synchronization is needed, False otherwise.
        """
        self.local_counts = self._get_local_table_counts()
        self.remote_counts = self._get_remote_table_counts()

        self.needs_sync = False

        # Check all tables present in either database
        all_tables = set(self.local_counts.keys()).union(
            set(self.remote_counts.keys()))
        messages = []
        self.mismatch_counts = {"local": {}, "remote": {}}
        for table in all_tables:
            local_count = self.local_counts.get(table, -1)
            remote_count = self.remote_counts.get(table, -1)

            if local_count != remote_count:
                self.mismatch_counts["local"][table] = local_count
                self.mismatch_counts["remote"][table] = remote_count
                message = f"Mismatch in table '{table}': Local={local_count}, Remote={remote_count}"
                messages.append(message)
                print(message)
                self.needs_sync = True

        if not self.needs_sync:
            message = "All table counts match. No sync needed."
            messages.append(message)
        return self.needs_sync, messages

    def print_counts(self):
        """Print a comparison of local and remote table counts."""
        all_tables = set(self.local_counts.keys()).union(
            set(self.remote_counts.keys()))
        print("\nTable Count Comparison:")
        print(f"{'Table':<20} | {'Local':>10} | {'Remote':>10}")
        print("-" * 50)

        for table in sorted(all_tables):
            local = self.local_counts.get(table, "N/A")
            remote = self.remote_counts.get(table, "N/A")
            print(f"{table:<20} | {str(local):>10} | {str(remote):>10}")
