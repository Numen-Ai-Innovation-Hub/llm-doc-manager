"""
Marker validation logic.

Validates that documentation markers are correctly formatted and structured
before processing them with the LLM.
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple
from enum import Enum

from .markers import MarkerDetector, MarkerType


class ValidationLevel(Enum):
    """Severity levels for validation issues."""
    ERROR = "error"      # Fatal - must be fixed
    WARNING = "warning"  # Suspicious - should review
    INFO = "info"        # Informational


@dataclass
class ValidationIssue:
    """Represents a validation issue with markers."""
    level: ValidationLevel
    message: str
    file_path: str
    line_number: Optional[int] = None
    marker_type: Optional[str] = None

    def __str__(self) -> str:
        """Format issue for display."""
        location = f"{self.file_path}"
        if self.line_number:
            location += f":{self.line_number}"

        level_symbol = {
            ValidationLevel.ERROR: "❌",
            ValidationLevel.WARNING: "⚠️",
            ValidationLevel.INFO: "ℹ️"
        }

        symbol = level_symbol.get(self.level, "•")
        return f"{symbol} {location}: {self.message}"


class MarkerValidator:
    """Validates documentation markers in source files."""

    def __init__(self):
        """Initialize marker validator."""
        self.detector = MarkerDetector()

        # Compile marker patterns
        self.start_patterns = {
            MarkerType.DOCSTRING: re.compile(r'^\s*#\s*@llm-doc-start\s*$'),
            MarkerType.CLASS_DOC: re.compile(r'^\s*#\s*@llm-class-start\s*$'),
            MarkerType.COMMENT: re.compile(r'^\s*#\s*@llm-comm-start\s*$'),
        }

        self.end_patterns = {
            MarkerType.DOCSTRING: re.compile(r'^\s*#\s*@llm-doc-end\s*$'),
            MarkerType.CLASS_DOC: re.compile(r'^\s*#\s*@llm-class-end\s*$'),
            MarkerType.COMMENT: re.compile(r'^\s*#\s*@llm-comm-end\s*$'),
        }

    def validate_file(self, content: str, file_path: str) -> List[ValidationIssue]:
        """
        Validate all markers in a file.

        Args:
            content: File content
            file_path: Path to file (for error messages)

        Returns:
            List of validation issues (empty if all valid)
        """
        issues = []
        lines = content.split('\n')

        # Check for balanced markers (every START has matching END)
        issues.extend(self._check_balanced_markers(lines, file_path))

        # Check for orphaned END markers
        issues.extend(self._check_orphaned_ends(lines, file_path))

        # Check for inconsistent indentation
        issues.extend(self._check_indentation(lines, file_path))

        # Detect blocks and validate their content
        try:
            blocks = self.detector.detect_blocks(content, file_path)

            for block in blocks:
                # Check for empty blocks
                if not block.full_code.strip():
                    issues.append(ValidationIssue(
                        level=ValidationLevel.ERROR,
                        message=f"Empty {block.marker_type.value} block - no code between markers",
                        file_path=file_path,
                        line_number=block.start_line,
                        marker_type=block.marker_type.value
                    ))

                # Check for missing definitions
                if block.marker_type in [MarkerType.DOCSTRING, MarkerType.CLASS_DOC]:
                    if not block.function_name:
                        expected = "function/method" if block.marker_type == MarkerType.DOCSTRING else "class"
                        issues.append(ValidationIssue(
                            level=ValidationLevel.ERROR,
                            message=f"{block.marker_type.value} block missing {expected} definition",
                            file_path=file_path,
                            line_number=block.start_line,
                            marker_type=block.marker_type.value
                        ))

                # Check for very large blocks (potential mistake)
                block_size = block.end_line - block.start_line
                if block_size > 200:
                    issues.append(ValidationIssue(
                        level=ValidationLevel.WARNING,
                        message=f"Very large {block.marker_type.value} block ({block_size} lines) - verify markers are correct",
                        file_path=file_path,
                        line_number=block.start_line,
                        marker_type=block.marker_type.value
                    ))

        except Exception as e:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                message=f"Failed to parse markers: {str(e)}",
                file_path=file_path
            ))

        return issues

    def _check_balanced_markers(self, lines: List[str], file_path: str) -> List[ValidationIssue]:
        """Check that every START marker has a matching END marker."""
        issues = []

        for marker_type, start_pattern in self.start_patterns.items():
            end_pattern = self.end_patterns[marker_type]

            start_stack = []  # Track START markers

            for i, line in enumerate(lines, start=1):
                if start_pattern.match(line):
                    start_stack.append(i)
                elif end_pattern.match(line):
                    if not start_stack:
                        # This is handled by _check_orphaned_ends
                        pass
                    else:
                        start_stack.pop()

            # Any remaining START markers don't have matching END
            for start_line in start_stack:
                issues.append(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    message=f"Unmatched {marker_type.value} START marker - missing END",
                    file_path=file_path,
                    line_number=start_line,
                    marker_type=marker_type.value
                ))

        return issues

    def _check_orphaned_ends(self, lines: List[str], file_path: str) -> List[ValidationIssue]:
        """Check for END markers without matching START."""
        issues = []

        for marker_type, end_pattern in self.end_patterns.items():
            start_pattern = self.start_patterns[marker_type]

            start_count = 0

            for i, line in enumerate(lines, start=1):
                if start_pattern.match(line):
                    start_count += 1
                elif end_pattern.match(line):
                    if start_count == 0:
                        issues.append(ValidationIssue(
                            level=ValidationLevel.ERROR,
                            message=f"Orphaned {marker_type.value} END marker - no matching START",
                            file_path=file_path,
                            line_number=i,
                            marker_type=marker_type.value
                        ))
                    else:
                        start_count -= 1

        return issues

    def _check_indentation(self, lines: List[str], file_path: str) -> List[ValidationIssue]:
        """Check for suspicious indentation in markers."""
        issues = []

        # All marker patterns
        all_patterns = list(self.start_patterns.values()) + list(self.end_patterns.values())

        for i, line in enumerate(lines, start=1):
            for pattern in all_patterns:
                if pattern.match(line):
                    # Check if marker has significant indentation (more than 8 spaces or 2 tabs)
                    indent = len(line) - len(line.lstrip())

                    if indent > 8 or line.count('\t', 0, indent) > 2:
                        issues.append(ValidationIssue(
                            level=ValidationLevel.WARNING,
                            message=f"Marker has unusual indentation ({indent} spaces) - markers should typically be at module/class level",
                            file_path=file_path,
                            line_number=i
                        ))
                    break

        return issues

    def has_errors(self, issues: List[ValidationIssue]) -> bool:
        """Check if any issues are errors (not just warnings)."""
        return any(issue.level == ValidationLevel.ERROR for issue in issues)

    def format_summary(self, issues: List[ValidationIssue]) -> str:
        """Format a summary of validation issues."""
        if not issues:
            return "✅ All markers valid"

        errors = [i for i in issues if i.level == ValidationLevel.ERROR]
        warnings = [i for i in issues if i.level == ValidationLevel.WARNING]
        infos = [i for i in issues if i.level == ValidationLevel.INFO]

        parts = []
        if errors:
            parts.append(f"❌ {len(errors)} error(s)")
        if warnings:
            parts.append(f"⚠️  {len(warnings)} warning(s)")
        if infos:
            parts.append(f"ℹ️  {len(infos)} info")

        return ", ".join(parts)


def validate_markers(content: str, file_path: str) -> Tuple[bool, List[ValidationIssue]]:
    """
    Validate markers in file content.

    Args:
        content: File content
        file_path: Path to file

    Returns:
        Tuple of (is_valid, issues)
        - is_valid: True if no errors (warnings are OK)
        - issues: List of all validation issues
    """
    validator = MarkerValidator()
    issues = validator.validate_file(content, file_path)
    is_valid = not validator.has_errors(issues)
    return is_valid, issues