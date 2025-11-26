"""
Response schema definitions.

Pydantic schemas for OpenAI Structured Outputs that mirror Google Style
Guide docstring structure. These schemas enforce consistent JSON responses
from LLMs for documentation generation and validation tasks.
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Helper function for line wrapping
# ============================================================================

def _wrap_text_at_79_chars(text: str) -> str:
    """
    Break text at 79 characters by splitting on whitespace.

    Preserves all words, only adds line breaks at spaces.
    Indents continuation lines with 8 spaces (for Google Style).

    Args:
        text: Text to wrap

    Returns:
        str: Text with lines wrapped at 79 characters
    """
    if len(text) <= 79:
        return text

    words = text.split()
    lines = []
    current_line = []
    current_len = 0

    for word in words:
        word_len = len(word)
        space_len = 1 if current_line else 0

        if current_len + word_len + space_len > 79:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
            current_len = word_len
        else:
            current_line.append(word)
            current_len += word_len + space_len

    if current_line:
        lines.append(' '.join(current_line))

    return '\n        '.join(lines)  # 8 spaces for continuation


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
        """Break lines at 79 characters by splitting on whitespace."""
        return _wrap_text_at_79_chars(v)


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
        """Break lines at 79 characters by splitting on whitespace."""
        return _wrap_text_at_79_chars(v)


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
        """Break lines at 79 characters by splitting on whitespace."""
        return _wrap_text_at_79_chars(v)


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
        """Break lines at 79 characters by splitting on whitespace."""
        return _wrap_text_at_79_chars(v)


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
        """Break lines at 79 characters by splitting on whitespace."""
        if v is None:
            return v
        return _wrap_text_at_79_chars(v)


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
        """Break lines at 79 characters by splitting on whitespace."""
        if v is None:
            return v
        return _wrap_text_at_79_chars(v)


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
        """Break lines at 79 characters by splitting on whitespace."""
        if v is None:
            return v
        return _wrap_text_at_79_chars(v)


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
        """Break lines at 79 characters by splitting on whitespace."""
        return _wrap_text_at_79_chars(v)


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
        """Break lines at 79 characters by splitting on whitespace."""
        if v is None:
            return v
        return _wrap_text_at_79_chars(v)