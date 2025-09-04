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
import os
from PKDevTools.classes.log import default_logger
from PKDevTools.classes.dictModel import SmartDictModel

def get_file_size(file_path):
    """Get the size of a file in bytes and human-readable format."""
    try:
        # Get size in bytes
        size_bytes = os.path.getsize(file_path)
        # Convert to human-readable format
        size_kb = size_bytes / 1024
        size_mb = size_bytes / (1024 * 1024)
        return SmartDictModel({
            'bytes': size_bytes,
            'kb': round(size_kb, 2),
            'mb': round(size_mb, 2),
            'human_readable': f"{size_mb:.2f} MB" if size_mb >= 1 else f"{size_kb:.2f} KB"
        })
    except FileNotFoundError:
        default_logger().error(f"File not found: {file_path}")
        return None
    except Exception as e:
        default_logger().error(f"Error getting file size: {e}")
        return None

def is_valid_sqlite_db(db_path):
    """Check if a file is a valid SQLite database."""
    if not os.path.exists(db_path):
        return False
    try:
        # SQLite database files start with this header
        with open(db_path, 'rb') as f:
            header = f.read(16)
            return header == b'SQLite format 3\x00'
    except:
        return False

def get_sqlite_db_info(db_path):
    import sqlite3
    """Get comprehensive information about a SQLite database."""
    if not os.path.exists(db_path):
        print(f"Database file does not exist: {db_path}")
        return None
    # Check if it's a valid SQLite database
    if is_valid_sqlite_db(db_path):
        print("✓ File is a valid SQLite database")
    try:
        # Get file size
        size_bytes = os.path.getsize(db_path)
        size_mb = size_bytes / (1024 * 1024)
        # Connect to database for additional info
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # Get table information
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        # Get row counts for each table
        table_stats = {}
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(1) FROM {table_name};")
            row_count = cursor.fetchone()[0]
            table_stats[table_name] = row_count
        # Get total row count
        total_rows = sum(table_stats.values())
        # Get database schema info
        cursor.execute("PRAGMA page_size;")
        page_size = cursor.fetchone()[0]
        cursor.execute("PRAGMA page_count;")
        page_count = cursor.fetchone()[0]
        cursor.execute("PRAGMA journal_mode;")
        journal_mode = cursor.fetchone()[0]
        conn.close()

        return SmartDictModel({
            'file_size_bytes': size_bytes,
            'file_size_mb': round(size_mb, 2),
            'file_size_human': f"{size_mb:.2f} MB",
            'tables': [table[0] for table in tables],
            'table_stats': table_stats,
            'total_rows': total_rows,
            'page_size': page_size,
            'page_count': page_count,
            'database_size_bytes': page_size * page_count,
            'journal_mode': journal_mode
        })
    except sqlite3.Error as e:
        default_logger().error(f"SQLite error: {e}")
        return None
    except Exception as e:
        default_logger().error(f"Error: {e}")
        return None
