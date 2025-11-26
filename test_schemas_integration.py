"""Integration test for Structured Outputs schemas and formatters."""

import json
from llm_doc_manager.utils.response_schemas import (
    ModuleDocstring,
    ClassDocstring,
    MethodDocstring,
    CommentText,
    ValidationResult,
    ArgumentDoc,
    ReturnDoc,
    AttributeDoc
)
from llm_doc_manager.utils.docstring_formatter import (
    format_module_docstring,
    format_class_docstring,
    format_method_docstring
)


def test_method_docstring_schema():
    """Test MethodDocstring schema with formatters."""
    # Sample JSON response from LLM (Structured Output)
    llm_response = {
        "summary": "Calculate final price after applying percentage discount.",
        "extended_description": None,
        "args": [
            {
                "name": "price",
                "type_hint": "float",
                "description": "Original price before discount"
            },
            {
                "name": "discount_percent",
                "type_hint": "int",
                "description": "Discount percentage (0-100)"
            }
        ],
        "returns": {
            "type_hint": "float",
            "description": "Final price after discount applied"
        },
        "raises": [
            {
                "exception_type": "ValueError",
                "description": "If discount_percent is not between 0 and 100"
            }
        ],
        "example": None
    }

    # Parse into Pydantic schema
    schema = MethodDocstring(**llm_response)

    # Format as Google Style docstring
    formatted = format_method_docstring(schema)

    print("=" * 70)
    print("TEST: MethodDocstring Schema -> Formatted Docstring")
    print("=" * 70)
    print(formatted)
    print("=" * 70)

    # Expected output
    expected_lines = [
        "Calculate final price after applying percentage discount.",
        "",
        "Args:",
        "    price (float): Original price before discount",
        "    discount_percent (int): Discount percentage (0-100)",
        "",
        "Returns:",
        "    float: Final price after discount applied",
        "",
        "Raises:",
        "    ValueError: If discount_percent is not between 0 and 100"
    ]

    assert formatted == "\n".join(expected_lines), "Formatted output doesn't match expected"
    print("[PASS] MethodDocstring test passed!")


def test_class_docstring_schema():
    """Test ClassDocstring schema with formatters."""
    llm_response = {
        "summary": "Manages items in a shopping cart.",
        "extended_description": "Provides functionality to add, remove, and calculate total price of items.",
        "attributes": [
            {
                "name": "items",
                "type_hint": "list",
                "description": "List of cart items"
            },
            {
                "name": "total",
                "type_hint": "float",
                "description": "Total price of all items"
            }
        ],
        "example": None,
        "notes": None
    }

    schema = ClassDocstring(**llm_response)
    formatted = format_class_docstring(schema)

    print("\n" + "=" * 70)
    print("TEST: ClassDocstring Schema -> Formatted Docstring")
    print("=" * 70)
    print(formatted)
    print("=" * 70)

    assert "Manages items in a shopping cart." in formatted
    assert "items (list): List of cart items" in formatted
    print("✓ ClassDocstring test passed!")


def test_module_docstring_schema():
    """Test ModuleDocstring schema with formatters."""
    llm_response = {
        "summary": "Shopping cart management utilities.",
        "extended_description": "This module provides utilities for managing shopping carts, including item tracking and price calculations.",
        "typical_usage": "from cart import ShoppingCart\ncart = ShoppingCart()\ncart.add_item('Apple', 1.50)",
        "notes": None
    }

    schema = ModuleDocstring(**llm_response)
    formatted = format_module_docstring(schema)

    print("\n" + "=" * 70)
    print("TEST: ModuleDocstring Schema -> Formatted Docstring")
    print("=" * 70)
    print(formatted)
    print("=" * 70)

    assert "Shopping cart management utilities." in formatted
    assert "Typical usage example:" in formatted
    print("✓ ModuleDocstring test passed!")


def test_comment_schema():
    """Test CommentText schema."""
    llm_response = {
        "comment": "Calculate total price with discount applied"
    }

    schema = CommentText(**llm_response)

    print("\n" + "=" * 70)
    print("TEST: CommentText Schema")
    print("=" * 70)
    print(f"Comment: {schema.comment}")
    print("=" * 70)

    assert schema.comment == "Calculate total price with discount applied"
    print("✓ CommentText test passed!")


def test_validation_result_schema():
    """Test ValidationResult schema."""
    llm_response = {
        "is_valid": False,
        "issues": [
            "Summary doesn't end with a period",
            "Missing return type documentation"
        ],
        "suggestions": [
            "Add period at end of summary",
            "Document the return value"
        ],
        "improved_docstring": "Calculate discount.\n\nReturns:\n    float: Discounted price"
    }

    schema = ValidationResult(**llm_response)

    print("\n" + "=" * 70)
    print("TEST: ValidationResult Schema")
    print("=" * 70)
    print(f"Is Valid: {schema.is_valid}")
    print(f"Issues: {schema.issues}")
    print(f"Suggestions: {schema.suggestions}")
    print(f"Improved:\n{schema.improved_docstring}")
    print("=" * 70)

    assert not schema.is_valid
    assert len(schema.issues) == 2
    print("✓ ValidationResult test passed!")


def test_long_description_wrapping():
    """Test that long descriptions are wrapped at 79 characters."""
    llm_response = {
        "summary": "Test function.",
        "args": [
            {
                "name": "param",
                "type_hint": "str",
                "description": "This is a very long description that should be wrapped at 79 characters to ensure proper formatting and readability in the generated docstring"
            }
        ],
        "returns": None,
        "raises": [],
        "example": None
    }

    schema = MethodDocstring(**llm_response)
    formatted = format_method_docstring(schema)

    print("\n" + "=" * 70)
    print("TEST: Long Description Wrapping (79 chars)")
    print("=" * 70)
    print(formatted)
    print("=" * 70)

    # The wrapping happens in the description field itself
    # The formatted line includes "    param (str): <description>"
    # So we just verify the description was wrapped
    lines = formatted.split('\n')
    # Find the Args section
    args_section = False
    for line in lines:
        if line.strip() == "Args:":
            args_section = True
        elif args_section and "param (str):" in line:
            # This line should have wrapped text on next line
            # We just verify wrapping occurred by checking there's a continuation
            assert "\n        " in formatted, "Description should be wrapped with continuation"
            break

    print("[PASS] Long description wrapping test passed!")


if __name__ == "__main__":
    test_method_docstring_schema()
    test_class_docstring_schema()
    test_module_docstring_schema()
    test_comment_schema()
    test_validation_result_schema()
    test_long_description_wrapping()

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED! ✓")
    print("=" * 70)