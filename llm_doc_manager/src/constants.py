"""
Shared constants for LLM Doc Manager.

Centralizes mappings and configuration values used across multiple modules.
"""

from ..utils.marker_detector import MarkerType

# Mapping from marker types to task types for documentation processing
# This ensures consistent task creation across all components
MARKER_TO_TASK_TYPE = {
    MarkerType.MODULE_DOC: 'generate_module',    # For modules (uses module_generate.md template)
    MarkerType.DOCSTRING: 'generate_docstring',  # For methods/functions
    MarkerType.CLASS_DOC: 'generate_class',      # For classes (uses class_generate.md template)
    MarkerType.COMMENT: 'generate_comment'       # For code comments
}

# String-based mapping for legacy compatibility
# Used when marker_type comes as string value instead of enum
MARKER_VALUE_TO_TASK_TYPE = {
    'module_doc': 'generate_module',     # For modules
    'docstring': 'generate_docstring',   # For methods/functions
    'class_doc': 'generate_class',       # For classes (uses class_generate.md template)
    'comment': 'generate_comment'        # For code comments
}

# Human-readable labels for task types (used in CLI display)
TASK_TYPE_LABELS = {
    'generate_module': '📦 Module Documentation',
    'generate_docstring': '📝 Method/Function Docstring',
    'generate_class': '🏛️  Class Documentation',
    'generate_comment': '💬 Comment Block',
    'validate_module': '✓ Validate Module Documentation',
    'validate_docstring': '✓ Validate Method Docstring',
    'validate_class': '✓ Validate Class Documentation',
    'validate_comment': '✓ Validate Comment'
}

# Processing order for tasks (ensures module docs are generated before classes, etc.)
# Tasks MUST be processed in this order to maintain documentation hierarchy
TASK_PROCESSING_ORDER = [
    'generate_module',    # 1st - Module-level documentation
    'validate_module',    # Validate modules immediately after generation
    'generate_class',     # 2nd - Class documentation
    'validate_class',     # Validate classes immediately after generation
    'generate_docstring', # 3rd - Method/function documentation
    'validate_docstring', # Validate methods immediately after generation
    'generate_comment',   # 4th - Code comments (lowest priority)
    'validate_comment'    # Validate comments last
]