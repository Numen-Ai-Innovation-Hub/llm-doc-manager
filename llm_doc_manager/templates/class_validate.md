You are an expert technical documentation reviewer. Validate and improve the existing class docstring against Google Style standards.

## Required Standard: Google Style for Python Classes

Brief one-line summary of the class purpose ending with a period.

Extended description (2-3 sentences maximum):
- What the class does
- Its main responsibility

Attributes:
    attribute_name (type): Brief description.

Example (only if usage is non-obvious):
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
2. Is the extended description concise (2-3 sentences maximum)?
3. Are all public attributes documented briefly with correct types?
4. Is indentation consistent (4 spaces)?
5. Does it match the actual class implementation?
6. **LINE LENGTH**: Are lines kept under 79 characters?
7. **VERBOSITY CHECK**: Is the docstring overly verbose or unnecessarily detailed?

## Output Format
Provide your response in JSON format:
```json
{{
  "is_valid": true/false,
  "issues": [
    "List of specific issues found (focus on verbosity, missing info, or incorrect info)"
  ],
  "suggestions": [
    "List of specific improvements (prioritize making it more concise)"
  ],
  "improved_docstring": "The complete improved docstring (if improvements are needed)"
}}
```

**Priority**: If the docstring is verbose, simplify it to 2-3 sentences maximum.
If the docstring is perfect, set is_valid to true and leave issues/suggestions empty.
If improvements are needed, provide the complete improved docstring content (without the triple quotes).