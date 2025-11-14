You are an expert technical documentation reviewer. Validate and improve the existing class docstring against Google Style standards.

## Required Standard: Google Style for Python Classes

Brief one-line summary of the class purpose ending with a period.

Extended description explaining:
- What the class represents
- Its main responsibilities
- Key design decisions or patterns used

Attributes:
    attribute_name (type): Description of attribute.

Example (optional):
    >>> instance = ClassName()
    >>> instance.method()
    expected_output

## Complete Class Code
File: {file_path}
Line: {line_number}

```python
{context}
```

## Current Docstring
```
{current_docstring}
```

## Validation Checklist
1. Does summary follow "one line, present tense, period" rule?
2. Is the class's purpose clearly explained?
3. Are all public attributes documented with correct types?
4. Does extended description explain responsibilities and design?
5. Is indentation consistent (4 spaces)?
6. Does it match the actual class implementation?

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