"""
Change detection logic using independent hash comparison.

Detects changes at file/class/method levels independently by comparing
current hashes with stored hashes from previous runs. When both class
and method changes are detected, reports BOTH (Option 1: Report BOTH).
"""

import hashlib
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Set, Optional
from ..utils.content_hash import ContentHasher, CodeHash
from .hashing import HashStorage, StoredHash


@dataclass
class ChangeReport:
    """Report of detected changes in a file."""
    file_path: str
    scope: str  # 'NONE' | 'FILE' | 'MODULE' | 'CLASS' | 'METHOD' | 'COMMENT'
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
            Tuple of (List[ChangeReport], current_hashes dict)
            - List can contain 0, 1, or multiple ChangeReports
            - Multiple reports occur when both CLASS and METHOD changes detected
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
            return [report], current_hashes

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
            return [report], current_hashes

        # File changed - detect changes at all levels independently
        # Report ALL detected changes (MODULE + CLASS + METHOD + COMMENT)

        # Check module level
        module_changes = self._compare_scope_hashes(
            current_hashes['modules'],
            stored_hashes.get('modules', [])
        )

        # Check class level
        class_changes = self._compare_scope_hashes(
            current_hashes['classes'],
            stored_hashes['classes']
        )

        # Check method level
        method_changes = self._compare_scope_hashes(
            current_hashes['methods'],
            stored_hashes['methods']
        )

        # Check comment level
        comment_changes = self._compare_scope_hashes(
            current_hashes['comments'],
            stored_hashes.get('comments', [])
        )

        # Collect all reports (can be multiple)
        reports = []

        # Add module-level report if module changed
        if module_changes['changed'] or module_changes['new']:
            reports.append(ChangeReport(
                file_path=file_path,
                scope='MODULE',
                changed_items=module_changes['changed'],
                unchanged_items=module_changes['unchanged'],
                new_items=module_changes['new'],
                reason=self._format_module_reason(module_changes)
            ))

        # Add class-level report if classes changed
        if class_changes['changed'] or class_changes['new']:
            reports.append(ChangeReport(
                file_path=file_path,
                scope='CLASS',
                changed_items=class_changes['changed'],
                unchanged_items=class_changes['unchanged'],
                new_items=class_changes['new'],
                reason=self._format_class_reason(class_changes)
            ))

        # Add method-level report if methods changed
        if method_changes['changed'] or method_changes['new']:
            reports.append(ChangeReport(
                file_path=file_path,
                scope='METHOD',
                changed_items=method_changes['changed'],
                unchanged_items=method_changes['unchanged'],
                new_items=method_changes['new'],
                reason=self._format_method_reason(method_changes)
            ))

        # Add comment-level report if comments changed
        if comment_changes['changed'] or comment_changes['new']:
            reports.append(ChangeReport(
                file_path=file_path,
                scope='COMMENT',
                changed_items=comment_changes['changed'],
                unchanged_items=comment_changes['unchanged'],
                new_items=comment_changes['new'],
                reason=self._format_comment_reason(comment_changes)
            ))

        # If no changes detected at any level, file hash changed due to formatting only
        if not reports:
            reports.append(ChangeReport(
                file_path=file_path,
                scope='NONE',
                changed_items=[],
                unchanged_items=self._extract_scope_names(current_hashes),
                new_items=[],
                reason='Only formatting/comment changes detected (normalized hashes match)'
            ))

        # Return list of reports (can be 0, 1, or multiple)
        return reports, current_hashes

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

    def _format_module_reason(self, changes: Dict[str, List[str]]) -> str:
        """Format human-readable reason for module-level changes."""
        parts = []

        if changes['changed']:
            parts.append(f"Module modified")
        if changes['new']:
            parts.append(f"New module")

        return ' | '.join(parts)

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

    def _format_comment_reason(self, changes: Dict[str, List[str]]) -> str:
        """Format human-readable reason for comment-level changes."""
        parts = []

        if changes['changed']:
            parts.append(f"{len(changes['changed'])} comment(s) modified")
        if changes['new']:
            parts.append(f"{len(changes['new'])} new comment(s)")

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

        # Store new hashes for all scope types
        for scope_key in ['file', 'modules', 'classes', 'methods', 'comments']:
            for hash_obj in current_hashes.get(scope_key, []):
                self.storage.store_hash(
                    file_path=file_path,
                    scope_type=hash_obj.scope_type,
                    scope_name=hash_obj.scope_name,
                    content_hash=hash_obj.content_hash,
                    line_start=hash_obj.line_start,
                    line_end=hash_obj.line_end
                )

    def detect_docs_changes(
        self,
        project_root: str,
        db_connection
    ) -> Dict[str, bool]:
        """
        Detect if source files have changed since documentation was generated.

        Compares current source file hashes with hashes stored in
        generated_documentation table to determine if docs need regeneration.

        Args:
            project_root: Root directory of project
            db_connection: Database connection to query generated_documentation

        Returns:
            Dictionary with documentation types and whether they need regeneration:
            {
                "docs_changed": bool,  # True if any source changed
                "readme": bool,        # readme.md needs update
                "architecture": bool,  # architecture.md needs update
                "glossary": bool,      # glossary.md needs update
                "whereiwas": bool,     # whereiwas.md needs update (git-based)
                "modules": List[str]   # List of module docs needing update
            }
        """
        cursor = db_connection.cursor()
        project_path = Path(project_root)

        result = {
            "docs_changed": False,
            "readme": False,
            "architecture": False,
            "glossary": False,
            "whereiwas": False,
            "modules": []
        }

        # Get all generated documentation records
        cursor.execute("""
            SELECT doc_path, doc_type, file_path, source_hash
            FROM generated_documentation
        """)
        docs = cursor.fetchall()

        if not docs:
            # No docs generated yet - mark all as needing generation
            result["docs_changed"] = True
            result["readme"] = True
            result["architecture"] = True
            result["glossary"] = True
            result["whereiwas"] = True
            return result

        # Check each documentation file
        for doc_path, doc_type, source_files_str, stored_hash in docs:
            # Parse source files (comma-separated)
            source_files = source_files_str.split(",") if source_files_str else []

            # Calculate current hash of source files
            current_hash = self._calculate_source_files_hash(
                project_path,
                source_files
            )

            # Compare hashes
            if current_hash != stored_hash:
                result["docs_changed"] = True

                # Mark specific doc type as changed
                if doc_type == "readme":
                    result["readme"] = True
                elif doc_type == "architecture":
                    result["architecture"] = True
                elif doc_type == "glossary":
                    result["glossary"] = True
                elif doc_type == "whereiwas":
                    result["whereiwas"] = True
                elif doc_type == "module":
                    result["modules"].append(doc_path)

        return result

    def _calculate_source_files_hash(
        self,
        project_root: Path,
        source_files: List[str]
    ) -> str:
        """
        Calculate combined hash of multiple source files.

        Args:
            project_root: Project root directory
            source_files: List of relative file paths

        Returns:
            SHA256 hash of combined file contents
        """
        hasher = hashlib.sha256()

        for file_path in sorted(source_files):
            if not file_path.strip():
                continue

            full_path = project_root / file_path
            try:
                if full_path.exists():
                    content = full_path.read_bytes()
                    hasher.update(content)
            except Exception:
                # File might have been deleted - treat as changed
                pass

        return hasher.hexdigest()