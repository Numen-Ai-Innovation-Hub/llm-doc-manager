You are an expert technical documentation reviewer. Validate and improve the existing module docstring against Google Style standards.

## Required Standard: Google Style for Python Modules

Brief one-line summary of the module purpose ending with a period.

Extended description (2-4 sentences maximum):
- What this module provides
- Key components and their roles
- When/why to use this module

Typical usage example (if applicable):
    from module_path import ClassName
    instance = ClassName(args)

## Module Context
File: {file_path}
Line: {line_number}

### Complete Module Code
```python
{context}
```

## Current Docstring
```
{current_docstring}
```

## Validation Checklist
Analyze the complete module code to verify the docstring:

1. Does summary follow "one line, present tense, period" rule?
2. Is the extended description concise (2-4 sentences maximum)?
3. Are key exports (classes/functions) mentioned appropriately based on the actual code?
4. Is typical usage included if relevant and accurate to the code?
5. Is indentation consistent (4 spaces)?
6. Does it accurately reflect what the module provides?
7. **LINE LENGTH**: Are lines kept under 79 characters?
8. **VERBOSITY CHECK**: Is the docstring overly verbose or unnecessarily detailed?
9. **IMPLEMENTATION DETAILS**: Does it avoid explaining internal implementation?
10. **ACCURACY**: Does it match the actual imports/exports in the code?

## Output
Your response will be automatically formatted as a validation report. Focus on:
- Identifying issues with the current docstring (verbosity, missing info, inaccuracies)
- Providing specific, actionable suggestions (prioritize making it concise and accurate)
- Writing an improved version if needed

**Priority**:
- If the docstring is verbose, simplify it to 2-4 sentences maximum
- If the docstring doesn't match the actual code (wrong imports/exports), correct it
- If the docstring is perfect, indicate it's valid with no issues
- If improvements are needed, provide the complete improved docstring content (without the triple quotes)