# Indentation Architecture

## Overview

This document describes the refactored indentation and formatting architecture implemented in llm_doc_manager. The architecture leverages OpenAI Structured Outputs to provide precise, single-pass formatting of documentation.

## Core Philosophy

**Format Once, Format Right**: With Structured Outputs providing complete control over LLM responses, we format docstrings exactly once with full precision, eliminating redundant formatting layers.

## Architecture Layers

### 1. LLM Layer (OpenAI API)
- **Input**: Structured prompts with JSON schema
- **Output**: Valid JSON matching Pydantic schemas
- **Guarantee**: 100% schema compliance via Structured Outputs

### 2. Processor Layer (`processor.py`)
- **Input**: JSON response from LLM
- **Output**:
  - For `generate_*` tasks: Pydantic schema objects (ModuleDocstring, ClassDocstring, MethodDocstring)
  - For `validate_*` tasks: Pre-formatted strings (for backwards compatibility)
  - For `generate_comment`: Plain strings
- **Responsibility**: Parse and validate JSON, return appropriate type

### 3. Formatter Layer (`docstring_formatter.py`)
- **Input**: Pydantic schema object + indentation string
- **Output**: Complete, indented docstring with triple quotes
- **Responsibility**: Convert schema to Google Style format with exact indentation

#### Formatters

##### `format_module_docstring(schema: ModuleDocstring, indent: str = "") -> str`
Formats module-level docstrings.

**Structure**:
```python
"""Summary line.

Extended description.

Typical Usage:
    Example code here.

Notes:
    Additional notes.
"""
```

##### `format_class_docstring(schema: ClassDocstring, indent: str = "") -> str`
Formats class docstrings.

**Structure**:
```python
    """Summary line.

    Extended description.

    Attributes:
        attr_name (type): Description.

    Example:
        Usage example.
    """
```

##### `format_method_docstring(schema: MethodDocstring, indent: str = "") -> str`
Formats method/function docstrings.

**Structure**:
```python
    """Summary line.

    Extended description.

    Args:
        param (type): Description.

    Returns:
        type: Description.

    Raises:
        ExceptionType: Description.
    """
```

### 4. Applier Layer (`applier.py`)
- **Input**: File content, marker metadata, Pydantic object or string
- **Output**: Modified file content with injected documentation
- **Responsibility**:
  - Detect indentation from source code
  - Calculate correct indentation level
  - Call appropriate formatter
  - Inject formatted documentation

## Indentation Detection and Calculation

### Helper Methods

#### `_extract_indentation(line: str) -> str`
Extracts leading whitespace from a line.

**Algorithm**:
```python
indent = ""
for char in line:
    if char in [' ', '\t']:
        indent += char
    else:
        break
return indent
```

**Examples**:
- `"def foo():"` → `""`
- `"    def bar():"` → `"    "`
- `"\t\tclass Baz:"` → `"\t\t"`

#### `_add_indent_level(base_indent: str) -> str`
Adds one indentation level to base indent.

**Algorithm**:
1. If tabs detected → add one tab
2. If 4-space indent → add 4 spaces
3. If 2-space indent → add 2 spaces
4. Default → add 4 spaces

**Examples**:
- `""` → `"    "` (default 4 spaces)
- `"    "` → `"        "` (4-space project)
- `"  "` → `"    "` (2-space project)
- `"\t"` → `"\t\t"` (tab-based project)

## Indentation Rules by Marker Type

### @llm-doc (Function/Method Docstrings)

**Rule**: Docstring indent = function indent + 1 level

**Example**:
```python
# @llm-doc-start
def foo():
    """Docstring here."""
    pass
# @llm-doc-end
```

**Process**:
1. Extract function indent: `""` (top-level)
2. Add one level: `"    "`
3. Format with indent: `format_method_docstring(schema, "    ")`

### @llm-class (Class Docstrings)

**Rule**: Docstring indent = class indent + 1 level

**Example**:
```python
# @llm-class-start
class MyClass:
    """Class docstring here."""
    pass
# @llm-class-end
```

