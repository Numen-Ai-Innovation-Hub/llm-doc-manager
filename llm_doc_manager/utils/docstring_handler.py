"""
Utilities for working with docstrings.

Provides functions for extracting and manipulating docstrings
to avoid code duplication between modules.
"""

import re
from typing import Optional, Tuple


def extract_docstring(code: str) -> Optional[str]:
    """
    Extract docstring from Python code.

    Handles both triple-double-quote and triple-single-quote docstrings.

    Args:
        code (str): Python code containing potential docstring

    Returns:
        Optional[str]: Extracted docstring content (without quotes), or None if no
        docstring found
    """
    # Match both """ and ''' docstrings
    # Pattern: captures content between triple quotes
    patterns = [
        r'"""(.*?)"""',  # Triple double quotes
        r"'''(.*?)'''",  # Triple single quotes
    ]

    for pattern in patterns:
        match = re.search(pattern, code, re.DOTALL)
        if match:
            return match.group(1).strip()

    return None


def find_docstring_location(lines: list, start_idx: int) -> Tuple[Optional[int], Optional[int]]:
    """
    Find the start and end line indices of a docstring.

    Searches from start_idx forward to find triple-quote delimiters.
    Stops searching when encountering markers or non-docstring code.

    Args:
        lines (list): List of code lines (0-indexed)
        start_idx (int): Line index to start searching from (0-indexed)

    Returns:
        Tuple[Optional[int], Optional[int]]: (start_line_idx, end_line_idx) of
        docstring, or (None, None) if not found. Indices are 0-based.
    """
    # Look for opening triple quotes
    docstring_start = None
    docstring_end = None
    quote_type = None

    for i in range(start_idx, len(lines)):  # Search until end of file (no arbitrary limit)
        line = lines[i].strip()

        # Stop if we hit an END marker (end of current block)
        if line.startswith('# @llm-') and '-end' in line:
            break

        # Check for triple quotes
        if '"""' in line or "'''" in line:
            if docstring_start is None:
                # Found opening
                docstring_start = i
                quote_type = '"""' if '"""' in line else "'''"

                # Check if it's a one-liner docstring
                if line.count(quote_type) >= 2:
                    docstring_end = i
                    break
            else:
                # Found closing
                if quote_type in line:
                    docstring_end = i
                    break
        elif docstring_start is None and line and not line.startswith('#'):
            # Found non-comment, non-empty line before docstring
            # This means there's no docstring in this location
            break

    if docstring_start is not None and docstring_end is not None:
        return (docstring_start, docstring_end)

    return (None, None)