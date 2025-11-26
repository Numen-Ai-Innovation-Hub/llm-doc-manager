"""
Response schema definitions.

Pydantic schemas for OpenAI Structured Outputs that mirror Google Style
Guide docstring structure. These schemas enforce consistent JSON responses
from LLMs for documentation generation and validation tasks.
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Helper functions for line wrapping with indentation normalization
# ============================================================================

def _wrap_single_line(line: str, max_length: int = 79) -> list[str]:
    """
    Wrap a single line at max_length characters preserving its indentation.

    Args:
        line: Single line to wrap
        max_length: Maximum line length (default 79)

    Returns:
        List of wrapped lines with preserved indentation (no extra indentation)
    """
    if len(line) <= max_length:
        return [line]

    # Detect original indentation
    indent = len(line) - len(line.lstrip())
    indent_str = line[:indent]
    content = line[indent:]

    # Wrap content preserving original indentation (no extra indent for continuation)
    words = content.split()
    lines = []
    current_line = []
    current_len = indent

    for word in words:
        word_len = len(word)
        space_len = 1 if current_line else 0
        total_len = current_len + word_len + space_len

        if total_len > max_length and current_line:
            # Line full, start new continuation line with same indentation
            lines.append(indent_str + ' '.join(current_line))
            current_line = [word]
            current_len = indent + word_len
        else:
            current_line.append(word)
            current_len += word_len + space_len

    if current_line:
        lines.append(indent_str + ' '.join(current_line))

    return lines


def _wrap_docstring_preserving_structure(text: str) -> str:
    """
    Wrap docstring content with normalized indentation.

    Removes excessive indentation from continuation lines while preserving
    intentional indentation (Args lists, code examples with 4+ spaces).

    Processes text in three steps:
    1. Detect minimum indentation across all non-empty lines
    2. Normalize (dedent) all lines to remove excessive indentation
    3. Apply wrapping to normalized lines

    This allows LLMs to focus on content while the validator handles formatting.

    Args:
        text: Complete docstring content (may be multi-line)

    Returns:
        Wrapped docstring with normalized indentation and all lines <= 79 chars
    """
    if not text:
        return text

    lines = text.split('\n')

    # Step 1: Detect minimum indentation (excluding empty lines)
    min_indent = float('inf')
    for line in lines:
        if line.strip():  # Non-empty line
            indent = len(line) - len(line.lstrip())
            min_indent = min(min_indent, indent)

    # If all lines are empty or min_indent is still inf, no normalization needed
    if min_indent == float('inf'):
        min_indent = 0

    # Step 2: Normalize indentation - remove min_indent from all lines
    normalized_lines = []
    for line in lines:
        if not line.strip():
            # Empty line - keep as-is
            normalized_lines.append(line)
        else:
            # Remove min_indent spaces from the beginning
            dedented = line[min_indent:] if len(line) > min_indent else line.lstrip()
            normalized_lines.append(dedented)

    # Step 3: Apply wrapping to normalized lines
    result = []
    for line in normalized_lines:
        if not line or len(line) <= 79:
            result.append(line)
        else:
            wrapped_lines = _wrap_single_line(line, max_length=79)
            result.extend(wrapped_lines)

    return '\n'.join(result)


# ============================================================================
# Auxiliary schemas (reusable components)
# ============================================================================

class ArgumentDoc(BaseModel):
    """Single argument documentation following Google Style."""
    name: str = Field(..., description="Parameter name")
    type_hint: str = Field(
        ...,
        description="Type annotation (e.g., 'str', 'int', 'List[str]')"
    )
    description: str = Field(
        ...,
        description="Brief description of the parameter"
    )

    @field_validator('description')
    @classmethod
    def wrap_long_lines(cls, v: str) -> str:
        """Wrap lines at 79 characters with normalized indentation."""
        return _wrap_docstring_preserving_structure(v)


class ReturnDoc(BaseModel):
    """Return value documentation following Google Style."""
    type_hint: str = Field(..., description="Return type annotation")
    description: str = Field(
        ...,
        description="Description of what is returned"
    )

    @field_validator('description')
    @classmethod
    def wrap_long_lines(cls, v: str) -> str:
        """Wrap lines at 79 characters with normalized indentation."""
        return _wrap_docstring_preserving_structure(v)


class RaisesDoc(BaseModel):
    """Exception documentation following Google Style."""
    exception_type: str = Field(
        ...,
        description="Exception class name (e.g., 'ValueError')"
    )
    description: str = Field(
        ...,
        description="When/why this exception is raised"
    )

    @field_validator('description')
    @classmethod
    def wrap_long_lines(cls, v: str) -> str:
        """Wrap lines at 79 characters with normalized indentation."""
        return _wrap_docstring_preserving_structure(v)


class AttributeDoc(BaseModel):
    """Class attribute documentation following Google Style."""
    name: str = Field(..., description="Attribute name")
    type_hint: str = Field(..., description="Type annotation")
    description: str = Field(
        ...,
        description="Brief description of the attribute"
    )

    @field_validator('description')
    @classmethod
    def wrap_long_lines(cls, v: str) -> str:
        """Wrap lines at 79 characters with normalized indentation."""
        return _wrap_docstring_preserving_structure(v)


# ============================================================================
# Main schemas (for each documentation type)
# ============================================================================

class ModuleDocstring(BaseModel):
    """
    Structured schema for MODULE docstrings following Google Style.

    Google Style format:
    - Brief one-line summary
    - Extended description (2-4 sentences)
    - Typical usage example (optional)
    """
    summary: str = Field(
        ...,
        description="One-line summary ending with period, present tense"
    )
    extended_description: str = Field(
        ...,
        description=(
            "2-4 sentences explaining what module provides, "
            "key components, when to use"
        )
    )
    typical_usage: Optional[str] = Field(
        None,
        description="Code example showing typical usage (if applicable)"
    )
    notes: Optional[str] = Field(
        None,
        description=(
            "Important notes about dependencies or limitations (if needed)"
        )
    )

    @field_validator('summary', 'extended_description', 'notes')
    @classmethod
    def wrap_long_lines(cls, v: Optional[str]) -> Optional[str]:
        """Wrap lines at 79 characters with normalized indentation."""
        if v is None:
            return v
        return _wrap_docstring_preserving_structure(v)


class ClassDocstring(BaseModel):
    """
    Structured schema for CLASS docstrings following Google Style.

    Google Style format:
    - Brief one-line summary
    - Extended description (2-3 sentences)
    - Attributes section
    - Example (if non-obvious)
    """
    summary: str = Field(
        ...,
        description="One-line summary ending with period, present tense"
    )
    extended_description: str = Field(
        ...,
        description=(
            "2-3 sentences explaining what the class does "
            "and its main responsibility"
        )
    )
    attributes: list[AttributeDoc] = Field(
        default_factory=list,
        description="List of public attributes (not private _attributes)"
    )
    example: Optional[str] = Field(
        None,
        description="Usage example (only if usage is non-obvious)"
    )
    notes: Optional[str] = Field(
        None,
        description="Important usage notes or limitations (if critical)"
    )

    @field_validator('summary', 'extended_description', 'notes')
    @classmethod
    def wrap_long_lines(cls, v: Optional[str]) -> Optional[str]:
        """Wrap lines at 79 characters with normalized indentation."""
        if v is None:
            return v
        return _wrap_docstring_preserving_structure(v)


class MethodDocstring(BaseModel):
    """
    Structured schema for METHOD/FUNCTION docstrings following Google Style.

    Google Style format:
    - Brief one-line summary
    - Extended description (optional)
    - Args section
    - Returns section
    - Raises section
    - Example (optional)
    """
    summary: str = Field(
        ...,
        description="One-line summary ending with period, present tense"
    )
    extended_description: Optional[str] = Field(
        None,
        description="Extended description (only if summary is insufficient)"
    )
    args: list[ArgumentDoc] = Field(
        default_factory=list,
        description=(
            "List of all function parameters with types and descriptions"
        )
    )
    returns: Optional[ReturnDoc] = Field(
        None,
        description=(
            "Return value type and description "
            "(None if function returns None)"
        )
    )
    raises: list[RaisesDoc] = Field(
        default_factory=list,
        description="List of exceptions that can be raised"
    )
    example: Optional[str] = Field(
        None,
        description=(
            "Usage example (only if it significantly aids understanding)"
        )
    )

    @field_validator('summary', 'extended_description')
    @classmethod
    def wrap_long_lines(cls, v: Optional[str]) -> Optional[str]:
        """Wrap lines at 79 characters with normalized indentation."""
        if v is None:
            return v
        return _wrap_docstring_preserving_structure(v)


class CommentText(BaseModel):
    """
    Schema for inline COMMENT generation.

    Simple single-line comment explaining WHAT the code does.
    """
    comment: str = Field(
        ...,
        description=(
            "Single-line comment (under 79 chars) "
            "explaining what the code does"
        )
    )

    @field_validator('comment')
    @classmethod
    def wrap_long_lines(cls, v: str) -> str:
        """Wrap lines at 79 characters with normalized indentation."""
        return _wrap_docstring_preserving_structure(v)


# ============================================================================
# Validation schemas (for validate_* tasks)
# ============================================================================

class ValidationResult(BaseModel):
    """
    Schema for validation responses.

    Used for validate_module, validate_class, validate_docstring,
    validate_comment tasks.
    """
    is_valid: bool = Field(
        ...,
        description="Whether current documentation passes validation"
    )
    issues: list[str] = Field(
        default_factory=list,
        description=(
            "Specific issues found "
            "(verbosity, missing info, inaccuracies)"
        )
    )
    suggestions: list[str] = Field(
        default_factory=list,
        description="Specific actionable improvements"
    )
    improved_content: Optional[str] = Field(
        None,
        description=(
            "The complete improved content as formatted string "
            "(docstring or comment, if improvements needed)"
        )
    )

    @field_validator('improved_content')
    @classmethod
    def wrap_long_lines(cls, v: Optional[str]) -> Optional[str]:
        """
        Wrap docstring preserving multi-line structure.

        Uses intelligent line-by-line wrapping that:
        - Preserves multi-line structure (Args, Returns, etc. sections)
        - Normalizes indentation (removes excessive indentation from continuation lines)
        - Preserves blank lines
        - Preserves intentional indentation (4+ spaces for code blocks, Args lists)

        This allows LLMs to focus on content while validator ensures 79-char limit.
        """
        if v is None:
            return v
        return _wrap_docstring_preserving_structure(v)