**Process**:
1. Extract class indent: `""` (top-level)
2. Add one level: `"    "`
3. Format with indent: `format_class_docstring(schema, "    ")`

### @llm-comm (Code Comments)

**Rule**: Comment indent = code indent (NO level addition)

**Example**:
```python
# @llm-comm-start
    # This comment aligns with the code
    result = calculate()
# @llm-comm-end
```

**Process**:
1. Extract code indent: `"    "`
2. NO level addition
3. Format: `f"{code_indent}# {comment_text}"`

### @llm-module (Module Docstrings)

**Rule**: Use marker indent (usually none for top-level)

**Example**:
```python
# @llm-module-start
"""Module docstring at file top."""

import sys
# @llm-module-end
```

**Process**:
1. Use marker indent: `""` (top-level)
2. NO level addition
3. Format with indent: `format_module_docstring(schema, "")`

## Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. USER REQUEST                                                 │
│    "Generate docstring for function at line 42"                 │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. PROCESSOR: Create Task                                       │
│    task_type = "generate_docstring"                             │
│    context = function code + signature                          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. LLM: Generate Structured Response                            │
│    Input: Prompt + MethodDocstring JSON schema                  │
│    Output: Valid JSON matching schema                           │
│    {                                                             │
│      "summary": "Calculate total price.",                       │
│      "args": [{"name": "price", "type_hint": "float", ...}],    │
│      "returns": {"type_hint": "float", ...}                     │
│    }                                                             │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. PROCESSOR: Parse Response                                    │
│    parsed = json.loads(response)                                │
│    schema = MethodDocstring(**parsed)                           │
│    return schema  # Return Pydantic object                      │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. APPLIER: Detect Indentation                                  │
│    func_line = "    def calculate_price(...):"                  │
│    func_indent = _extract_indentation(func_line)  # "    "      │
│    docstring_indent = _add_indent_level(func_indent)  # "        "│
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. APPLIER: Detect Type and Format                              │
│    if isinstance(schema, MethodDocstring):                      │
│        formatted = format_method_docstring(schema, "        ")  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 7. FORMATTER: Generate Complete Docstring                       │
│    """Calculate total price.                                    │
│                                                                  │
│    Args:                                                         │
│        price (float): Original price.                           │
│                                                                  │
│    Returns:                                                      │
│        float: Final price after discount.                       │
│    """                                                           │
│    (All lines have "        " indentation)                      │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 8. APPLIER: Inject into Source File                             │
│    - Find docstring location after function definition          │
│    - Replace or insert formatted docstring                      │
│    - Return modified file content                               │
└─────────────────────────────────────────────────────────────────┘
```

## Type Detection and Routing

The applier uses runtime type detection to route to the correct formatter:

```python
def _replace_docstring(self, ..., suggested_text: Union[ModuleDocstring, ClassDocstring, MethodDocstring, str], ...):
    # Extract indentation
    func_indent = self._extract_indentation(lines[func_line_idx])
    docstring_indent = self._add_indent_level(func_indent)

    # Route based on type
    if isinstance(suggested_text, ModuleDocstring):
        formatted_docstring = format_module_docstring(suggested_text, docstring_indent)
    elif isinstance(suggested_text, ClassDocstring):
        formatted_docstring = format_class_docstring(suggested_text, docstring_indent)
    elif isinstance(suggested_text, MethodDocstring):
        formatted_docstring = format_method_docstring(suggested_text, docstring_indent)
    elif isinstance(suggested_text, str):
        # Backwards compatibility for validate_* tasks
        formatted_docstring = self._format_docstring(suggested_text, docstring_indent)
    else:
        raise ValueError(f"Unexpected type: {type(suggested_text)}")
