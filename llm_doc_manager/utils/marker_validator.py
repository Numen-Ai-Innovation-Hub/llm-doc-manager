"""
Marker validation logic.

Validates that documentation markers are correctly formatted and structured
before processing them with the LLM.
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple
from enum import Enum

from .marker_detector import MarkerDetector, MarkerType, MarkerPatterns


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

        # Use centralized pre-compiled patterns
        compiled = MarkerPatterns.get_compiled_patterns()
        self.start_patterns = {mtype: patterns['start'] for mtype, patterns in compiled.items()}
        self.end_patterns = {mtype: patterns['end'] for mtype, patterns in compiled.items()}

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

        # Check for comment blocks crossing scope boundaries
        issues.extend(self._check_comment_scope(lines, file_path))

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

    def _check_comment_scope(self, lines: List[str], file_path: str) -> List[ValidationIssue]:
        """
        Check that comment blocks (@llm-comm) don't cross scope boundaries.

        A comment block cannot:
        - Start inside a def/class and end outside
        - Start outside a def/class and end inside

        Args:
            lines: File lines
            file_path: Path to file (for error messages)

        Returns:
            List of validation issues
        """
        issues = []

        # Get comment marker patterns
        comment_start = self.start_patterns.get(MarkerType.COMMENT)
        comment_end = self.end_patterns.get(MarkerType.COMMENT)

        if not comment_start or not comment_end:
            return issues

        # Find all comment block pairs
        comment_blocks = []  # List of (start_line, end_line) tuples
        start_stack = []

        for i, line in enumerate(lines, start=1):
            if comment_start.match(line):
                start_stack.append(i)
            elif comment_end.match(line):
                if start_stack:
                    start_line = start_stack.pop()
                    comment_blocks.append((start_line, i))

        # For each comment block, check if it crosses scope boundaries
        for start_line, end_line in comment_blocks:
            # Get indentation of start and end markers
            start_indent = len(lines[start_line - 1]) - len(lines[start_line - 1].lstrip())
            end_indent = len(lines[end_line - 1]) - len(lines[end_line - 1].lstrip())

            # Check 1: End marker has different indentation than start
            # This indicates the block exits/enters a scope
            if start_indent != end_indent:
                issues.append(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    message=f"Comment block crosses scope boundary - START at line {start_line} (indent: {start_indent}) and END at line {end_line} (indent: {end_indent}) have different indentation levels",
                    file_path=file_path,
                    line_number=start_line,
                    marker_type=MarkerType.COMMENT.value
                ))
                continue

            # Check 2: There's a 'def' or 'class' between start and end
            # that would indicate entering a new scope
            for i in range(start_line, end_line):
                line = lines[i]
                stripped = line.strip()

                # Check for function or class definition
                if stripped.startswith('def ') or stripped.startswith('async def ') or stripped.startswith('class '):
                    # Get indentation of this definition
                    def_indent = len(line) - len(line.lstrip())

                    # If definition is at same or outer level than start marker,
                    # it means we're crossing into a new scope
                    if def_indent <= start_indent:
                        issues.append(ValidationIssue(
                            level=ValidationLevel.ERROR,
                            message=f"Comment block crosses scope boundary - starts at line {start_line}, encounters '{stripped.split('(')[0].strip()}' at line {i+1}, ends at line {end_line}",
                            file_path=file_path,
                            line_number=start_line,
                            marker_type=MarkerType.COMMENT.value
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
