"""
Marker definitions and detection logic.

This module defines delimiter-based markers for function documentation.
Uses @llm-doc-start and @llm-doc-end to mark functions for documentation.
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum


class MarkerType(Enum):
    """Types of documentation markers."""
    DOCSTRING = "docstring"  # Unified type - auto-detects generate vs validate


class MarkerPatterns:
    """Delimiter-based marker patterns."""

    # Delimiter markers for function documentation
    DOC_START = r"^\s*#\s*@llm-doc-start\s*$"
    DOC_END = r"^\s*#\s*@llm-doc-end\s*$"


@dataclass
class DetectedBlock:
    """Represents a detected documentation block."""
    file_path: str
    start_line: int
    end_line: int
    full_code: str
    has_docstring: bool
    current_docstring: Optional[str]
    function_name: Optional[str]
    marker_type: MarkerType


class MarkerDetector:
    """Detects delimiter-based documentation markers in code."""

    def __init__(self):
        """Initialize marker detector."""
        self.start_pattern = re.compile(MarkerPatterns.DOC_START)
        self.end_pattern = re.compile(MarkerPatterns.DOC_END)

    def detect_blocks(self, content: str, file_path: str = "") -> List[DetectedBlock]:
        """
        Detect all documentation blocks in the given content.

        A documentation block is defined by @llm-doc-start and @llm-doc-end markers.
        The function code between these markers is extracted completely.

        Args:
            content: The file content to search
            file_path: Optional path to the file (for context)

        Returns:
            List of detected blocks with their details
        """
        blocks = []
        lines = content.split('\n')

        i = 0
        while i < len(lines):
            # Look for start marker
            if self.start_pattern.match(lines[i]):
                start_line = i + 1  # 1-indexed

                # Find corresponding end marker
                end_line = None
                for j in range(i + 1, len(lines)):
                    if self.end_pattern.match(lines[j]):
                        end_line = j + 1  # 1-indexed
                        break

                if end_line is None:
                    # No matching end marker - skip this start marker
                    i += 1
                    continue

                # Extract code block (everything between markers)
                block_lines = lines[i + 1:end_line - 1]  # Exclude marker lines
                full_code = '\n'.join(block_lines)

                # Analyze the block
                analysis = self._analyze_block(block_lines)

                blocks.append(DetectedBlock(
                    file_path=file_path,
                    start_line=start_line,
                    end_line=end_line,
                    full_code=full_code,
                    has_docstring=analysis['has_docstring'],
                    current_docstring=analysis['docstring'],
                    function_name=analysis['function_name'],
                    marker_type=MarkerType.DOCSTRING
                ))

                # Move past this block
                i = end_line
            else:
                i += 1

        return blocks

    def _analyze_block(self, block_lines: List[str]) -> Dict:
        """
        Analyze a code block to determine if it has a docstring.

        Args:
            block_lines: Lines of code in the block

        Returns:
            Dictionary with analysis results
        """
        result = {
            'has_docstring': False,
            'docstring': None,
            'function_name': None,
            'function_line_idx': None
        }

        # Find function definition
        func_line_idx = None
        for i, line in enumerate(block_lines):
            stripped = line.strip()
            if stripped.startswith('def ') or stripped.startswith('async def '):
                func_line_idx = i
                # Extract function name
                match = re.match(r'(?:async\s+)?def\s+(\w+)', stripped)
                if match:
                    result['function_name'] = match.group(1)
                break

        if func_line_idx is None:
            return result

        result['function_line_idx'] = func_line_idx

        # Look for docstring after function definition
        docstring_start = None
        docstring_end = None
        quote_type = None

        # Start from line after function definition
        for i in range(func_line_idx + 1, len(block_lines)):
            line = block_lines[i].strip()

            # Skip empty lines
            if not line:
                continue

            # Check for docstring start
            if line.startswith('"""') or line.startswith("'''"):
                quote_type = '"""' if '"""' in line else "'''"
                docstring_start = i

                # Single-line docstring?
                if line.count(quote_type) >= 2:
                    docstring_end = i
                else:
                    # Multi-line - find end
                    for j in range(i + 1, len(block_lines)):
                        if quote_type in block_lines[j]:
                            docstring_end = j
                            break
                break
            else:
                # Hit code before docstring - no docstring exists
                break

        # Extract docstring if found
        if docstring_start is not None and docstring_end is not None:
            docstring_lines = block_lines[docstring_start:docstring_end + 1]
            docstring_text = '\n'.join(docstring_lines)

            # Clean up the docstring
            docstring_text = docstring_text.strip()
            docstring_text = docstring_text.strip('"""').strip("'''").strip()

            # Check if it's a real docstring or placeholder
            if docstring_text and not self._is_placeholder(docstring_text):
                result['has_docstring'] = True
                result['docstring'] = docstring_text

        return result

    def _is_placeholder(self, docstring: str) -> bool:
        """
        Check if a docstring is just a placeholder.

        Args:
            docstring: The docstring text to check

        Returns:
            True if it's a placeholder, False otherwise
        """
        placeholders = [
            'to_do', 'todo', 'fixme', 'to do',
            'to_review', 'to review', 'placeholder',
            'add description', 'description here'
        ]

        lower = docstring.lower().strip()

        # Empty or very short
        if len(lower) < 5:
            return True

        # Contains placeholder keywords
        for placeholder in placeholders:
            if placeholder in lower:
                return True

        return False

    def detect_markers(self, content: str, file_path: str = "") -> List[Dict]:
        """
        Legacy method for backward compatibility with scanner.

        Converts new block-based detection to old marker format.

        Args:
            content: The file content to search
            file_path: Optional path to the file

        Returns:
            List of markers in legacy format
        """
        blocks = self.detect_blocks(content, file_path)
        markers = []

        for block in blocks:
            # Determine task type based on docstring presence
            if block.has_docstring:
                task_type = "validate_docstring"
            else:
                task_type = "generate_docstring"

            markers.append({
                'file_path': block.file_path,
                'line_number': block.start_line,
                'line_content': f"# @llm-doc-start (function: {block.function_name})",
                'marker_type': block.marker_type,
                'priority': 10,
                'task_type': task_type,
                'full_code': block.full_code,
                'current_docstring': block.current_docstring,
                'block_start': block.start_line,
                'block_end': block.end_line
            })

        return markers


def get_default_detector() -> MarkerDetector:
    """Get a marker detector with default patterns."""
    return MarkerDetector()
