"""
Line number handling utilities.

This module provides type hints and conversion utilities to prevent
off-by-one errors when working with line numbers.

Convention:
- Internal (code operations): 0-indexed (list/array indices)
- External (user-facing, storage): 1-indexed (human-readable)
"""

from typing import NewType

# Type aliases for clarity
InternalLineNumber = NewType('InternalLineNumber', int)  # 0-indexed
ExternalLineNumber = NewType('ExternalLineNumber', int)  # 1-indexed


def to_internal(external: int) -> int:
    """
    Convert external (1-indexed) line number to internal (0-indexed).

    Args:
        external (int): 1-indexed line number (as shown to user)

    Returns:
        int: 0-indexed line number (for array access)

    Example:
        >>> to_internal(1)
        0
        >>> to_internal(42)
        41
    """
    return external - 1


def to_external(internal: int) -> int:
    """
    Convert internal (0-indexed) line number to external (1-indexed).

    Args:
        internal (int): 0-indexed line number (array index)

    Returns:
        int: 1-indexed line number (for display to user)

    Example:
        >>> to_external(0)
        1
        >>> to_external(41)
        42
    """
    return internal + 1


def validate_external(line_number: int, total_lines: int) -> bool:
    """
    Validate that external line number is within valid range.

    Args:
        line_number (int): 1-indexed line number to validate
        total_lines (int): Total number of lines in file

    Returns:
        bool: True if valid, False otherwise

    Example:
        >>> validate_external(1, 100)
        True
        >>> validate_external(0, 100)
        False
        >>> validate_external(101, 100)
        False
    """
    return 1 <= line_number <= total_lines


def validate_internal(line_index: int, total_lines: int) -> bool:
    """
    Validate that internal line index is within valid range.

    Args:
        line_index (int): 0-indexed line index to validate
        total_lines (int): Total number of lines in file

    Returns:
        bool: True if valid, False otherwise

    Example:
        >>> validate_internal(0, 100)
        True
        >>> validate_internal(-1, 100)
        False
        >>> validate_internal(100, 100)
        False
    """
    return 0 <= line_index < total_lines