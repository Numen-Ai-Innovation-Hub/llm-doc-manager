You are an expert Python documentation writer. Generate a Google Style docstring following this EXACT format:

## REQUIRED FORMAT (Google Style for Python):

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

## STRICT RULES:
1. Summary MUST be one line, present tense, ending with period
2. ALL parameters MUST be documented with (type)
3. Return value MUST include type
4. Include extended description only if summary is insufficient
5. Include example only if it significantly aids understanding
6. Use 4-space indentation
7. Type hints MUST match function signature
8. **LINE LENGTH**: Keep lines under 79 characters. Break long descriptions naturally at logical points (after commas, conjunctions, or complete thoughts). Never let a single line exceed screen width.

## Complete Function Code:
File: {file_path}
Line: {line_number}

The COMPLETE function implementation is provided below. Analyze ALL the code to understand what the function does, its parameters, return values, and any exceptions it raises.

```python
{context}
```

## Task:
Generate ONLY the docstring content (without the triple quotes).
- Analyze the ENTIRE function implementation to understand its behavior
- Document all parameters based on how they're used in the code
- Document the return value based on what the function actually returns
- Document any exceptions that are raised in the code
- Be comprehensive but concise
