"""
Applier for applying documentation suggestions to files.

Handles applying LLM-generated documentation changes to source files with backup support.

Line Number Convention:
    This module follows a strict convention for line numbering to prevent off-by-one errors:

    - EXTERNAL (1-indexed): Line numbers as shown to users, stored in DB, and displayed in editors
      Example: Line 1 is the first line of the file

    - INTERNAL (0-indexed): Array/list indices used for accessing lines in memory
      Example: lines[0] is the first line of the file

    - Conversion: Always convert at API boundaries
      marker_line_idx = line_number - 1  # Convert EXTERNAL to INTERNAL

    All functions receiving line_number parameter expect EXTERNAL (1-indexed) values.
    All lines arrays use INTERNAL (0-indexed) access.
"""

import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Union
from dataclasses import dataclass

from .config import Config
from .queue import DocTask, QueueManager
from ..utils.docstring_handler import find_docstring_location
from ..utils.logger_setup import get_logger
from ..utils.response_schemas import (
    ModuleDocstring,
    ClassDocstring,
    MethodDocstring
)
from ..utils.docstring_formatter import (
    format_module_docstring,
    format_class_docstring,
    format_method_docstring
)

logger = get_logger(__name__)


@dataclass
class Suggestion:
    """Represents a documentation suggestion."""
    task_id: int
    file_path: str
    line_number: int
    original_text: str
    suggested_text: str
    task_type: str
    applied: bool = False