```

## Benefits of This Architecture

### 1. Single Responsibility
Each layer has ONE clear job:
- **Processor**: Parse JSON → Pydantic objects
- **Formatter**: Schema → formatted text
- **Applier**: Indentation detection + injection

### 2. No Redundancy
- Formatting happens ONCE in formatter layer
- No re-parsing of formatted text
- No heuristic detection when we have structured data

### 3. Type Safety
- Union types with runtime checking
- Pydantic validation at parse time
- Impossible to inject malformed docstrings

### 4. Consistent Indentation
- Unified extraction logic for all markers
- Project-aware indentation (detects tabs/2-space/4-space)
- Correct nesting for all scenarios

### 5. Testability
- Each layer can be tested independently
- Formatters are pure functions (schema + indent → text)
- Easy to verify indentation correctness

## Testing

### Test File: `test_refactored_indentation.py`

Validates:
1. ✅ Module formatter with indentation parameter
2. ✅ Class formatter with indentation parameter
3. ✅ Method formatter with indentation parameter
4. ✅ Indentation extraction for spaces and tabs
5. ✅ Adding indent levels (2-space, 4-space, tab detection)
6. ✅ Complete flow from schema → formatter → indented output

### Running Tests

```bash
python test_refactored_indentation.py
```

Expected output:
```
======================================================================
ALL INDENTATION TESTS PASSED!
======================================================================

CONCLUSION:
[OK] Formatters correctly apply indentation parameter
[OK] Indentation extraction works for spaces and tabs
[OK] Adding indent levels works correctly
[OK] Complete flow (schema -> formatter) produces correct output

The refactored architecture is working correctly!
```

## Edge Cases Handled

### 1. Nested Classes/Functions
```python
class Outer:
    class Inner:
        def method(self):
            """Correctly indented at 12 spaces (3 levels)."""
            pass
```

**Process**:
- Extract `method` indent: `"        "` (8 spaces)
- Add one level: `"            "` (12 spaces)

### 2. Mixed Tabs and Spaces
```python
\t\tdef foo():
\t\t    """Docstring with tabs + spaces."""
```

**Process**:
- Extract function indent: `"\t\t"`
- Tab detected → add one tab: `"\t\t\t"`

### 3. Top-Level Functions
```python
def foo():
    """Correctly indented at 4 spaces (1 level)."""
    pass
```

**Process**:
- Extract function indent: `""` (no indent)
- Add one level: `"    "` (default 4 spaces)

### 4. Already Formatted Strings (validate_* tasks)
For backwards compatibility, `validate_*` tasks still return pre-formatted strings:

```python
if isinstance(suggested_text, str):
    # Use legacy formatter
    formatted_docstring = self._format_docstring(suggested_text, docstring_indent)
```

## Migration Notes

### What Changed in FASE 2

1. **Formatters now return complete docstrings**
   - BEFORE: Returned text without quotes/indentation
   - AFTER: Return complete `"""..."""` with indentation

2. **Processor returns Pydantic objects**
   - BEFORE: Returned formatted strings
   - AFTER: Returns ModuleDocstring/ClassDocstring/MethodDocstring objects

3. **Applier detects types and routes**
   - BEFORE: Always used `_format_docstring()` method
   - AFTER: Uses `isinstance()` to route to correct formatter

4. **Unified indentation extraction**
   - BEFORE: Different logic in different methods
   - AFTER: `_extract_indentation()` and `_add_indent_level()` helpers

### What Stayed the Same

1. **Line numbering convention** (1-indexed external, 0-indexed internal)
2. **Marker detection logic** (`marker_detector.py`)
3. **Google Style format** (Args, Returns, Raises sections)
4. **79-character line wrapping** (Pydantic validators)
5. **`_format_docstring()` method** (kept for validate_* tasks)

## Future Improvements

1. **Configuration**: Allow users to configure indent size (2 vs 4 spaces)
2. **Validation**: Add pre-injection validation of formatted docstrings
3. **Caching**: Cache compiled formatters for repeated use
4. **Metrics**: Track formatting success rate and indentation accuracy

## References

- [Google Python Style Guide - Docstrings](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
- [OpenAI Structured Outputs Documentation](https://platform.openai.com/docs/guides/structured-outputs)
- [Pydantic BaseModel Documentation](https://docs.pydantic.dev/latest/concepts/models/)