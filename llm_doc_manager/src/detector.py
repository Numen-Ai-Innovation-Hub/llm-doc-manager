"""
Change detection logic using hierarchical hash comparison.

Detects changes at file/class/method levels by comparing current hashes
with stored hashes from previous runs.
"""

from dataclasses import dataclass
from typing import List, Dict, Set
from ..utils.content_hash import ContentHasher, CodeHash
from .hashing import HashStorage, StoredHash


@dataclass
class ChangeReport:
    """Report of detected changes in a file."""
    file_path: str
    scope: str  # 'NONE' | 'METHOD' | 'CLASS' | 'FILE'
    changed_items: List[str]  # Names of changed scopes
    unchanged_items: List[str]  # Names of unchanged scopes
    new_items: List[str]  # Names of new scopes (not in DB)
    reason: str  # Human-readable explanation


class ChangeDetector:
    """Detects changes by comparing current and stored hashes."""

    def __init__(self, storage: HashStorage):
        """
        Initialize change detector.

        Args:
            storage: HashStorage instance for retrieving stored hashes
        """
        self.storage = storage

    def detect_changes(
        self,
        file_path: str,
        blocks: List
    ) -> tuple:
        """
        Detect changes in a file by comparing hashes.

        Args:
            file_path: Path to file
            blocks: List of DetectedBlock objects from MarkerDetector

        Returns:
            Tuple of (ChangeReport, current_hashes dict) for reuse
        """
        # Calculate current hashes (once)
        current_hashes = ContentHasher.calculate_all_hashes(file_path, blocks)

        # Retrieve stored hashes
        stored_hashes = self.storage.get_file_hashes(file_path)

        # Check if file exists in DB
        if not stored_hashes['file'] and not stored_hashes['classes'] and not stored_hashes['methods']:
            # New file - all blocks are new
            new_items = self._extract_scope_names(current_hashes)
            report = ChangeReport(
                file_path=file_path,
                scope='FILE',
                changed_items=[],
                unchanged_items=[],
                new_items=new_items,
                reason='New file - no previous hashes stored'
            )
            return report, current_hashes

        # Compare file-level hash
        file_changed = self._compare_file_hash(
            current_hashes['file'][0] if current_hashes['file'] else None,
            stored_hashes['file'][0] if stored_hashes['file'] else None
        )

        if not file_changed:
            # No changes at all
            report = ChangeReport(
                file_path=file_path,
                scope='NONE',
                changed_items=[],
                unchanged_items=self._extract_scope_names(current_hashes),
                new_items=[],
                reason='File hash unchanged - no modifications'
            )
            return report, current_hashes

        # File changed - apply hierarchical detection (METHOD > CLASS > FILE)
        # This prevents false positives when inner scopes change

        # Check method level first (most specific)
        method_changes = self._compare_scope_hashes(
            current_hashes['methods'],
            stored_hashes['methods']
        )

        # Check class level (intermediate)
        class_changes = self._compare_scope_hashes(
            current_hashes['classes'],
            stored_hashes['classes']
        )

        # Hierarchical logic: report the most specific change
        if method_changes['changed'] or method_changes['new']:
            # Priority 1: Method-level changes detected
            # Ignore class/file changes (they're reflections of method changes)
            report = ChangeReport(
                file_path=file_path,
                scope='METHOD',
                changed_items=method_changes['changed'],
                unchanged_items=method_changes['unchanged'],
                new_items=method_changes['new'],
                reason=self._format_method_reason(method_changes)
            )
            return report, current_hashes

        elif class_changes['changed'] or class_changes['new']:
            # Priority 2: Class-level changes (outside of methods)
            # Ignore file changes (they're reflections of class changes)
            report = ChangeReport(
                file_path=file_path,
                scope='CLASS',
                changed_items=class_changes['changed'],
                unchanged_items=class_changes['unchanged'],
                new_items=class_changes['new'],
                reason=self._format_class_reason(class_changes)
            )
            return report, current_hashes

        # File hash changed but no class/method changes detected
        # This means formatting/comment changes only
        report = ChangeReport(
            file_path=file_path,
            scope='NONE',
            changed_items=[],
            unchanged_items=self._extract_scope_names(current_hashes),
            new_items=[],
            reason='Only formatting/comment changes detected (normalized hashes match)'
        )
        return report, current_hashes

    def _compare_file_hash(
        self,
        current: CodeHash,
        stored: StoredHash
    ) -> bool:
        """
        Compare file-level hashes.

        Returns:
            True if file changed, False otherwise
        """
        if not current or not stored:
            return True  # Treat missing hash as changed

        return current.content_hash != stored.content_hash

    def _compare_scope_hashes(
        self,
        current_list: List[CodeHash],
        stored_list: List[StoredHash]
    ) -> Dict[str, List[str]]:
        """
        Compare hashes for a specific scope (classes or methods).

        Returns:
            Dict with 'changed', 'unchanged', 'new' lists of scope names
        """
        result = {
            'changed': [],
            'unchanged': [],
            'new': []
        }

        # Create lookup dict for stored hashes
        stored_dict = {s.scope_name: s.content_hash for s in stored_list}

        # Track which stored items we've seen
        seen_stored = set()

        for current in current_list:
            scope_name = current.scope_name

            if scope_name not in stored_dict:
                # New scope
                result['new'].append(scope_name)
            elif current.content_hash != stored_dict[scope_name]:
                # Changed scope
                result['changed'].append(scope_name)
                seen_stored.add(scope_name)
            else:
                # Unchanged scope
                result['unchanged'].append(scope_name)
                seen_stored.add(scope_name)

        return result

    def _extract_scope_names(self, hashes: Dict[str, List[CodeHash]]) -> List[str]:
        """Extract all scope names from hash dictionary."""
        names = []
        for scope_list in [hashes['classes'], hashes['methods']]:
            names.extend([h.scope_name for h in scope_list])
        return names

    def _format_class_reason(self, changes: Dict[str, List[str]]) -> str:
        """Format human-readable reason for class-level changes."""
        parts = []

        if changes['changed']:
            parts.append(f"{len(changes['changed'])} class(es) modified")
        if changes['new']:
            parts.append(f"{len(changes['new'])} new class(es)")

        return ' | '.join(parts)

    def _format_method_reason(self, changes: Dict[str, List[str]]) -> str:
        """Format human-readable reason for method-level changes."""
        parts = []

        if changes['changed']:
            parts.append(f"{len(changes['changed'])} method(s) modified")
        if changes['new']:
            parts.append(f"{len(changes['new'])} new method(s)")

        return ' | '.join(parts)

    def update_stored_hashes(self, file_path: str, current_hashes: Dict):
        """
        Update stored hashes for a file after processing.

        Args:
            file_path: Path to file
            current_hashes: Pre-calculated hashes from detect_changes()
        """
        # Delete old hashes for this file
        self.storage.delete_file_hashes(file_path)

        # Store new hashes
        for hash_obj in current_hashes['file']:
            self.storage.store_hash(
                file_path=hash_obj.scope_name,
                scope_type=hash_obj.scope_type,
                scope_name=hash_obj.scope_name,
                content_hash=hash_obj.content_hash,
                line_start=hash_obj.line_start,
                line_end=hash_obj.line_end
            )

        for hash_obj in current_hashes['classes']:
            self.storage.store_hash(
                file_path=file_path,
                scope_type=hash_obj.scope_type,
                scope_name=hash_obj.scope_name,
                content_hash=hash_obj.content_hash,
                line_start=hash_obj.line_start,
                line_end=hash_obj.line_end
            )

        for hash_obj in current_hashes['methods']:
            self.storage.store_hash(
                file_path=file_path,
                scope_type=hash_obj.scope_type,
                scope_name=hash_obj.scope_name,
                content_hash=hash_obj.content_hash,
                line_start=hash_obj.line_start,
                line_end=hash_obj.line_end
            )