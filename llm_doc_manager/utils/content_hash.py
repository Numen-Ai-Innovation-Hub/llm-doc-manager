"""
Content hash calculation with normalization.

Calculates hierarchical SHA256 hashes (file/class/method levels) with
code normalization to ignore formatting changes.
"""

import hashlib
import re
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class CodeHash:
    """Represents a hash for a specific code scope."""
    scope_type: str  # 'FILE' | 'CLASS' | 'METHOD'
    scope_name: str  # file path, class name, or method name
    content_hash: str  # SHA256 hex digest
    line_start: int
    line_end: int


class ContentHasher:
    """Calculates normalized hierarchical hashes for code content."""

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
    def calculate_file_hash(file_path: str) -> CodeHash:
        """
        Calculate hash for entire file.

        Args:
            file_path: Path to file

        Returns:
            CodeHash for the file
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        lines = content.split('\n')
        content_hash = ContentHasher.calculate_hash(content)

        return CodeHash(
            scope_type='FILE',
            scope_name=file_path,
            content_hash=content_hash,
            line_start=1,
            line_end=len(lines)
        )

    @staticmethod
    def calculate_block_hashes(file_path: str, blocks: List) -> List[CodeHash]:
        """
        Calculate hashes for all detected marker blocks.

        Args:
            file_path: Path to file
            blocks: List of DetectedBlock objects from MarkerDetector

        Returns:
            List of CodeHash objects for each block
        """
        hashes = []

        for block in blocks:
            # Determine scope type and name based on marker type
            # Note: function_name is used for both functions AND classes
            # With strict validation in marker_detector, function_name is always set
            if block.marker_type.value == 'module_doc':
                scope_type = 'MODULE'
                scope_name = block.function_name or 'module'  # Module name or default
            elif block.marker_type.value == 'class_doc':
                scope_type = 'CLASS'
                scope_name = block.function_name  # Always set by validation
            elif block.marker_type.value == 'docstring':
                scope_type = 'METHOD'
                scope_name = block.function_name  # Always set by validation
            elif block.marker_type.value == 'comment':
                scope_type = 'COMMENT'
                scope_name = block.function_name  # Always set to f"block_{start_line}"
            else:
                # Fallback for unknown marker types
                scope_type = 'METHOD'
                scope_name = block.function_name or 'unknown'

            # Calculate hash of block content
            content_hash = ContentHasher.calculate_hash(block.full_code)

            hashes.append(CodeHash(
                scope_type=scope_type,
                scope_name=scope_name,
                content_hash=content_hash,
                line_start=block.start_line,
                line_end=block.end_line
            ))

        return hashes

    @staticmethod
    def calculate_all_hashes(file_path: str, blocks: List) -> Dict[str, List[CodeHash]]:
        """
        Calculate all hierarchical hashes in a single pass.

        Args:
            file_path: Path to file
            blocks: List of DetectedBlock objects

        Returns:
            Dict with keys 'file', 'modules', 'classes', 'methods', 'comments' containing CodeHash lists
        """
        result = {
            'file': [],
            'modules': [],
            'classes': [],
            'methods': [],
            'comments': []
        }

        # File-level hash
        file_hash = ContentHasher.calculate_file_hash(file_path)
        result['file'].append(file_hash)

        # Block-level hashes
        block_hashes = ContentHasher.calculate_block_hashes(file_path, blocks)

        for hash_obj in block_hashes:
            if hash_obj.scope_type == 'MODULE':
                result['modules'].append(hash_obj)
            elif hash_obj.scope_type == 'CLASS':
                result['classes'].append(hash_obj)
            elif hash_obj.scope_type == 'METHOD':
                result['methods'].append(hash_obj)
            elif hash_obj.scope_type == 'COMMENT':
                result['comments'].append(hash_obj)

        return result