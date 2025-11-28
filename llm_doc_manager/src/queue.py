"""
Task queue management for documentation tasks.

Manages the queue of documentation tasks that need to be processed by the LLM.

Line Number Convention:
    DocTask.line_number is EXTERNAL (1-indexed) - the line number as shown in editors.
    This matches user expectations and editor displays (first line is line 1, not line 0).
"""

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


@dataclass
class DocTask:
    """Represents a documentation task."""
    id: Optional[int] = None
    file_path: str = ""
    line_number: int = 0  # EXTERNAL (1-indexed) - line number shown to user
    task_type: str = ""  # validate_docstring, generate_docstring
    marker_text: str = ""
    context: str = ""  # Surrounding code context
    status: str = TaskStatus.PENDING.value
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    error_message: Optional[str] = None
    suggestion: Optional[str] = None  # LLM-generated suggestion
    accepted: bool = False  # Whether user accepted the suggestion
    scope_name: Optional[str] = None  # Name of class/method being documented

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DocTask':
        """Create from dictionary."""
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
            # Use unified database
            db_path = Path.cwd() / ".llm-doc-manager" / "llm_doc_manager.db"
        else:
            db_path = Path(db_path)

        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = str(db_path)

        # Initialize unified database (creates all tables including documentation_tasks)
        from .database import DatabaseManager
        DatabaseManager(db_path=self.db_path)

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
        query = f"INSERT INTO documentation_tasks ({columns}) VALUES ({placeholders})"

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

        cursor.execute("SELECT * FROM documentation_tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()

        conn.close()

        if row:
            return DocTask.from_dict(dict(row))
        return None

    def get_pending_tasks(self, limit: Optional[int] = None) -> List[DocTask]:
        """
        Get pending tasks ordered by creation time.

        Tasks are returned in FIFO order (first created, first returned).
        The actual processing order is determined by TASK_PROCESSING_ORDER constant.

        Args:
            limit: Maximum number of tasks to return

        Returns:
            List of pending tasks
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = """
            SELECT * FROM documentation_tasks
            WHERE status = ?
            ORDER BY created_at ASC
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
            UPDATE documentation_tasks
            SET status = ?, updated_at = ?, error_message = ?
            WHERE id = ?
        """, (status.value, datetime.now().isoformat(), error_message, task_id))

        conn.commit()
        conn.close()

    def update_task_error(self, task_id: int, error_message: Optional[str]):
        """
        Update task error message.

        Args:
            task_id: Task ID
            error_message: Error message (None to clear)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE documentation_tasks
            SET error_message = ?, updated_at = ?
            WHERE id = ?
        """, (error_message, datetime.now().isoformat(), task_id))

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
            FROM documentation_tasks
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

        cursor.execute("DELETE FROM documentation_tasks")

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
            SELECT * FROM documentation_tasks
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
            List of tasks with the status ordered by creation time
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM documentation_tasks
            WHERE status = ?
            ORDER BY created_at ASC
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
            UPDATE documentation_tasks
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
            UPDATE documentation_tasks
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
            SELECT * FROM documentation_tasks
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

        cursor.execute("DELETE FROM documentation_tasks WHERE id = ?", (task_id,))

        conn.commit()
        conn.close()
