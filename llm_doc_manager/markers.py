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
    DOCSTRING = "docstring"  # Method/function docstrings (@llm-doc)
    CLASS_DOC = "class_doc"  # Class documentation (@llm-class)
    COMMENT = "comment"      # Code comments (@llm-comm)


class MarkerPatterns:
    """Delimiter-based marker patterns."""

    # Delimiter markers for function/method documentation
    DOC_START = r"^\s*#\s*@llm-doc-start\s*$"
    DOC_END = r"^\s*#\s*@llm-doc-end\s*$"

    # Delimiter markers for class documentation
    CLASS_START = r"^\s*#\s*@llm-class-start\s*$"
    CLASS_END = r"^\s*#\s*@llm-class-end\s*$"

    # Delimiter markers for code comments
    COMM_START = r"^\s*#\s*@llm-comm-start\s*$"
    COMM_END = r"^\s*#\s*@llm-comm-end\s*$"


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
        # Compile all marker patterns
        self.patterns = {
            MarkerType.DOCSTRING: {
                'start': re.compile(MarkerPatterns.DOC_START),
                'end': re.compile(MarkerPatterns.DOC_END)
            },
            MarkerType.CLASS_DOC: {
                'start': re.compile(MarkerPatterns.CLASS_START),
                'end': re.compile(MarkerPatterns.CLASS_END)
            },
            MarkerType.COMMENT: {
                'start': re.compile(MarkerPatterns.COMM_START),
                'end': re.compile(MarkerPatterns.COMM_END)
            }
        }

    def detect_blocks(self, content: str, file_path: str = "") -> List[DetectedBlock]:
        """
        Detect all documentation blocks in the given content.

        Supports three types of markers:
        - @llm-doc: Method/function docstrings
        - @llm-class: Class documentation
        - @llm-comm: Code comments

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
            # Check which type of marker this is
            marker_type = None
            for mtype, patterns in self.patterns.items():
                if patterns['start'].match(lines[i]):
                    marker_type = mtype
                    break

            if marker_type:
                start_line = i + 1  # 1-indexed

                # Find corresponding end marker with nesting support
                end_line = None
                start_pattern = self.patterns[marker_type]['start']
                end_pattern = self.patterns[marker_type]['end']
                depth = 1  # We're inside one marker already

                for j in range(i + 1, len(lines)):
                    # Check for nested start markers of the same type
                    if start_pattern.match(lines[j]):
                        depth += 1
                    elif end_pattern.match(lines[j]):
                        depth -= 1
                        if depth == 0:
                            # Found the matching end marker
                            end_line = j + 1  # 1-indexed
                            break

                if end_line is None:
                    # No matching end marker - skip this start marker
                    i += 1
                    continue

                # Extract code block (everything between markers)
                block_lines = lines[i + 1:end_line - 1]  # Exclude marker lines
                full_code = '\n'.join(block_lines)

                # Analyze the block based on marker type
                if marker_type == MarkerType.DOCSTRING:
                    analysis = self._analyze_block(block_lines)
                elif marker_type == MarkerType.CLASS_DOC:
                    analysis = self._analyze_class_block(block_lines)
                else:  # MarkerType.COMMENT
                    analysis = self._analyze_comment_block(block_lines)

                blocks.append(DetectedBlock(
                    file_path=file_path,
                    start_line=start_line,
                    end_line=end_line,
                    full_code=full_code,
                    has_docstring=analysis['has_docstring'],
                    current_docstring=analysis['docstring'],
                    function_name=analysis.get('function_name'),
                    marker_type=marker_type
                ))

                # Move to next line (to allow scanning for nested markers of different types)
                i += 1
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

        # Extract docstring using shared method
        docstring = self._extract_docstring(block_lines, func_line_idx)
        if docstring:
            result['has_docstring'] = True
            result['docstring'] = docstring

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

    def _extract_docstring(self, block_lines: List[str], def_line_idx: int) -> Optional[str]:
        """
        Extract docstring from block after a definition line.

        Args:
            block_lines: Lines of code in the block
            def_line_idx: Index of the definition line (function/class)

        Returns:
            Docstring text if found and valid, None otherwise
        """
        docstring_start = None
        docstring_end = None
        quote_type = None

        for i in range(def_line_idx + 1, len(block_lines)):
            line = block_lines[i].strip()

            if not line:
                continue

            if line.startswith('"""') or line.startswith("'''"):
                quote_type = '"""' if '"""' in line else "'''"
                docstring_start = i

                if line.count(quote_type) >= 2:
                    docstring_end = i
                else:
                    for j in range(i + 1, len(block_lines)):
                        if quote_type in block_lines[j]:
                            docstring_end = j
                            break
                break
            else:
                break

        if docstring_start is not None and docstring_end is not None:
            docstring_lines = block_lines[docstring_start:docstring_end + 1]
            docstring_text = '\n'.join(docstring_lines)
            docstring_text = docstring_text.strip().strip('"""').strip("'''").strip()

            if docstring_text and not self._is_placeholder(docstring_text):
                return docstring_text

        return None

    def _analyze_class_block(self, block_lines: List[str]) -> Dict:
        """
        Analyze a class block to determine if it has a docstring.

        Args:
            block_lines: Lines of code in the block

        Returns:
            Dictionary with analysis results
        """
        result = {
            'has_docstring': False,
            'docstring': None,
            'function_name': None
        }

        # Find class definition
        def_line_idx = None
        for i, line in enumerate(block_lines):
            stripped = line.strip()
            if stripped.startswith('class '):
                def_line_idx = i
                # Extract class name
                match = re.match(r'class\s+(\w+)', stripped)
                if match:
                    result['function_name'] = match.group(1)
                break

        if def_line_idx is None:
            return result

        # Extract docstring using shared method
        docstring = self._extract_docstring(block_lines, def_line_idx)
        if docstring:
            result['has_docstring'] = True
            result['docstring'] = docstring

        return result

    def _analyze_comment_block(self, block_lines: List[str]) -> Dict:
        """
        Analyze a code comment block.

        Args:
            block_lines: Lines of code in the block

        Returns:
            Dictionary with analysis results
        """
        # For comments, there's no docstring - we'll generate comments
        # Extract existing comments if any
        existing_comments = []
        for line in block_lines:
            stripped = line.strip()
            if stripped.startswith('#') and not stripped.startswith('#@llm'):
                # Remove the # and add to existing comments
                comment_text = stripped[1:].strip()
                if comment_text:
                    existing_comments.append(comment_text)

        result = {
            'has_docstring': bool(existing_comments),
            'docstring': '\n'.join(existing_comments) if existing_comments else None,
            'function_name': None
        }

        return result

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
            # Determine task type based on marker type and docstring presence
            if block.marker_type == MarkerType.COMMENT:
                # Comment blocks: generate or validate comments
                task_type = "validate_comment" if block.has_docstring else "generate_comment"
            elif block.marker_type == MarkerType.CLASS_DOC:
                # Class documentation: generate or validate class docs
                task_type = "validate_class" if block.has_docstring else "generate_class"
            else:  # MarkerType.DOCSTRING (methods/functions)
                # Function/method docstrings: generate or validate
                task_type = "validate_docstring" if block.has_docstring else "generate_docstring"

            markers.append({
                'file_path': block.file_path,
                'line_number': block.start_line,
                'line_content': f"# Marker for {block.marker_type.value}: {block.function_name or 'N/A'}",
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
