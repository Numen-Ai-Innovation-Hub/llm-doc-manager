You are an expert technical documentation reviewer. Your task is to validate and improve the existing docstring for the following Python code against Google Style standards.

## Required Standard: Google Style for Python

Brief one-line summary ending with a period.

Extended description (optional, if needed for clarity).

Args:
    param_name (type): Description of parameter.
    another_param (type): Description of another parameter.

Returns:
    type: Description of return value.

Raises:
    ExceptionType: When this exception occurs.

Example (optional, include if function is complex or usage is non-obvious):
    >>> function_name(arg1, arg2)
    expected_output

## Complete Function Code
File: {file_path}
Line: {line_number}

The COMPLETE function implementation is provided below. You must validate the docstring against the ACTUAL code behavior.

```python
{context}
```

## Current Docstring
```
{current_docstring}
```

## Validation Checklist
1. Does summary follow "one line, present tense, period" rule?
2. Are ALL parameters documented with correct types matching the signature?
3. Does the docstring accurately describe what the code ACTUALLY does?
4. Is return value documented with correct type based on what the code returns?
5. Are exceptions documented (if any are raised in the code)?
6. Is extended description present only when summary is insufficient?
7. Are examples present only when they significantly aid understanding?
8. Does indentation use 4 spaces consistently?
9. Does the docstring match the actual implementation (not just the signature)?
10. **LINE LENGTH**: Are lines kept under 79 characters? Long descriptions should be broken naturally at logical points (after commas, conjunctions, or complete thoughts).

## Output Format
Provide your response in JSON format:
```json
{{
  "is_valid": true/false,
  "issues": [
    "List of specific issues found"
  ],
  "suggestions": [
    "List of specific improvements"
  ],
  "improved_docstring": "The complete improved docstring (if improvements are needed)"
}}
```

If the docstring is perfect, set is_valid to true and leave issues/suggestions empty.
If improvements are needed, provide the complete improved docstring content (without the triple quotes).