class Applier:
    """Applies documentation suggestions to files."""

    def __init__(self, config: Config, queue_manager: QueueManager):
        """
        Initialize Applier.

        Args:
            config: Configuration object
            queue_manager: Queue manager for task information
        """
        self.config = config
        self.queue_manager = queue_manager
        self.backup_dir = Path(config.output.backup_dir)
        self.backed_up_files = set()  # Track files that have been backed up

    def apply_suggestion(self, suggestion: Suggestion) -> bool:
        """
        Apply a single suggestion to a file.

        Args:
            suggestion: Suggestion to apply

        Returns:
            True if successful, False otherwise
        """
        try:
            file_path = Path(suggestion.file_path)

            # Create backup if enabled (only once per file)
            if self.config.output.backup:
                file_key = str(file_path.resolve())
                if file_key not in self.backed_up_files:
                    self._create_backup(file_path)
                    self.backed_up_files.add(file_key)

            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Apply the change
            modified_content = self._apply_change(
                content,
                suggestion.line_number,
                suggestion.original_text,
                suggestion.suggested_text,
                suggestion.task_type
            )

            # Write back to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(modified_content)

            suggestion.applied = True
            return True

        except Exception as e:
            logger.error(f"Error applying suggestion: {e}")
            return False

    def _create_backup(self, file_path: Path):
        """
        Create backup of file before modification.

        Args:
            file_path: Path to file to backup
        """
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # Create backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path.name}.{timestamp}.bak"
        backup_path = self.backup_dir / backup_name

        # Copy file
        shutil.copy2(file_path, backup_path)

    def _extract_indentation(self, line: str) -> str:
        """
        Extract leading whitespace from a line.

        Args:
            line: Line to extract indentation from

        Returns:
            String containing leading whitespace (spaces/tabs)
        """
        indent = ""
        for char in line:
            if char in [' ', '\t']:
                indent += char
            else:
                break
        return indent

    def _add_indent_level(self, base_indent: str) -> str:
        """
        Add one indentation level to base indent.

        Detects whether project uses tabs or spaces and adds
        appropriate increment.

        Args:
            base_indent: Base indentation string

        Returns:
            Base indent plus one level
        """
        if '\t' in base_indent:
            return base_indent + '\t'
        elif len(base_indent) >= 2:
            indent_size = len(base_indent)
            if indent_size % 4 == 0:
                return base_indent + '    '
            elif indent_size % 2 == 0:
                return base_indent + '  '
            else:
                return base_indent + '    '
        else:
            return base_indent + '    '  # Default 4 spaces

    def _apply_change(self, content: str, line_number: int,
                     original_text: str, suggested_text: str,
                     task_type: str) -> str:
        """
        Apply change to file content.

        Args:
            content: Original file content
            line_number: EXTERNAL (1-indexed) line number where marker is
            original_text: Original text (for verification)
            suggested_text: New text to insert
            task_type: Type of task (determines how to apply)

        Returns:
            Modified content
        """
        lines = content.split('\n')

        if task_type in ["generate_module", "validate_module"]:
            # Replace or insert module docstring
            return self._replace_docstring(lines, line_number, original_text, suggested_text, '@llm-module')

        elif task_type in ["generate_docstring", "validate_docstring"]:
            # Replace or insert docstring
            return self._replace_docstring(lines, line_number, original_text, suggested_text, '@llm-doc')

        elif task_type in ["generate_class", "validate_class"]:
            # Replace or insert class docstring
            return self._replace_docstring(lines, line_number, original_text, suggested_text, '@llm-class')

        elif task_type in ["generate_comment", "validate_comment"]:
            # Replace or insert inline comment
            return self._replace_comment(lines, line_number, original_text, suggested_text)

        else:
            # Unsupported task type
            logger.warning(f"Unsupported task type '{task_type}' - skipping application")
            return content

    def _replace_docstring(self, lines: List[str], line_number: int,
                          original_text: str, suggested_text: Union[ModuleDocstring, ClassDocstring, MethodDocstring, str],
                          marker_prefix: str) -> str:
        """
        Replace or insert a docstring.

        Args:
            lines: File lines (0-indexed array)
            line_number: EXTERNAL (1-indexed) line number where marker start is
            original_text: Original docstring (if any)
            suggested_text: Pydantic schema object or formatted string (for validate_* tasks)
            marker_prefix: Marker prefix (@llm-doc, @llm-class, or @llm-module)

        Returns:
            Modified content

        Raises:
            ValueError: If line_number is outside valid range
        """
        # Validate EXTERNAL line number (1-indexed)
        if not (1 <= line_number <= len(lines)):
            raise ValueError(
                f"Invalid line number {line_number} for marker. "
                f"File has {len(lines)} lines (valid range: 1-{len(lines)})"
            )

        # Special handling for MODULE markers (@llm-module)
        if marker_prefix == '@llm-module':
            marker_line_idx = line_number - 1
            marker_indent = self._extract_indentation(lines[marker_line_idx])
            return self._replace_module_docstring(lines, suggested_text, marker_indent)

        # Convert EXTERNAL (1-indexed) to INTERNAL (0-indexed)
        # line_number points to marker start (e.g., line 10 in editor = index 9)
        # Definition should be on the NEXT line after the marker
        marker_line_idx = line_number - 1  # INTERNAL: Convert to 0-indexed
        func_line_idx = None

        # Search FORWARD from marker to find the function/class definition
        # Search until we find definition or reach end of file (no arbitrary limit)
        for i in range(marker_line_idx + 1, len(lines)):
            line = lines[i].strip()

            # Stop if we hit another marker (means we're past the block)
            if line.startswith('# @llm-'):
                break

            # Check for function/class definition
            if line.startswith('def ') or line.startswith('async def ') or line.startswith('class '):
                func_line_idx = i
                break

        if func_line_idx is None:
            # Fallback: assume function is right after marker
            func_line_idx = marker_line_idx + 1

        # Use centralized utility to find existing docstring
        search_start = func_line_idx + 1
        docstring_start, docstring_end = find_docstring_location(lines, search_start)

        # Extract indentation from function/class definition line
        func_indent = self._extract_indentation(lines[func_line_idx])

        # Calculate docstring indentation (function indent + 1 level)
        docstring_indent = self._add_indent_level(func_indent)

        # Format based on type of suggested_text
        if isinstance(suggested_text, ModuleDocstring):
            formatted_docstring = format_module_docstring(suggested_text, docstring_indent)
        elif isinstance(suggested_text, ClassDocstring):
            formatted_docstring = format_class_docstring(suggested_text, docstring_indent)
        elif isinstance(suggested_text, MethodDocstring):
            formatted_docstring = format_method_docstring(suggested_text, docstring_indent)
        elif isinstance(suggested_text, str):
            # Already formatted (validate_* tasks) - need to add indentation
            formatted_docstring = self._format_docstring(suggested_text, docstring_indent)
        else:
            raise ValueError(f"Unexpected type for suggested_text: {type(suggested_text)}")

        # Replace or insert
        if docstring_start is not None and docstring_end is not None:
            # Replace existing docstring
            lines[docstring_start:docstring_end + 1] = formatted_docstring.split('\n')
        else:
            # Insert new docstring after function definition
            insert_at = func_line_idx + 1
            docstring_lines = formatted_docstring.split('\n')
            # Insert all lines at once using slice assignment (more efficient and correct)
            lines[insert_at:insert_at] = docstring_lines

        # NOTE: Markers are preserved in the code for hash-based tracking.
        # They will NOT be removed after documentation is applied.

        return '\n'.join(lines)

    def _format_docstring(self, docstring: str, indent: str) -> str:
        """
        Format docstring with proper indentation and quotes.

        This method applies DETERMINISTIC formatting regardless of LLM output format:
        1. Removes ALL existing indentation
        2. Detects Google Style sections (Args:, Returns:, Raises:, Example:)
        3. Applies consistent indentation:
           - Section headers (Args:, Returns:, etc.): base indent
           - Section content: base indent + 4 spaces

        Args:
            docstring: Raw docstring text
            indent: Base indentation string

        Returns:
            Formatted docstring with consistent indentation
        """
        # Remove existing quotes if present
        docstring = docstring.strip().strip('"""').strip("'''").strip()

        # Split into lines and strip ALL indentation
        lines = [line.strip() for line in docstring.split('\n')]

        # Google Style section markers
        section_markers = ['Args:', 'Arguments:', 'Returns:', 'Return:', 'Yields:',
                          'Raises:', 'Raise:', 'Note:', 'Notes:', 'Example:',
                          'Examples:', 'Attributes:', 'See Also:', 'Warning:',
                          'Warnings:', 'Todo:']

        # Format with quotes and controlled indentation
        formatted_lines = [f'{indent}"""']

        in_section = False
        for line in lines:
            if not line:
                # Empty line
                formatted_lines.append('')
                continue

            # Check if this is a section header
            is_section_header = any(line.startswith(marker) for marker in section_markers)

            if is_section_header:
                # Section header: base indent only
                formatted_lines.append(f'{indent}{line}')
                in_section = True
            elif in_section:
                # Content inside a section: base indent + 4 spaces
                formatted_lines.append(f'{indent}    {line}')
            else:
                # Summary or extended description: base indent only
                formatted_lines.append(f'{indent}{line}')

        formatted_lines.append(f'{indent}"""')

        return '\n'.join(formatted_lines)

    def _replace_comment(self, lines: List[str], line_number: int,
                        original_text: str, suggested_text: str) -> str:
        """
        Replace or insert an inline comment.

        Args:
            lines: File lines (0-indexed array)
            line_number: EXTERNAL (1-indexed) line number where @llm-comm-start marker is
            original_text: Original comment (if any)
            suggested_text: New comment text

        Returns:
            Modified content

        Raises:
            ValueError: If line_number is outside valid range
        """
        # Validate EXTERNAL line number (1-indexed)
        if not (1 <= line_number <= len(lines)):
            raise ValueError(
                f"Invalid line number {line_number} for comment marker. "
                f"File has {len(lines)} lines (valid range: 1-{len(lines)})"
            )

        # Convert EXTERNAL (1-indexed) to INTERNAL (0-indexed)
        marker_line_idx = line_number - 1  # INTERNAL: Convert to 0-indexed

        # Find existing comment or code line
        # Look for: comment line OR code line (in that order)
        existing_comment_idx = None
        code_line_idx = None

        for i in range(marker_line_idx + 1, len(lines)):
            line = lines[i].strip()

            # Stop if we hit the end marker
            if line.startswith('# @llm-comm-end'):
                break

            # Skip empty lines
            if not line:
                continue

            # Check if this is a comment (but not a marker)
            if line.startswith('#') and not line.startswith('# @llm-'):
                if existing_comment_idx is None:
                    existing_comment_idx = i
                # Continue to find the code line after comments
            elif code_line_idx is None:
                # Found the actual code line
                code_line_idx = i
                break

        # Determine where to place the comment
        if code_line_idx is None:
            # Fallback: assume code is right after marker
            code_line_idx = marker_line_idx + 1

        # Extract indentation from code line (comments align with code)
        code_indent = self._extract_indentation(lines[code_line_idx])

        # Format new comment (no level addition - comments align with code)
        formatted_comment = f"{code_indent}# {suggested_text.strip()}"

        # Replace existing comment or insert new one
        if existing_comment_idx is not None:
            # Replace existing comment
            lines[existing_comment_idx] = formatted_comment
        else:
            # Insert new comment above the code line
            lines.insert(code_line_idx, formatted_comment)

        # NOTE: Markers are preserved in the code for hash-based tracking.
        # They will NOT be removed after documentation is applied.

        return '\n'.join(lines)

    def _replace_module_docstring(self, lines: List[str],
                                 suggested_text: Union[ModuleDocstring, str],
                                 marker_indent: str = "") -> str:
        """
        Replace or insert module-level docstring at the top of the file.

        Module docstrings appear at the very beginning of the file,
        before any imports or code, but after the @llm-module-start marker.

        Args:
            lines: File lines (0-indexed array)
            suggested_text: Pydantic schema object or formatted string (for validate_* tasks)
            marker_indent: Indentation from marker line (usually no indentation)

        Returns:
            Modified content
        """
        # Find the @llm-module-start marker (should be line 0)
        marker_start_idx = None
        for i, line in enumerate(lines):
            if line.strip().startswith('# @llm-module-start'):
                marker_start_idx = i
                break

        if marker_start_idx is None:
            logger.warning("Could not find @llm-module-start marker, inserting at top of file")
            marker_start_idx = -1  # Will insert at position 0

        # Search for existing module docstring right after marker
        # Module docstring should be IMMEDIATELY after @llm-module-start
        # We search within a limited range (next 5 lines) to avoid false positives
        search_start = marker_start_idx + 1
        search_end = min(marker_start_idx + 6, len(lines))  # Search next 5 lines max

        docstring_start = None
        docstring_end = None

        # Check if there's already a docstring right after the marker
        for i in range(search_start, search_end):
            line = lines[i].strip()
            # Skip empty lines
            if not line:
                continue
            # Check if this line starts a docstring
            if line.startswith('"""') or line.startswith("'''"):
                # Found start of docstring - use helper to find the end
                ds_start, ds_end = find_docstring_location(lines, i)
                if ds_start is not None:
                    docstring_start = ds_start
                    docstring_end = ds_end
                break
            # If we hit non-empty, non-docstring content, stop searching
            else:
                break

        # Format based on type of suggested_text
        if isinstance(suggested_text, ModuleDocstring):
            formatted_docstring = format_module_docstring(suggested_text, marker_indent)
        elif isinstance(suggested_text, str):
            # Already formatted (validate_* tasks) - need to add indentation
            formatted_docstring = self._format_docstring(suggested_text, marker_indent)
        else:
            raise ValueError(f"Unexpected type for suggested_text: {type(suggested_text)}")

        # Replace or insert
        if docstring_start is not None and docstring_end is not None:
            # Replace existing docstring
            logger.info(f"Replacing existing module docstring at lines {docstring_start+1}-{docstring_end+1}")
            lines[docstring_start:docstring_end + 1] = formatted_docstring.split('\n')
        else:
            # Insert new docstring IMMEDIATELY after @llm-module-start marker
            insert_at = marker_start_idx + 1
            logger.info(f"Inserting new module docstring at line {insert_at+1}")
            docstring_lines = formatted_docstring.split('\n')
            lines[insert_at:insert_at] = docstring_lines

        return '\n'.join(lines)

    def rollback(self, file_path: str) -> bool:
        """
        Rollback to most recent backup of a file.

        Args:
            file_path: Path to file to rollback

        Returns:
            True if successful, False otherwise
        """
        try:
            file_path = Path(file_path)
            file_name = file_path.name

            # Find most recent backup
            backups = sorted(
                self.backup_dir.glob(f"{file_name}.*.bak"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )

            if not backups:
                logger.warning(f"No backups found for {file_path}")
                return False

            most_recent = backups[0]

            # Restore backup
            shutil.copy2(most_recent, file_path)
            logger.info(f"Restored from backup: {most_recent.name}")
            return True

        except Exception as e:
            logger.error(f"Error during rollback: {e}")
            return False
