"""
File scanner for detecting documentation markers.

Scans project files to find markers that indicate where documentation
needs to be validated, generated, or reviewed.
"""

import os
from fnmatch import fnmatch
from pathlib import Path
from typing import List, Optional, Set
from dataclasses import dataclass

from .markers import MarkerDetector
from .queue import DocTask, QueueManager
from .config import Config
from .validator import MarkerValidator, ValidationIssue, ValidationLevel
from .logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class ScanResult:
    """Result of scanning operation."""
    files_scanned: int = 0
    tasks_created: int = 0
    errors: List[str] = None
    validation_issues: List[ValidationIssue] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.validation_issues is None:
            self.validation_issues = []


class Scanner:
    """Scans files for documentation markers."""

    def __init__(self, config: Config, queue_manager: QueueManager):
        """
        Initialize Scanner.

        Args:
            config: Configuration object
            queue_manager: Queue manager for adding tasks
        """
        self.config = config
        self.queue_manager = queue_manager
        self.marker_detector = MarkerDetector()
        self.validator = MarkerValidator()

    def scan(self, paths: Optional[List[str]] = None) -> ScanResult:
        """
        Scan files for markers.

        Args:
            paths: Optional list of paths to scan. If None, uses config paths.

        Returns:
            ScanResult with statistics
        """
        if paths is None:
            paths = self.config.scanning.paths

        result = ScanResult()
        files_to_scan = self._collect_files(paths)

        logger.info(f"Scanning {len(files_to_scan)} file(s) for markers")

        for file_path in files_to_scan:
            try:
                # Read file content
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Validate markers first
                issues = self.validator.validate_file(content, str(file_path))
                result.validation_issues.extend(issues)

                # Check if there are any errors
                if self.validator.has_errors(issues):
                    # Don't process this file - has validation errors
                    logger.warning(f"Skipping {file_path} due to validation errors")
                    result.files_scanned += 1
                    continue

                # If only warnings, proceed but track them
                tasks = self._scan_file(file_path, content)
                for task in tasks:
                    self.queue_manager.add_task(task)
                    result.tasks_created += 1
                result.files_scanned += 1
            except Exception as e:
                error_msg = f"Error scanning {file_path}: {str(e)}"
                logger.error(error_msg)
                result.errors.append(error_msg)

        return result

    def _collect_files(self, paths: List[str]) -> List[Path]:
        """
        Collect all files to scan based on configuration.

        Args:
            paths: List of paths to scan (files or directories)

        Returns:
            List of file paths to scan
        """
        files = []
        exclude_patterns = set(self.config.scanning.exclude)
        file_types = {".py"}  # Always Python files

        for path_str in paths:
            path = Path(path_str)

            if not path.exists():
                continue

            if path.is_file():
                if self._should_include_file(path, file_types, exclude_patterns):
                    files.append(path)
            elif path.is_dir():
                files.extend(self._scan_directory(path, file_types, exclude_patterns))

        return files

    def _scan_directory(self, directory: Path, file_types: Set[str],
                       exclude_patterns: Set[str]) -> List[Path]:
        """
        Recursively scan directory for files.

        Args:
            directory: Directory to scan
            file_types: Set of file extensions to include
            exclude_patterns: Set of patterns to exclude

        Returns:
            List of file paths
        """
        files = []

        for root, dirs, filenames in os.walk(directory):
            # Filter out excluded directories
            dirs[:] = [d for d in dirs if not self._matches_exclude(d, exclude_patterns)]

            for filename in filenames:
                file_path = Path(root) / filename
                if self._should_include_file(file_path, file_types, exclude_patterns):
                    files.append(file_path)

        return files

    def _should_include_file(self, file_path: Path, file_types: Set[str],
                            exclude_patterns: Set[str]) -> bool:
        """
        Check if file should be included in scan.

        Args:
            file_path: File path to check
            file_types: Set of allowed file extensions
            exclude_patterns: Set of patterns to exclude

        Returns:
            True if file should be included
        """
        # Check file type
        if file_types and file_path.suffix not in file_types:
            return False

        # Check exclude patterns
        if self._matches_exclude(str(file_path), exclude_patterns):
            return False

        # Check file size
        max_size = self.config.scanning.max_file_size_mb * 1024 * 1024
        if file_path.stat().st_size > max_size:
            return False

        return True

    def _matches_exclude(self, path: str, exclude_patterns: Set[str]) -> bool:
        """
        Check if path matches any exclude pattern.

        Args:
            path: Path to check
            exclude_patterns: Set of exclude patterns

        Returns:
            True if path should be excluded
        """
        for pattern in exclude_patterns:
            if fnmatch(path, pattern) or pattern in path:
                return True
        return False

    def _scan_file(self, file_path: Path, content: str = None) -> List[DocTask]:
        """
        Scan a single file for markers.

        Args:
            file_path: Path to file
            content: Optional pre-read content (for efficiency)

        Returns:
            List of DocTasks found in the file
        """
        if content is None:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                # Try with different encoding
                with open(file_path, 'r', encoding='latin-1') as f:
                    content = f.read()

        # Detect markers
        markers = self.marker_detector.detect_markers(content, str(file_path))

        # Convert markers to tasks
        tasks = []
        for marker in markers:
            task = self._create_task_from_marker(marker, content, file_path)
            if task:
                tasks.append(task)

        return tasks

    def _create_task_from_marker(self, marker: dict, content: str,
                                 file_path: Path) -> Optional[DocTask]:
        """
        Create a DocTask from a detected marker.

        Args:
            marker: Marker information from detector
            content: Full file content
            file_path: Path to the file

        Returns:
            DocTask or None
        """
        # Delimiter-based system ALWAYS provides full_code
        context = marker['full_code']

        # Task type is auto-determined by marker detection
        task_type = marker['task_type']

        # Determine priority
        priority = marker['priority']

        # Create task
        task = DocTask(
            file_path=str(file_path),
            line_number=marker['line_number'],
            task_type=task_type,
            marker_text=marker.get('match_text', marker['line_content']),
            context=context,
            priority=priority
        )

        return task

    def scan_file(self, file_path: str) -> ScanResult:
        """
        Scan a single file.

        Args:
            file_path: Path to the file to scan

        Returns:
            ScanResult
        """
        return self.scan(paths=[file_path])
