"""
Docstring formatter utilities.

Converts structured Pydantic schemas into properly formatted
Google Style docstrings.
"""

from llm_doc_manager.utils.response_schemas import (
    ModuleDocstring,
    ClassDocstring,
    MethodDocstring,
)


def format_module_docstring(schema: ModuleDocstring) -> str:
    """
    Convert ModuleDocstring schema to Google Style docstring.

    Args:
        schema: Structured module documentation

    Returns:
        str: Formatted docstring ready to inject in file
    """
    lines = []

    # Summary (required)
    lines.append(schema.summary)
    lines.append("")

    # Extended description (required)
    lines.append(schema.extended_description)

    # Typical usage (optional)
    if schema.typical_usage:
        lines.append("")
        lines.append("Typical usage example:")
        # Indent code example with 4 spaces
        for line in schema.typical_usage.strip().split("\n"):
            lines.append(f"    {line}")

    # Notes (optional)
    if schema.notes:
        lines.append("")
        lines.append("Note:")
        # Indent notes with 4 spaces
        for line in schema.notes.strip().split("\n"):
            lines.append(f"    {line}")

    return "\n".join(lines)


def format_class_docstring(schema: ClassDocstring) -> str:
    """
    Convert ClassDocstring schema to Google Style docstring.

    Args:
        schema: Structured class documentation

    Returns:
        str: Formatted docstring ready to inject in file
    """
    lines = []

    # Summary (required)
    lines.append(schema.summary)
    lines.append("")

    # Extended description (required)
    lines.append(schema.extended_description)

    # Attributes (optional, but common)
    if schema.attributes:
        lines.append("")
        lines.append("Attributes:")
        for attr in schema.attributes:
            lines.append(
                f"    {attr.name} ({attr.type_hint}): {attr.description}"
            )

    # Example (optional)
    if schema.example:
        lines.append("")
        lines.append("Example:")
        for line in schema.example.strip().split("\n"):
            lines.append(f"    {line}")

    # Notes (optional)
    if schema.notes:
        lines.append("")
        lines.append("Note:")
        for line in schema.notes.strip().split("\n"):
            lines.append(f"    {line}")

    return "\n".join(lines)


def format_method_docstring(schema: MethodDocstring) -> str:
    """
    Convert MethodDocstring schema to Google Style docstring.

    Args:
        schema: Structured method/function documentation

    Returns:
        str: Formatted docstring ready to inject in file
    """
    lines = []

    # Summary (required)
    lines.append(schema.summary)

    # Extended description (optional)
    if schema.extended_description:
        lines.append("")
        lines.append(schema.extended_description)

    # Args (optional, but very common)
    if schema.args:
        lines.append("")
        lines.append("Args:")
        for arg in schema.args:
            lines.append(
                f"    {arg.name} ({arg.type_hint}): {arg.description}"
            )

    # Returns (optional)
    if schema.returns:
        lines.append("")
        lines.append("Returns:")
        lines.append(
            f"    {schema.returns.type_hint}: {schema.returns.description}"
        )

    # Raises (optional)
    if schema.raises:
        lines.append("")
        lines.append("Raises:")
        for exc in schema.raises:
            lines.append(
                f"    {exc.exception_type}: {exc.description}"
            )

    # Example (optional)
    if schema.example:
        lines.append("")
        lines.append("Example:")
        for line in schema.example.strip().split("\n"):
            lines.append(f"    {line}")

    return "\n".join(lines)