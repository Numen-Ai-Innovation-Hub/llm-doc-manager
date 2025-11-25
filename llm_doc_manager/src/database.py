"""
Unified database manager for all persistence needs.

Single SQLite database with multiple tables:
- documentation_tasks: Documentation task queue (workflow)
- content_hashes: File/class/method hashes (change detection)
- file_validations: Validation state (marker validation)
- generated_documentation: Generated documentation tracking
- project_metadata: Project-level configuration

All tables follow the 2-word naming convention (no abbreviations).
"""

import sqlite3
from pathlib import Path
from typing import Optional
from ..utils.logger_setup import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """
    Unified database manager.

    Manages a single SQLite database with multiple tables for different concerns.
    Creates all tables automatically on initialization.
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database manager.

        Args:
            db_path: Path to SQLite database file.
                    If None, uses default: .llm-doc-manager/llm_doc_manager.db
        """
        if db_path is None:
            db_path = Path.cwd() / '.llm-doc-manager' / 'llm_doc_manager.db'

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initializing database: {self.db_path}")

        # Initialize schema
        self._init_database()

    def _init_database(self):
        """Create all tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # ============================================
        # TABLE 1: documentation_tasks (workflow)
        # ============================================
        # Check if table exists and has priority column (legacy schema)
        cursor.execute("""
            SELECT sql FROM sqlite_master
            WHERE type='table' AND name='documentation_tasks'
        """)
        existing_schema = cursor.fetchone()

        if existing_schema and 'priority' in existing_schema[0]:
            # Migration: Remove priority column by recreating table
            logger.info("Migrating documentation_tasks: removing priority column")

            # Create new table without priority
            cursor.execute("""
                CREATE TABLE documentation_tasks_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL,
                    line_number INTEGER NOT NULL,
                    task_type TEXT NOT NULL,
                    marker_text TEXT,
                    context TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    error_message TEXT,
                    suggestion TEXT,
                    accepted INTEGER DEFAULT 0,
                    scope_name TEXT
                )
            """)

            # Copy data (excluding priority column)
            cursor.execute("""
                INSERT INTO documentation_tasks_new
                (id, file_path, line_number, task_type, marker_text, context,
                 status, created_at, updated_at, error_message, suggestion, accepted, scope_name)
                SELECT id, file_path, line_number, task_type, marker_text, context,
                       status, created_at, updated_at, error_message, suggestion, accepted, scope_name
                FROM documentation_tasks
            """)

            # Drop old table and rename new one
            cursor.execute("DROP TABLE documentation_tasks")
            cursor.execute("ALTER TABLE documentation_tasks_new RENAME TO documentation_tasks")

            logger.info("Migration completed: priority column removed")
        else:
            # Create table from scratch (no priority column)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documentation_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL,
                    line_number INTEGER NOT NULL,
                    task_type TEXT NOT NULL,
                    marker_text TEXT,
                    context TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    error_message TEXT,
                    suggestion TEXT,
                    accepted INTEGER DEFAULT 0,
                    scope_name TEXT
                )
            """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_documentation_tasks_status
            ON documentation_tasks(status)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_documentation_tasks_file_path
            ON documentation_tasks(file_path)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_documentation_tasks_accepted
            ON documentation_tasks(accepted)
        """)

        # ============================================
        # TABLE 2: content_hashes (change detection)
        # ============================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS content_hashes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                scope_type TEXT NOT NULL,
                scope_name TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                line_start INTEGER NOT NULL,
                line_end INTEGER NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(file_path, scope_type, scope_name)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_content_hashes_file_path
            ON content_hashes(file_path)
        """)

        # ============================================
        # TABLE 3: file_validations (validation state)
        # ============================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS file_validations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL UNIQUE,
                is_valid INTEGER NOT NULL,
                validated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                file_hash TEXT NOT NULL,
                markers_count INTEGER NOT NULL DEFAULT 0,
                error_count INTEGER NOT NULL DEFAULT 0,
                warning_count INTEGER NOT NULL DEFAULT 0,
                validation_details TEXT
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_file_validations_is_valid
            ON file_validations(is_valid)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_file_validations_file_path
            ON file_validations(file_path)
        """)

        # ============================================
        # TABLE 4: generated_documentation (documentation tracking)
        # ============================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS generated_documentation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                doc_path TEXT NOT NULL UNIQUE,
                doc_type TEXT NOT NULL,
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source_hash TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                metadata TEXT
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_generated_documentation_file_path
            ON generated_documentation(file_path)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_generated_documentation_type
            ON generated_documentation(doc_type)
        """)

        # ============================================
        # TABLE 5: project_metadata (configuration)
        # ============================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS project_metadata (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

        logger.info("Database schema initialized successfully")

    def get_connection(self) -> sqlite3.Connection:
        """
        Get a connection to the database.

        Returns:
            SQLite connection object
        """
        return sqlite3.connect(self.db_path)

    def execute_query(self, query: str, params: tuple = ()):
        """
        Execute a query (INSERT, UPDATE, DELETE).

        Args:
            query: SQL query
            params: Query parameters

        Returns:
            Number of affected rows
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        return affected

    def fetch_one(self, query: str, params: tuple = ()):
        """
        Fetch a single row.

        Args:
            query: SQL SELECT query
            params: Query parameters

        Returns:
            Row as dict or None
        """
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, params)
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def fetch_all(self, query: str, params: tuple = ()):
        """
        Fetch all rows.

        Args:
            query: SQL SELECT query
            params: Query parameters

        Returns:
            List of rows as dicts
        """
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]