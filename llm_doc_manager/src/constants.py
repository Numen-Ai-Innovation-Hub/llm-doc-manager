"""
Shared constants for LLM Doc Manager.

Centralizes mappings and configuration values used across multiple modules.
"""

from ..utils.marker_detector import MarkerType

# Mapping from marker types to task types for documentation processing
# This ensures consistent task creation across all components
MARKER_TO_TASK_TYPE = {
    MarkerType.DOCSTRING: 'generate_docstring',  # For methods/functions
    MarkerType.CLASS_DOC: 'generate_class',       # For classes (uses class_generate.md template)
    MarkerType.COMMENT: 'generate_comment'
}

# String-based mapping for legacy compatibility
# Used when marker_type comes as string value instead of enum
MARKER_VALUE_TO_TASK_TYPE = {
    'docstring': 'generate_docstring',  # For methods/functions
    'class_doc': 'generate_class',       # For classes (uses class_generate.md template)
    'comment': 'generate_comment'
}

# Human-readable labels for task types (used in CLI display)
TASK_TYPE_LABELS = {
    'generate_docstring': '📝 Method/Function Docstring',
    'generate_class': '🏛️  Class Documentation',
    'generate_comment': '💬 Comment Block',
    'validate_docstring': '✓ Validate Method Docstring',
    'validate_class': '✓ Validate Class Documentation',
    'validate_comment': '✓ Validate Comment'
}