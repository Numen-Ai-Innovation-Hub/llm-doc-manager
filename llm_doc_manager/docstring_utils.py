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

    Example:
        >>> code = '''def foo():\\n    """This is a docstring."""\\n    pass'''
        >>> extract_docstring(code)
        'This is a docstring.'
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


def extract_function_signature(code: str) -> Optional[str]:
    """
    Extract function or method signature from Python code.

    Args:
        code (str): Python code containing function/method definition

    Returns:
        Optional[str]: Function signature (e.g., "def foo(x, y):"), or None if not
        found

    Example:
        >>> code = "def foo(x, y):\\n    pass"
        >>> extract_function_signature(code)
        'def foo(x, y):'
    """
    # Match function/method definition (including async)
    pattern = r'^\s*(async\s+)?def\s+\w+\s*\([^)]*\)\s*(?:->.*)?:'
    match = re.search(pattern, code, re.MULTILINE)

    if match:
        return match.group(0).strip()

    return None


def extract_class_signature(code: str) -> Optional[str]:
    """
    Extract class signature from Python code.

    Args:
        code (str): Python code containing class definition

    Returns:
        Optional[str]: Class signature (e.g., "class Foo:"), or None if not found

    Example:
        >>> code = "class Foo(Bar):\\n    pass"
        >>> extract_class_signature(code)
        'class Foo(Bar):'
    """
    # Match class definition
    pattern = r'^\s*class\s+\w+\s*(?:\([^)]*\))?\s*:'
    match = re.search(pattern, code, re.MULTILINE)

    if match:
        return match.group(0).strip()

    return None


def has_docstring(code: str) -> bool:
    """
    Check if code contains a docstring.

    Args:
        code (str): Python code to check

    Returns:
        bool: True if docstring is present, False otherwise

    Example:
        >>> has_docstring('def foo():\\n    """Docstring"""\\n    pass')
        True
        >>> has_docstring('def foo():\\n    pass')
        False
    """
    return extract_docstring(code) is not None


def find_docstring_location(lines: list, start_idx: int) -> Tuple[Optional[int], Optional[int]]:
    """
    Find the start and end line indices of a docstring.

    Searches from start_idx forward to find triple-quote delimiters.

    Args:
        lines (list): List of code lines (0-indexed)
        start_idx (int): Line index to start searching from (0-indexed)

    Returns:
        Tuple[Optional[int], Optional[int]]: (start_line_idx, end_line_idx) of
        docstring, or (None, None) if not found. Indices are 0-based.

    Example:
        >>> lines = ['def foo():', '    """', '    Docstring', '    """', '    pass']
        >>> find_docstring_location(lines, 0)
        (1, 3)
    """
    # Look for opening triple quotes
    docstring_start = None
    docstring_end = None
    quote_type = None

    for i in range(start_idx, min(len(lines), start_idx + 20)):
        line = lines[i].strip()

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

    if docstring_start is not None and docstring_end is not None:
        return (docstring_start, docstring_end)

    return (None, None)


def strip_indentation(text: str) -> str:
    """
    Remove common leading indentation from all lines.

    Args:
        text (str): Text with potential indentation

    Returns:
        str: Text with common indentation removed

    Example:
        >>> strip_indentation("    Line 1\\n    Line 2")
        'Line 1\\nLine 2'
    """
    lines = text.split('\n')

    # Find minimum indentation (ignoring empty lines)
    min_indent = float('inf')
    for line in lines:
        if line.strip():  # Skip empty lines
            indent = len(line) - len(line.lstrip())
            min_indent = min(min_indent, indent)

    # Handle case where all lines are empty
    if min_indent == float('inf'):
        return text

    # Remove common indentation
    stripped_lines = []
    for line in lines:
        if line.strip():  # Non-empty line
            stripped_lines.append(line[min_indent:])
        else:  # Empty line
            stripped_lines.append('')

    return '\n'.join(stripped_lines)