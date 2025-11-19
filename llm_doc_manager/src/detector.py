"""
Simple file-level change detection.

Detects if a file has changed by comparing current hash with stored hash.
"""

from ..utils.content_hash import ContentHasher
from .hashing import HashStorage


class ChangeDetector:
    """Detects file-level changes by comparing hashes."""

    def __init__(self, storage: HashStorage):
        """
        Initialize change detector.

        Args:
            storage: HashStorage instance for retrieving stored hashes
        """
        self.storage = storage

    def file_changed(self, file_path: str) -> bool:
        """
        Check if a file has changed since last sync.

        Args:
            file_path: Path to file to check

        Returns:
            True if file changed or is new, False if unchanged
        """
        # Calculate current hash
        current_hash = ContentHasher.calculate_file_hash(file_path)

        # Get stored hash
        stored_hash = self.storage.get_file_hash(file_path)

        # No stored hash = new file = changed
        if stored_hash is None:
            return True

        # Compare hashes
        return current_hash != stored_hash

    def update_file_hash(self, file_path: str):
        """
        Update stored hash for a file after processing.

        Args:
            file_path: Path to file to update
        """
        current_hash = ContentHasher.calculate_file_hash(file_path)
        self.storage.store_file_hash(file_path, current_hash)