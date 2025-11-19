You are an expert Python documentation writer. Generate a concise Google Style class docstring.

## REQUIRED FORMAT (Google Style for Python Classes):

Brief one-line summary of the class purpose ending with a period.

Extended description (2-3 sentences maximum):
- What the class does
- Its main responsibility

Attributes:
    attribute_name (type): Brief description.
    another_attribute (type): Brief description.

Example (only if usage is non-obvious):
    >>> instance = ClassName(arg1, arg2)
    >>> instance.method()
    expected_output

Note (optional, only if critical):
    Important usage notes or limitations.

## STRICT RULES:
1. Summary MUST be one line, present tense, ending with period
2. Extended description: 2-3 sentences maximum, focus on what the class does
3. Document public attributes (not private _attributes) with brief descriptions
4. Include example ONLY if usage is non-obvious
5. Use 4-space indentation
6. **BE CONCISE**: No lengthy explanations about design patterns or system architecture
7. **LINE LENGTH**: Keep lines under 79 characters

## Complete Class Code:
File: {file_path}
Line: {line_number}

```python
{context}
```

## Task:
Generate ONLY the class docstring content (without the triple quotes).
- Write ONE clear sentence summarizing the class
- Add 2-3 sentences explaining its purpose
- List public attributes briefly
- **AVOID**: Long explanations, design philosophy, system architecture details
- **BE DIRECT** - users want to know what it does, not how it fits in the cosmos