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
from llm_doc_manager.utils.text_normalizer import add_indent


def format_module_docstring(schema: ModuleDocstring, indent: str = "") -> str:
    """
    Convert ModuleDocstring schema to Google Style docstring.

    Args:
        schema: Structured module documentation
        indent: Base indentation to apply to all lines

    Returns:
        str: Formatted docstring with quotes and indentation
    """
    lines = []

    # Opening quote
    lines.append(f'{indent}"""')

    # Summary (required)
    lines.extend(add_indent(schema.summary, indent))
    lines.append('')

    # Extended description (required)
    lines.extend(add_indent(schema.extended_description, indent))

    # Typical usage (optional)
    if schema.typical_usage:
        lines.append('')
        lines.append(f'{indent}Typical usage example:')
        # Indent code example with 4 spaces
        for line in schema.typical_usage.strip().split("\n"):
            lines.append(f'{indent}    {line}')

    # Notes (optional)
    if schema.notes:
        lines.append('')
        lines.append(f'{indent}Note:')
        # Indent notes with 4 spaces
        for line in schema.notes.strip().split("\n"):
            lines.append(f'{indent}    {line}')

    # Closing quote
    lines.append(f'{indent}"""')

    return "\n".join(lines)


def format_class_docstring(schema: ClassDocstring, indent: str = "") -> str:
    """
    Convert ClassDocstring schema to Google Style docstring.

    Args:
        schema: Structured class documentation
        indent: Base indentation to apply to all lines

    Returns:
        str: Formatted docstring with quotes and indentation
    """
    lines = []

    # Opening quote
    lines.append(f'{indent}"""')

    # Summary (required)
    lines.extend(add_indent(schema.summary, indent))
    lines.append('')

    # Extended description (required)
    lines.extend(add_indent(schema.extended_description, indent))

    # Attributes (optional, but common)
    if schema.attributes:
        lines.append('')
        lines.append(f'{indent}Attributes:')
        for attr in schema.attributes:
            lines.append(
                f'{indent}    {attr.name} ({attr.type_hint}): {attr.description}'
            )

    # Example (optional)
    if schema.example:
        lines.append('')
        lines.append(f'{indent}Example:')
        for line in schema.example.strip().split("\n"):
            lines.append(f'{indent}    {line}')

    # Notes (optional)
    if schema.notes:
        lines.append('')
        lines.append(f'{indent}Note:')
        for line in schema.notes.strip().split("\n"):
            lines.append(f'{indent}    {line}')

    # Closing quote
    lines.append(f'{indent}"""')

    return "\n".join(lines)


def format_method_docstring(schema: MethodDocstring, indent: str = "") -> str:
    """
    Convert MethodDocstring schema to Google Style docstring.

    Args:
        schema: Structured method/function documentation
        indent: Base indentation to apply to all lines

    Returns:
        str: Formatted docstring with quotes and indentation
    """
    lines = []

    # Opening quote
    lines.append(f'{indent}"""')

    # Summary (required)
    lines.extend(add_indent(schema.summary, indent))

    # Extended description (optional)
    if schema.extended_description:
        lines.append('')
        lines.extend(add_indent(schema.extended_description, indent))

    # Args (optional, but very common)
    if schema.args:
        lines.append('')
        lines.append(f'{indent}Args:')
        for arg in schema.args:
            lines.append(
                f'{indent}    {arg.name} ({arg.type_hint}): {arg.description}'
            )

    # Returns (optional)
    if schema.returns:
        lines.append('')
        lines.append(f'{indent}Returns:')
        lines.append(
            f'{indent}    {schema.returns.type_hint}: {schema.returns.description}'
        )

    # Raises (optional)
    if schema.raises:
        lines.append('')
        lines.append(f'{indent}Raises:')
        for exc in schema.raises:
            lines.append(
                f'{indent}    {exc.exception_type}: {exc.description}'
            )

    # Example (optional)
    if schema.example:
        lines.append('')
        lines.append(f'{indent}Example:')
        for line in schema.example.strip().split("\n"):
            lines.append(f'{indent}    {line}')

    # Closing quote
    lines.append(f'{indent}"""')

    return "\n".join(lines)