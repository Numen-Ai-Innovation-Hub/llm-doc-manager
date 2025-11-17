"""
Applier for applying documentation suggestions to files.

Handles applying LLM-generated documentation changes to source files with backup support.
"""

import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict
from dataclasses import dataclass

from .config import Config
from .queue import DocTask, QueueManager
from .markers import MarkerPatterns


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
            print(f"Error applying suggestion: {e}")
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

    def _apply_change(self, content: str, line_number: int,
                     original_text: str, suggested_text: str,
                     task_type: str) -> str:
        """
        Apply change to file content.

        Args:
            content: Original file content
            line_number: Line number where change occurs
            original_text: Original text (for verification)
            suggested_text: New text to insert
            task_type: Type of task (determines how to apply)

        Returns:
            Modified content
        """
        lines = content.split('\n')

        if task_type in ["generate_docstring", "validate_docstring"]:
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
            return content

    def _replace_docstring(self, lines: List[str], line_number: int,
                          original_text: str, suggested_text: str, marker_prefix: str) -> str:
        """
        Replace or insert a docstring.

        Args:
            lines: File lines
            line_number: Starting line number (where marker start is)
            original_text: Original docstring (if any)
            suggested_text: New docstring
            marker_prefix: Marker prefix (@llm-doc or @llm-class)

        Returns:
            Modified content
        """
        # Find the function/class definition
        # line_number is 1-indexed and points to marker start
        # Definition should be on the NEXT line after the marker
        marker_line_idx = line_number - 1
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

        # Look for existing docstring after the function definition
        docstring_start = None
        docstring_end = None

        # Start looking from the line after the function definition
        search_start = func_line_idx + 1

        for i in range(search_start, min(search_start + 10, len(lines))):
            line = lines[i].strip()

            # Skip empty lines
            if not line:
                continue

            if line.startswith('"""') or line.startswith("'''"):
                quote = '"""' if '"""' in line else "'''"
                docstring_start = i

                # Check if docstring ends on same line
                if line.count(quote) >= 2:
                    docstring_end = i
                else:
                    # Find end
                    for j in range(i + 1, len(lines)):
                        if quote in lines[j]:
                            docstring_end = j
                            break
                break
            else:
                # If we hit non-docstring code, stop searching
                break

        # Get indentation from the function definition line
        indent = ""
        if func_line_idx < len(lines):
            func_line_text = lines[func_line_idx]
            for char in func_line_text:
                if char in [' ', '\t']:
                    indent += char
                else:
                    break

            # Detect indentation style and add one level
            if '\t' in indent:
                # Project uses tabs
                indent += '\t'
            elif len(indent) >= 2:
                # Project uses spaces - detect the increment size
                # Common sizes: 2, 4, or 8 spaces
                # Assume same size as current indent (or 4 if indent is unusual)
                indent_size = len(indent)
                if indent_size % 4 == 0:
                    indent += '    '  # 4 spaces
                elif indent_size % 2 == 0:
                    indent += '  '  # 2 spaces
                else:
                    indent += '    '  # Default to 4 spaces
            else:
                # No indentation detected or single space - default to 4 spaces
                indent += '    '

        # Format new docstring
        formatted_docstring = self._format_docstring(suggested_text, indent)

        # Replace or insert
        if docstring_start is not None and docstring_end is not None:
            # Replace existing docstring
            lines[docstring_start:docstring_end + 1] = formatted_docstring.split('\n')
        else:
            # Insert new docstring after function definition
            insert_at = func_line_idx + 1
            docstring_lines = formatted_docstring.split('\n')
            for i, docstring_line in enumerate(docstring_lines):
                lines.insert(insert_at + i, docstring_line)

        # NOTE: Markers are NOT removed here - they will be removed in a final pass
        # after all documentation has been applied. This prevents issues with
        # line number shifts when processing multiple markers.

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

    def remove_all_markers(self, file_path: str) -> bool:
        """
        Remove all documentation markers from a file after all changes have been applied.

        This is called as a final cleanup step after all documentation has been inserted.
        Removing markers in a single pass (rather than during each application) prevents
        line number shifts that would cause subsequent markers to be misaligned.

        Args:
            file_path: Path to file to clean up

        Returns:
            True if successful, False otherwise
        """
        try:
            file_path = Path(file_path)

            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            lines = content.split('\n')

            # Use centralized marker patterns
            marker_patterns = MarkerPatterns.get_all_removal_patterns()

            # Remove markers from bottom to top (preserves line indices)
            for i in range(len(lines) - 1, -1, -1):
                for pattern in marker_patterns:
                    if pattern.match(lines[i]):
                        del lines[i]
                        break  # Move to next line after deleting

            # Write cleaned content back
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))

            return True

        except Exception as e:
            print(f"Error removing markers: {e}")
            return False

    def _replace_comment(self, lines: List[str], line_number: int,
                        original_text: str, suggested_text: str) -> str:
        """
        Replace or insert an inline comment.

        Args:
            lines: File lines
            line_number: Starting line number (where @llm-comm-start marker is)
            original_text: Original comment (if any)
            suggested_text: New comment text

        Returns:
            Modified content
        """
        # line_number is 1-indexed and points to @llm-comm-start marker
        marker_line_idx = line_number - 1

        # Find the code line (should be right after the marker)
        code_line_idx = None
        for i in range(marker_line_idx + 1, min(len(lines), marker_line_idx + 10)):
            line = lines[i].strip()
            # Skip empty lines and end marker
            if line and not line.startswith('#'):
                code_line_idx = i
                break

        if code_line_idx is None:
            # Fallback: assume code is right after marker
            code_line_idx = marker_line_idx + 1

        # Get indentation from the code line
        indent = ""
        if code_line_idx < len(lines):
            code_line_text = lines[code_line_idx]
            for char in code_line_text:
                if char in [' ', '\t']:
                    indent += char
                else:
                    break

        # Format comment
        formatted_comment = f"{indent}# {suggested_text.strip()}"

        # Insert comment above the code line
        lines.insert(code_line_idx, formatted_comment)

        # NOTE: Markers are NOT removed here - they will be removed in a final pass
        # after all documentation has been applied. This prevents issues with
        # line number shifts when processing multiple markers.

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
                print(f"No backups found for {file_path}")
                return False

            most_recent = backups[0]

            # Restore backup
            shutil.copy2(most_recent, file_path)
            print(f"✓ Restored from backup: {most_recent.name}")
            return True

        except Exception as e:
            print(f"Error during rollback: {e}")
            return False

    def list_backups(self) -> List[Path]:
        """
        List all available backups.

        Returns:
            List of backup file paths
        """
        if not self.backup_dir.exists():
            return []

        return sorted(
            self.backup_dir.glob("*.bak"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
