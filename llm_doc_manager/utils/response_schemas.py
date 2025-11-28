"""
Response schema definitions.

Pydantic schemas for OpenAI Structured Outputs that mirror Google Style
Guide docstring structure. These schemas enforce consistent JSON responses
from LLMs for documentation generation and validation tasks.
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator

from llm_doc_manager.utils.text_normalizer import (
    wrap_and_normalize,
    wrap_list_items,
    clean_comment_prefix,
)


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
        return wrap_and_normalize(v)


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
        return wrap_and_normalize(v)


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
        return wrap_and_normalize(v)


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
        return wrap_and_normalize(v)


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

    @field_validator('summary', 'extended_description', 'notes', 'typical_usage')
    @classmethod
    def wrap_long_lines(cls, v: Optional[str]) -> Optional[str]:
        """Wrap lines at 79 characters with normalized indentation."""
        if v is None:
            return v
        return wrap_and_normalize(v)


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

    @field_validator('summary', 'extended_description', 'notes', 'example')
    @classmethod
    def wrap_long_lines(cls, v: Optional[str]) -> Optional[str]:
        """Wrap lines at 79 characters with normalized indentation."""
        if v is None:
            return v
        return wrap_and_normalize(v)


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

    @field_validator('summary', 'extended_description', 'example')
    @classmethod
    def wrap_long_lines(cls, v: Optional[str]) -> Optional[str]:
        """Wrap lines at 79 characters with normalized indentation."""
        if v is None:
            return v
        return wrap_and_normalize(v)


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
        """Clean and wrap comment at 79 characters with normalized indentation."""
        # Remove # prefix if LLM included it
        v = clean_comment_prefix(v)
        # Wrap at 79 characters
        return wrap_and_normalize(v)


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
        return wrap_and_normalize(v)

    @field_validator('issues', 'suggestions')
    @classmethod
    def wrap_list_items_validator(cls, v: list[str]) -> list[str]:
        """Wrap each item in list at 79 characters."""
        return wrap_list_items(v)
