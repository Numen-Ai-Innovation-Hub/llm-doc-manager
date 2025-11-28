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
from .text_normalizer import (
    wrap_and_normalize,
    strip_triple_quotes,
    format_bullet_item,
    format_comment_for_review,
)
from .docstring_handler import extract_docstring
from .docstring_formatter import (
    format_module_docstring,
    format_class_docstring,
    format_method_docstring,
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
            bullet_text = f"{attr.name} ({attr.type_hint}): {attr.description}"
            lines.extend(format_bullet_item(bullet_text))
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
            bullet_text = f"{arg.name} ({arg.type_hint}): {arg.description}"
            lines.extend(format_bullet_item(bullet_text))
    else:
        lines.append(f"Args: None")
    lines.append("")

    if schema.returns:
        lines.append(f"Returns:")
        bullet_text = f"{schema.returns.type_hint}: {schema.returns.description}"
        lines.extend(format_bullet_item(bullet_text))
    else:
        lines.append(f"Returns: None")
    lines.append("")

    if schema.raises:
        lines.append(f"Raises:")
        for exc in schema.raises:
            bullet_text = f"{exc.exception_type}: {exc.description}"
            lines.extend(format_bullet_item(bullet_text))
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


def format_validation_result_for_review(
    validation: ValidationResult,
    current_content: Optional[str] = None,
    is_comment: bool = False
) -> str:
    """
    Format ValidationResult for review display.

    Shows validation status, issues (rationale), suggestions (rationale),
    actual content (when validating), and improved content.

    Args:
        validation: ValidationResult Pydantic object
        current_content: Original content being validated (optional)
        is_comment: True if validating a comment (uses # prefix format)

    Returns:
        Formatted string for display
    """
    lines = []

    # Validation status: "Generate" or "Validate"
    status = "Generate" if validation.is_valid else "Validate"
    lines.append(f"Validation Status: {status}")
    lines.append("=" * 60)

    # Issues (rationale - what's wrong)
    if validation.issues:
        lines.append(f"Issues Found:")
        for issue in validation.issues:
            lines.extend(format_bullet_item(issue))
    else:
        lines.append(f"Issues Found: None")
    lines.append("-" * 60)

    # Suggestions (rationale - how to fix)
    if validation.suggestions:
        lines.append(f"Suggestions:")
        for suggestion in validation.suggestions:
            lines.extend(format_bullet_item(suggestion))
    else:
        lines.append(f"Suggestions: None")
    lines.append("-" * 60)

    # Actual Content (only when validating existing documentation)
    if status == "Validate":
        lines.append(f"Actual Content:")

        if is_comment:
            # Format comments with "# " prefix (no triple quotes)
            formatted_comment = format_comment_for_review(current_content)
            lines.append(formatted_comment if formatted_comment else "#")
        else:
            # Format docstrings with triple quotes
            clean_content = strip_triple_quotes(current_content) if current_content else ""
            clean_content = wrap_and_normalize(clean_content)
            lines.append('"""')
            lines.append(clean_content)
            lines.append('"""')

        lines.append("-" * 60)

    # Improved content
    if validation.improved_content:
        lines.append(f"Improved Content:")

        if is_comment:
            # Format comments with "# " prefix (no triple quotes)
            formatted_comment = format_comment_for_review(validation.improved_content)
            lines.append(formatted_comment if formatted_comment else "#")
        else:
            # Format docstrings with triple quotes
            clean_content = strip_triple_quotes(validation.improved_content)
            lines.append('"""')
            lines.append(clean_content)
            lines.append('"""')
    else:
        # Show appropriate empty format based on content type
        lines.append(f"Improved Content:")
        if is_comment:
            lines.append("#")
        else:
            lines.append("None")

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

            lines = []
            lines.append("Validation Status: Generate")
            lines.append("=" * 60)

            # Actual Content - empty for generate
            lines.append("Actual Content:")
            lines.append('"""')
            lines.append('"""')
            lines.append("-" * 60)

            # Improved Content - complete formatted docstring
            lines.append("Improved Content:")
            lines.append('"""')
            formatted = format_module_docstring(schema)
            # Remove the """  from formatted output (formatter adds them)
            clean = strip_triple_quotes(formatted)
            lines.append(clean)
            lines.append('"""')

            return '\n'.join(lines)

        elif task_type == "generate_class":
            schema = ClassDocstring.model_validate_json(task.suggestion)

            lines = []
            lines.append("Validation Status: Generate")
            lines.append("=" * 60)

            lines.append("Actual Content:")
            lines.append('"""')
            lines.append('"""')
            lines.append("-" * 60)

            lines.append("Improved Content:")
            lines.append('"""')
            formatted = format_class_docstring(schema)
            clean = strip_triple_quotes(formatted)
            lines.append(clean)
            lines.append('"""')

            return '\n'.join(lines)

        elif task_type == "generate_docstring":
            schema = MethodDocstring.model_validate_json(task.suggestion)

            lines = []
            lines.append("Validation Status: Generate")
            lines.append("=" * 60)

            lines.append("Actual Content:")
            lines.append('"""')
            lines.append('"""')
            lines.append("-" * 60)

            lines.append("Improved Content:")
            lines.append('"""')
            formatted = format_method_docstring(schema)
            clean = strip_triple_quotes(formatted)
            lines.append(clean)
            lines.append('"""')

            return '\n'.join(lines)

        elif task_type == "generate_comment":
            # Comments are plain text, not JSON
            lines = []
            lines.append("Validation Status: Generate")
            lines.append("=" * 60)

            # Actual Content - empty for generate (show # to indicate empty comment)
            lines.append("Actual Content:")
            lines.append("#")
            lines.append("-" * 60)

            # Improved Content - format with "# " prefix
            lines.append("Improved Content:")
            formatted_comment = format_comment_for_review(task.suggestion)
            lines.append(formatted_comment if formatted_comment else "#")

            return '\n'.join(lines)

        elif task_type.startswith("validate_"):
            # After Phase 1 fix: suggestion is ValidationResult JSON
            try:
                validation = ValidationResult.model_validate_json(task.suggestion)

                # Extract current content from task context
                current_content = extract_docstring(task.context) or ""

                # Determine if this is a comment validation
                is_comment = task_type == "validate_comment"

                return format_validation_result_for_review(
                    validation,
                    current_content,
                    is_comment=is_comment
                )
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