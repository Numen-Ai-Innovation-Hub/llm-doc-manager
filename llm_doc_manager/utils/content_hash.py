"""
Content hash calculation with normalization.

Calculates SHA256 hash for entire files with code normalization
to ignore formatting changes.
"""

import hashlib
import re


class ContentHasher:
    """Calculates normalized file-level hashes for code content."""

    @staticmethod
    def normalize_code(code: str) -> str:
        """
        Normalize code by removing formatting artifacts.

        Removes:
        - Leading/trailing whitespace per line
        - Blank lines
        - Inline comments (# ...)

        Args:
            code: Raw code string

        Returns:
            Normalized code string
        """
        lines = []
        for line in code.split('\n'):
            # Remove inline comments
            line = re.sub(r'#.*$', '', line)
            # Strip whitespace
            line = line.strip()
            # Skip blank lines
            if line:
                lines.append(line)

        return '\n'.join(lines)

    @staticmethod
    def calculate_hash(content: str) -> str:
        """
        Calculate SHA256 hash of content.

        Args:
            content: Code content to hash

        Returns:
            SHA256 hex digest
        """
        normalized = ContentHasher.normalize_code(content)
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

    @staticmethod
    def calculate_file_hash(file_path: str) -> str:
        """
        Calculate hash for entire file.

        Args:
            file_path: Path to file

        Returns:
            SHA256 hex digest of file content
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        return ContentHasher.calculate_hash(content)