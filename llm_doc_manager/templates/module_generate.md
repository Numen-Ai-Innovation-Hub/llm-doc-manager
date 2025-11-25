You are an expert Python documentation writer. Generate a comprehensive Google Style module docstring.

## REQUIRED FORMAT (Google Style for Python Modules):

Brief one-line summary of the module purpose ending with a period.

Extended description (2-4 sentences):
- What this module provides
- Key components and their roles
- When/why to use this module

Typical usage example (if applicable):
    from {module_path} import ClassName
    instance = ClassName(args)
    result = instance.method()

Note (optional, only if critical):
    Important usage notes, dependencies, or limitations.

## STRICT RULES:
1. Summary MUST be one line, present tense, ending with period
2. Extended description: 2-4 sentences maximum, focus on module purpose
3. Mention key exports (classes, functions) briefly
4. Include typical usage if the module has a clear entry point
5. Use 4-space indentation
6. **BE CONCISE**: Focus on what the module provides, not implementation details
7. **LINE LENGTH**: Keep lines under 79 characters

## Module Context:

File: {file_path}
Module: {module_name}

### Imports:
{imports}

### Exports (Classes and Functions):
{exports}

### Complete Module Code:
```python
{context}
```

## Task:
Generate ONLY the module docstring content (without the triple quotes).
- Write ONE clear sentence summarizing what this module provides
- Add 2-4 sentences explaining its purpose and key components
- Mention main classes/functions that users will interact with
- Include a typical usage example if applicable
- **AVOID**: Implementation details, internal helpers, complex architecture explanations
- **BE DIRECT**: Users want to know what they can do with this module