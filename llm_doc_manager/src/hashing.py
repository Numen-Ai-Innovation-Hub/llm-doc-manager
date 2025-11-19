"""
SQLite storage manager for content hashes.

Manages persistent storage of file-level hashes for change detection
between runs.
"""

import sqlite3
from pathlib import Path
from typing import Optional, List


class HashStorage:
    """Manages SQLite database for file hash storage."""

    def __init__(self, db_path: str):
        """
        Initialize hash storage.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._ensure_db_exists()

    def _ensure_db_exists(self):
        """Create database and tables if they don't exist."""
        # Ensure directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS file_hashes (
                file_path TEXT PRIMARY KEY,
                content_hash TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def get_file_hash(self, file_path: str) -> Optional[str]:
        """
        Retrieve stored hash for a file.

        Args:
            file_path: Path to file

        Returns:
            Hash string if found, None otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT content_hash FROM file_hashes
            WHERE file_path = ?
        """, (file_path,))

        result = cursor.fetchone()
        conn.close()

        return result[0] if result else None

    def store_file_hash(self, file_path: str, content_hash: str):
        """
        Store or update hash for a file.

        Args:
            file_path: Path to file
            content_hash: SHA256 hash of file content
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO file_hashes
            (file_path, content_hash, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (file_path, content_hash))

        conn.commit()
        conn.close()

    def delete_file_hash(self, file_path: str):
        """
        Delete hash for a file.

        Args:
            file_path: Path to file
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM file_hashes
            WHERE file_path = ?
        """, (file_path,))

        conn.commit()
        conn.close()

    def get_all_files(self) -> List[str]:
        """
        Get list of all files with stored hashes.

        Returns:
            List of file paths
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT file_path FROM file_hashes")

        rows = cursor.fetchall()
        conn.close()

        return [row[0] for row in rows]