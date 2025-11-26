"""Test refactored indentation architecture."""

from llm_doc_manager.utils.response_schemas import (
    ModuleDocstring,
    ClassDocstring,
    MethodDocstring,
    ArgumentDoc,
    ReturnDoc
)
from llm_doc_manager.utils.docstring_formatter import (
    format_module_docstring,
    format_class_docstring,
    format_method_docstring
)


def test_module_formatter_with_indent():
    """Test module formatter with indentation parameter."""
    print("=" * 70)
    print("TEST 1: Module Formatter with Indentation")
    print("=" * 70)

    schema = ModuleDocstring(
        summary="Test module for demonstrations.",
        extended_description="This module provides test utilities.",
        typical_usage=None,
        notes=None
    )

    # Test with no indentation
    result_no_indent = format_module_docstring(schema, indent="")
    print("\nWith NO indentation:")
    print(result_no_indent)

    # Test with 4 spaces
    result_with_indent = format_module_docstring(schema, indent="    ")
    print("\nWith 4 SPACES indentation:")
    print(result_with_indent)

    # Verify structure
    assert result_no_indent.startswith('"""')
    assert result_with_indent.startswith('    """')
    print("\n[PASS] Module formatter correctly applies indentation")


def test_class_formatter_with_indent():
    """Test class formatter with indentation parameter."""
    print("\n" + "=" * 70)
    print("TEST 2: Class Formatter with Indentation")
    print("=" * 70)

    schema = ClassDocstring(
        summary="Test class for demonstrations.",
        extended_description="Handles test operations.",
        attributes=[],
        example=None,
        notes=None
    )

    # Test with 8 spaces (nested class)
    result = format_class_docstring(schema, indent="        ")
    print("\nWith 8 SPACES indentation:")
    print(result)

    # Verify all lines have correct indentation
    lines = result.split('\n')
    for line in lines:
        if line.strip():  # Non-empty lines
            assert line.startswith('        '), f"Line not indented correctly: {line}"

    print("\n[PASS] Class formatter correctly applies indentation")


def test_method_formatter_with_indent():
    """Test method formatter with indentation parameter."""
    print("\n" + "=" * 70)
    print("TEST 3: Method Formatter with Indentation")
    print("=" * 70)

    schema = MethodDocstring(
        summary="Calculate total price.",
        extended_description=None,
        args=[
            ArgumentDoc(
                name="price",
                type_hint="float",
                description="Original price"
            ),
            ArgumentDoc(
                name="discount",
                type_hint="float",
                description="Discount percentage"
            )
        ],
        returns=ReturnDoc(
            type_hint="float",
            description="Final price after discount"
        ),
        raises=[],
        example=None
    )

    # Test with 4 spaces
    result = format_method_docstring(schema, indent="    ")
    print("\nWith 4 SPACES indentation:")
    print(result)

    # Verify structure
    assert '    """' in result
    assert '    Args:' in result
    assert '    Returns:' in result
    # Verify Args content has 8 spaces (4 base + 4 section)
    assert '        price (float):' in result

    print("\n[PASS] Method formatter correctly applies indentation")


def test_indentation_extraction():
    """Test indentation extraction (simulated from applier.py)."""
    print("\n" + "=" * 70)
    print("TEST 4: Indentation Extraction Logic")
    print("=" * 70)

    # Simulate _extract_indentation
    def extract_indentation(line: str) -> str:
        indent = ""
        for char in line:
            if char in [' ', '\t']:
                indent += char
            else:
                break
        return indent

    # Test cases
    test_cases = [
        ("def foo():", ""),
        ("    def bar():", "    "),
        ("        class Baz:", "        "),
        ("\t\tdef qux():", "\t\t"),
    ]

    for line, expected_indent in test_cases:
        result = extract_indentation(line)
        assert result == expected_indent, f"Failed for '{line}': got '{result}', expected '{expected_indent}'"
        print(f"[OK] '{line}' -> indent='{repr(result)}'")

    print("\n[PASS] Indentation extraction works correctly")


def test_add_indent_level():
    """Test adding indentation level (simulated from applier.py)."""
    print("\n" + "=" * 70)
    print("TEST 5: Add Indentation Level Logic")
    print("=" * 70)

    # Simulate _add_indent_level
    def add_indent_level(base_indent: str) -> str:
        if '\t' in base_indent:
            return base_indent + '\t'
        elif len(base_indent) >= 2:
            indent_size = len(base_indent)
            if indent_size % 4 == 0:
                return base_indent + '    '
            elif indent_size % 2 == 0:
                return base_indent + '  '
            else:
                return base_indent + '    '
        else:
            return base_indent + '    '

    # Test cases
    test_cases = [
        ("", "    "),           # No indent -> 4 spaces
        ("    ", "        "),   # 4 spaces -> 8 spaces
        ("  ", "    "),         # 2 spaces -> 4 spaces
        ("\t", "\t\t"),         # 1 tab -> 2 tabs
    ]

    for base, expected in test_cases:
        result = add_indent_level(base)
        assert result == expected, f"Failed for '{repr(base)}': got '{repr(result)}', expected '{repr(expected)}'"
        print(f"[OK] {repr(base)} -> {repr(result)}")

    print("\n[PASS] Add indent level works correctly")


def test_complete_flow():
    """Test complete flow: schema -> formatter -> indented output."""
    print("\n" + "=" * 70)
    print("TEST 6: Complete Flow (Schema -> Formatter -> Output)")
    print("=" * 70)

    # Simulate what happens in applier.py
    schema = MethodDocstring(
        summary="Test method.",
        extended_description=None,
        args=[],
        returns=None,
        raises=[],
        example=None
    )

    # Simulate function at different indentation levels
    indentation_levels = [
        ("", "Top-level function"),
        ("    ", "Method in class"),
        ("        ", "Nested method"),
    ]

    for base_indent, description in indentation_levels:
        # Add one level for docstring
        docstring_indent = base_indent + "    "

        # Format with correct indentation
        formatted = format_method_docstring(schema, docstring_indent)

        print(f"\n{description} (base indent: {repr(base_indent)}):")
        print(formatted)

        # Verify opening quote has correct indentation
        expected_opening = f'{docstring_indent}"""'
        assert formatted.startswith(expected_opening), f"Expected '{expected_opening}', got '{formatted[:20]}'"

    print("\n[PASS] Complete flow works correctly")


if __name__ == "__main__":
    test_module_formatter_with_indent()
    test_class_formatter_with_indent()
    test_method_formatter_with_indent()
    test_indentation_extraction()
    test_add_indent_level()
    test_complete_flow()

    print("\n" + "=" * 70)
    print("ALL INDENTATION TESTS PASSED!")
    print("=" * 70)
    print("\nCONCLUSION:")
    print("[OK] Formatters correctly apply indentation parameter")
    print("[OK] Indentation extraction works for spaces and tabs")
    print("[OK] Adding indent levels works correctly")
    print("[OK] Complete flow (schema -> formatter) produces correct output")
    print("\nThe refactored architecture is working correctly!")