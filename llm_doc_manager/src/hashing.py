"""
SQLite storage manager for content hashes.

Manages persistent storage of hierarchical hashes (file/class/method) for
change detection between runs.
"""

import sqlite3
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass


@dataclass
class StoredHash:
    """Represents a hash stored in the database."""
    file_path: str
    scope_type: str  # 'FILE' | 'CLASS' | 'METHOD'
    scope_name: str
    content_hash: str
    line_start: int
    line_end: int


class HashStorage:
    """Manages SQLite database for content hash storage."""

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize hash storage.

        Args:
            db_path: Path to SQLite database file. If None, uses default unified database.
        """
        if db_path is None:
            # Use unified database
            db_path = str(Path.cwd() / '.llm-doc-manager' / 'llm_doc_manager.db')

        self.db_path = db_path

        # Initialize unified database (creates all tables including content_hashes)
        from .database import DatabaseManager
        DatabaseManager(db_path=self.db_path)

    def get_hash(
        self,
        file_path: str,
        scope_type: str,
        scope_name: str
    ) -> Optional[str]:
        """
        Retrieve stored hash for a specific scope.

        Args:
            file_path: Path to file
            scope_type: 'FILE' | 'CLASS' | 'METHOD'
            scope_name: Name of scope

        Returns:
            Hash string if found, None otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT content_hash FROM content_hashes
            WHERE file_path = ? AND scope_type = ? AND scope_name = ?
        """, (file_path, scope_type, scope_name))

        result = cursor.fetchone()
        conn.close()

        return result[0] if result else None

    def store_hash(
        self,
        file_path: str,
        scope_type: str,
        scope_name: str,
        content_hash: str,
        line_start: int,
        line_end: int
    ):
        """
        Store or update hash for a specific scope.

        Args:
            file_path: Path to file
            scope_type: 'FILE' | 'CLASS' | 'METHOD'
            scope_name: Name of scope
            content_hash: SHA256 hash
            line_start: Starting line number
            line_end: Ending line number
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO content_hashes
            (file_path, scope_type, scope_name, content_hash, line_start, line_end, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (file_path, scope_type, scope_name, content_hash, line_start, line_end))

        conn.commit()
        conn.close()

    def get_file_hashes(self, file_path: str) -> Dict[str, List[StoredHash]]:
        """
        Get all stored hashes for a file.

        Args:
            file_path: Path to file

        Returns:
            Dict with keys 'file', 'classes', 'methods' containing StoredHash lists
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT file_path, scope_type, scope_name, content_hash, line_start, line_end
            FROM content_hashes
            WHERE file_path = ?
        """, (file_path,))

        rows = cursor.fetchall()
        conn.close()

        result = {
            'file': [],
            'classes': [],
            'methods': []
        }

        for row in rows:
            stored = StoredHash(
                file_path=row[0],
                scope_type=row[1],
                scope_name=row[2],
                content_hash=row[3],
                line_start=row[4],
                line_end=row[5]
            )

            if stored.scope_type == 'FILE':
                result['file'].append(stored)
            elif stored.scope_type == 'CLASS':
                result['classes'].append(stored)
            elif stored.scope_type == 'METHOD':
                result['methods'].append(stored)

        return result

    def delete_file_hashes(self, file_path: str):
        """
        Delete all hashes for a file.

        Args:
            file_path: Path to file
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM content_hashes
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

        cursor.execute("""
            SELECT DISTINCT file_path FROM content_hashes
        """)

        rows = cursor.fetchall()
        conn.close()

        return [row[0] for row in rows]