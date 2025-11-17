"""
Task queue management for documentation tasks.

Manages the queue of documentation tasks that need to be processed by the LLM.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum


class TaskStatus(Enum):
    """Status of a documentation task."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class TaskPriority(Enum):
    """Priority levels for tasks."""
    LOW = 1
    MEDIUM = 5
    HIGH = 10
    CRITICAL = 15


@dataclass
class DocTask:
    """Represents a documentation task."""
    id: Optional[int] = None
    file_path: str = ""
    line_number: int = 0  # EXTERNAL (1-indexed) - line number shown to user
    task_type: str = ""  # validate_docstring, generate_docstring
    marker_text: str = ""
    context: str = ""  # Surrounding code context
    parameters: Optional[Dict[str, Any]] = None  # DEPRECATED: Always None, kept for DB compatibility
    priority: int = TaskPriority.MEDIUM.value
    status: str = TaskStatus.PENDING.value
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    error_message: Optional[str] = None
    suggestion: Optional[str] = None  # LLM-generated suggestion
    accepted: bool = False  # Whether user accepted the suggestion

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        if self.parameters is not None:
            data['parameters'] = json.dumps(self.parameters)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DocTask':
        """Create from dictionary."""
        if 'parameters' in data and isinstance(data['parameters'], str):
            data['parameters'] = json.loads(data['parameters']) if data['parameters'] else None
        return cls(**data)


class QueueManager:
    """Manages the task queue using SQLite."""

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize QueueManager.

        Args:
            db_path: Path to SQLite database file. If None, uses default location.
        """
        if db_path is None:
            db_path = Path.cwd() / ".llm-doc-manager" / "queue.db"
        else:
            db_path = Path(db_path)

        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = str(db_path)
        self._init_database()

    def _init_database(self):
        """Initialize the database schema."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                line_number INTEGER NOT NULL,
                task_type TEXT NOT NULL,
                marker_text TEXT,
                context TEXT,
                parameters TEXT,
                priority INTEGER DEFAULT 5,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                error_message TEXT,
                suggestion TEXT,
                accepted INTEGER DEFAULT 0
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_status ON tasks(status)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_file_path ON tasks(file_path)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_accepted ON tasks(accepted)
        """)

        conn.commit()
        conn.close()

    def add_task(self, task: DocTask) -> int:
        """
        Add a task to the queue.

        Args:
            task: Task to add

        Returns:
            ID of the added task
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        task_dict = task.to_dict()
        task_dict.pop('id', None)  # Remove id if present
        task_dict['created_at'] = datetime.now().isoformat()
        task_dict['updated_at'] = datetime.now().isoformat()

        columns = ', '.join(task_dict.keys())
        placeholders = ', '.join(['?' for _ in task_dict])
        query = f"INSERT INTO tasks ({columns}) VALUES ({placeholders})"

        cursor.execute(query, list(task_dict.values()))
        task_id = cursor.lastrowid

        conn.commit()
        conn.close()

        return task_id

    def get_task(self, task_id: int) -> Optional[DocTask]:
        """
        Get a task by ID.

        Args:
            task_id: Task ID

        Returns:
            Task or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()

        conn.close()

        if row:
            return DocTask.from_dict(dict(row))
        return None

    def get_pending_tasks(self, limit: Optional[int] = None) -> List[DocTask]:
        """
        Get pending tasks ordered by priority.

        Args:
            limit: Maximum number of tasks to return

        Returns:
            List of pending tasks
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = """
            SELECT * FROM tasks
            WHERE status = ?
            ORDER BY priority DESC, created_at ASC
        """
        if limit:
            query += f" LIMIT {limit}"

        cursor.execute(query, (TaskStatus.PENDING.value,))
        rows = cursor.fetchall()

        conn.close()

        return [DocTask.from_dict(dict(row)) for row in rows]

    def update_task_status(self, task_id: int, status: TaskStatus,
                          error_message: Optional[str] = None):
        """
        Update task status.

        Args:
            task_id: Task ID
            status: New status
            error_message: Optional error message if status is FAILED
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE tasks
            SET status = ?, updated_at = ?, error_message = ?
            WHERE id = ?
        """, (status.value, datetime.now().isoformat(), error_message, task_id))

        conn.commit()
        conn.close()

    def get_stats(self) -> Dict[str, int]:
        """
        Get queue statistics.

        Returns:
            Dictionary with counts for each status
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM tasks
            GROUP BY status
        """)

        stats = {row[0]: row[1] for row in cursor.fetchall()}
        stats['total'] = sum(stats.values())

        conn.close()

        return stats

    def clear_all(self):
        """Remove all tasks from the queue."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM tasks")

        conn.commit()
        conn.close()

    def get_tasks_by_file(self, file_path: str) -> List[DocTask]:
        """
        Get all tasks for a specific file.

        Args:
            file_path: Path to the file

        Returns:
            List of tasks for the file
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM tasks
            WHERE file_path = ?
            ORDER BY line_number ASC
        """, (file_path,))

        rows = cursor.fetchall()
        conn.close()

        return [DocTask.from_dict(dict(row)) for row in rows]

    def get_tasks_by_status(self, status: TaskStatus) -> List[DocTask]:
        """
        Get all tasks with a specific status.

        Args:
            status: Task status

        Returns:
            List of tasks with the status
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM tasks
            WHERE status = ?
            ORDER BY priority DESC, created_at ASC
        """, (status.value,))

        rows = cursor.fetchall()
        conn.close()

        return [DocTask.from_dict(dict(row)) for row in rows]

    def update_suggestion(self, task_id: int, suggestion: str):
        """
        Update task with LLM-generated suggestion.

        Args:
            task_id: Task ID
            suggestion: Generated suggestion text
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE tasks
            SET suggestion = ?, updated_at = ?
            WHERE id = ?
        """, (suggestion, datetime.now().isoformat(), task_id))

        conn.commit()
        conn.close()

    def accept_task(self, task_id: int):
        """
        Mark task as accepted.

        Args:
            task_id: Task ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE tasks
            SET accepted = 1, updated_at = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), task_id))

        conn.commit()
        conn.close()

    def get_accepted_tasks(self) -> List[DocTask]:
        """
        Get all accepted tasks.

        Returns:
            List of accepted tasks sorted by file_path and line_number DESC
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM tasks
            WHERE accepted = 1
            ORDER BY file_path ASC, line_number DESC
        """)

        rows = cursor.fetchall()
        conn.close()

        return [DocTask.from_dict(dict(row)) for row in rows]

    def delete_task(self, task_id: int):
        """
        Delete a task from the queue.

        Args:
            task_id: Task ID to delete
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

        conn.commit()
        conn.close()
