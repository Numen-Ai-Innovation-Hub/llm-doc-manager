"""
Review formatter utilities.

Formats structured output schemas (Pydantic objects) into human-readable
text for display in the review command. Ensures all fields are visible
with deterministic ordering matching the schema definitions.
"""

import json
from typing import Optional
import logging

from .response_schemas import (
    ModuleDocstring,
    ClassDocstring,
    MethodDocstring,
    ValidationResult,
)


logger = logging.getLogger(__name__)


def format_module_docstring_for_review(schema: ModuleDocstring) -> str:
    """
    Format ModuleDocstring for review display.

    Shows all fields in schema order: summary, extended_description,
    typical_usage, notes. Displays "None" for empty optional fields.

    Args:
        schema: ModuleDocstring Pydantic object

    Returns:
        Formatted string for display
    """
    lines = []
    lines.append(f"Summary: {schema.summary}")
    lines.append("")
    lines.append(f"Extended Description:")
    lines.append(f"    {schema.extended_description}")
    lines.append("")

    if schema.typical_usage:
        lines.append(f"Typical Usage:")
        # Indent code example
        usage_lines = schema.typical_usage.split('\n')
        for line in usage_lines:
            lines.append(f"    {line}")
    else:
        lines.append(f"Typical Usage: None")
    lines.append("")

    lines.append(f"Notes: {schema.notes if schema.notes else 'None'}")

    return '\n'.join(lines)


def format_class_docstring_for_review(schema: ClassDocstring) -> str:
    """
    Format ClassDocstring for review display.

    Shows all fields in schema order: summary, extended_description,
    attributes, example, notes.

    Args:
        schema: ClassDocstring Pydantic object

    Returns:
        Formatted string for display
    """
    lines = []
    lines.append(f"Summary: {schema.summary}")
    lines.append("")
    lines.append(f"Extended Description:")
    lines.append(f"    {schema.extended_description}")
    lines.append("")

    if schema.attributes:
        lines.append(f"Attributes:")
        for attr in schema.attributes:
            lines.append(f"  • {attr.name} ({attr.type_hint}): {attr.description}")
    else:
        lines.append(f"Attributes: None")
    lines.append("")

    if schema.example:
        lines.append(f"Example:")
        # Indent code example
        example_lines = schema.example.split('\n')
        for line in example_lines:
            lines.append(f"    {line}")
    else:
        lines.append(f"Example: None")
    lines.append("")

    lines.append(f"Notes: {schema.notes if schema.notes else 'None'}")

    return '\n'.join(lines)


def format_method_docstring_for_review(schema: MethodDocstring) -> str:
    """
    Format MethodDocstring for review display.

    Shows all fields in schema order: summary, extended_description,
    args, returns, raises, example.

    Args:
        schema: MethodDocstring Pydantic object

    Returns:
        Formatted string for display
    """
    lines = []
    lines.append(f"Summary: {schema.summary}")
    lines.append("")

    if schema.extended_description:
        lines.append(f"Extended Description:")
        lines.append(f"    {schema.extended_description}")
    else:
        lines.append(f"Extended Description: None")
    lines.append("")

    if schema.args:
        lines.append(f"Args:")
        for arg in schema.args:
            lines.append(f"  • {arg.name} ({arg.type_hint}): {arg.description}")
    else:
        lines.append(f"Args: None")
    lines.append("")

    if schema.returns:
        lines.append(f"Returns:")
        lines.append(f"  • {schema.returns.type_hint}: {schema.returns.description}")
    else:
        lines.append(f"Returns: None")
    lines.append("")

    if schema.raises:
        lines.append(f"Raises:")
        for exc in schema.raises:
            lines.append(f"  • {exc.exception_type}: {exc.description}")
    else:
        lines.append(f"Raises: None")
    lines.append("")

    if schema.example:
        lines.append(f"Example:")
        # Indent code example
        example_lines = schema.example.split('\n')
        for line in example_lines:
            lines.append(f"    {line}")
    else:
        lines.append(f"Example: None")

    return '\n'.join(lines)


def format_validation_result_for_review(validation: ValidationResult) -> str:
    """
    Format ValidationResult for review display.

    Shows validation status, issues (rationale), suggestions (rationale),
    and improved content. This provides the "why" behind the validation.

    Args:
        validation: ValidationResult Pydantic object

    Returns:
        Formatted string for display
    """
    lines = []

    # Validation status
    status = "Valid" if validation.is_valid else "Invalid"
    lines.append(f"Validation Status: {status}")
    lines.append("")

    # Issues (rationale - what's wrong)
    if validation.issues:
        lines.append(f"Issues Found:")
        for issue in validation.issues:
            lines.append(f"  • {issue}")
    else:
        lines.append(f"Issues Found: None")
    lines.append("")

    # Suggestions (rationale - how to fix)
    if validation.suggestions:
        lines.append(f"Suggestions:")
        for suggestion in validation.suggestions:
            lines.append(f"  • {suggestion}")
    else:
        lines.append(f"Suggestions: None")
    lines.append("")

    # Improved content
    if validation.improved_content:
        lines.append(f"Improved Content:")
        # Don't add extra indentation - improved_content is already properly formatted
        # from the validator with correct indentation and line wrapping
        lines.append(validation.improved_content)
    else:
        lines.append(f"Improved Content: None")

    return '\n'.join(lines)


def format_task_for_review(task) -> str:
    """
    Format a DocTask's suggestion for review display.

    Main entry point that dispatches to appropriate formatter based on
    task_type. Handles JSON parsing back to Pydantic objects.

    Args:
        task: DocTask object with suggestion field

    Returns:
        Formatted string for display
    """
    if not task.suggestion:
        return "(No suggestion available)"

    task_type = task.task_type

    try:
        # Parse JSON suggestions back to Pydantic objects
        if task_type == "generate_module":
            schema = ModuleDocstring.model_validate_json(task.suggestion)
            return format_module_docstring_for_review(schema)

        elif task_type == "generate_class":
            schema = ClassDocstring.model_validate_json(task.suggestion)
            return format_class_docstring_for_review(schema)

        elif task_type == "generate_docstring":
            schema = MethodDocstring.model_validate_json(task.suggestion)
            return format_method_docstring_for_review(schema)

        elif task_type == "generate_comment":
            # Already a plain string
            return f"Comment: {task.suggestion}"

        elif task_type.startswith("validate_"):
            # After Phase 1 fix: suggestion is ValidationResult JSON
            try:
                validation = ValidationResult.model_validate_json(task.suggestion)
                return format_validation_result_for_review(validation)
            except (json.JSONDecodeError, ValueError) as e:
                # Fallback for legacy format (plain strings)
                logger.warning(f"Legacy validate_* format detected for task {task.id}: {e}")
                return f"Improved Content (legacy format):\n{task.suggestion}"

        else:
            logger.warning(f"Unknown task type: {task_type}")
            return task.suggestion

    except (json.JSONDecodeError, ValueError) as e:
        error_msg = f"(Error parsing suggestion: {e})"
        logger.error(f"Failed to parse suggestion for task {task.id}: {e}")
        return error_msg