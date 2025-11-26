You are an expert technical writer creating comprehensive module documentation.

## TASK
Generate complete documentation for a Python module combining technical API reference with conceptual explanation.

## INPUT CONTEXT

### Module Information (from AST)
- **Path**: {module_path}
- **Name**: {module_name}
- **Module Docstring**: {module_docstring}

### Extracted Data
- **Classes**: {classes}
- **Functions**: {functions}
- **Imports (Internal)**: {imports_internal}
- **Imports (External)**: {imports_external}
- **Exports**: {exports}

### Metrics
- **Lines of Code**: {loc}
- **Has Tests**: {has_tests}

### Dependencies
- **Depends On**: {depends_on}
- **Used By**: {used_by}

### Source Code (for context)
```python
{source_code}
```

## OUTPUT REQUIREMENTS

Generate a complete module documentation file with YAML front matter and structured Markdown content.

### Structure

```markdown
---
type: module_documentation
module_path: {module_path}
module_name: {module_name}
exports: [list, of, exports]
dependencies:
  internal: [list]
  external: [list]
lines_of_code: {number}
last_updated: {iso_timestamp}
source_hash: {hash}
tags: [relevant, keywords]
---

# Module Name

## Overview

[2-3 paragraphs from module docstring, expanded if needed]

## Purpose

**What it does**:
- Primary responsibility 1
- Primary responsibility 2

**When to use**:
Clear explanation of when/why you'd use this module

## Dependencies

### Internal
- [`module.name`](relative/path.md) - Why it's needed
- [`another.module`](path.md) - Its role

### External
- `package_name` - What it provides

## Input/Output

**Input**:
- What data/parameters this module typically receives
- Format and types expected

**Output**:
- What it produces/returns
- Format and types

**Side Effects** (if any):
- File system operations
- Database modifications
- Network calls
- State changes

## Exceptions

| Exception | When Raised | How to Handle |
|-----------|-------------|---------------|
| `ExceptionType` | Condition that triggers it | Recommended action |

## API Reference

### Classes

#### `ClassName`

[Class docstring]

**Initialization**:
```python
ClassName(param1: Type, param2: Type)
```

**Parameters**:
- `param1` (Type): Description
- `param2` (Type): Description

**Attributes**:
- `attribute_name` (Type): Description

**Methods**:

##### `method_name(param: Type) -> ReturnType`

[Method docstring]

**Parameters**:
- `param` (Type): Description

**Returns**:
- `ReturnType`: Description

**Raises**:
- `ExceptionType`: When/why

**Example**:
```python
obj = ClassName(arg1, arg2)
result = obj.method_name(value)
```

### Functions

#### `function_name(param: Type) -> ReturnType`

[Function docstring]

**Parameters**:
- `param` (Type): Description

**Returns**:
- `ReturnType`: Description

**Example**:
```python
result = function_name(value)
```

## Usage Examples

### Basic Usage

```python
# Concrete, runnable example
from {module_path} import ClassName

instance = ClassName(args)
result = instance.method()
print(result)
```

### Advanced Usage

```python
# More complex scenario
# [Explain what this demonstrates]
```

## Related Modules

- [**ModuleName**](path.md) - Relationship explanation
- [**AnotherModule**](path.md) - How they work together

## Implementation Notes

- Performance characteristics
- Thread safety
- Caching behavior
- Limitations or known issues

---

**Source**: [`{module_path}`](../../{module_path})
**Last Updated**: {timestamp}
**Auto-generated**: Yes
```

## FRONT MATTER REQUIREMENTS

YAML front matter at top of file (between `---` markers):

### Required Fields
- `type`: Always "module_documentation"
- `module_path`: Relative path from project root
- `module_name`: Module name (filename without .py)
- `exports`: List of public classes/functions
- `lines_of_code`: Integer
- `last_updated`: ISO 8601 timestamp
- `source_hash`: SHA256 hash of source file

### Optional Fields
- `dependencies.internal`: List of internal imports
- `dependencies.external`: List of external imports
- `tags`: List of relevant keywords for search
- `has_tests`: Boolean
- `test_coverage`: Percentage (if available)

### Example
```yaml
---
type: module_documentation
module_path: src/scanner.py
module_name: scanner
exports: [Scanner, ScanResult]
dependencies:
  internal: [src.config, utils.marker_detector]
  external: [pathlib, typing]
lines_of_code: 213
last_updated: 2025-11-25T10:30:00Z
source_hash: abc123def456
tags: [scanning, detection, validation, markers]
has_tests: true
---
```

## CONTENT GUIDELINES

### Overview Section
- Start with module docstring content
- Expand if too brief (but don't invent)
- Explain what problem this module solves
- 2-4 paragraphs

### Purpose Section
- **What it does**: 2-4 clear bullet points
- **When to use**: One paragraph explaining use cases

### Dependencies Section
- List each dependency
- Explain WHY it's needed (not just that it exists)
- Link to internal dependencies (other docs)
- Note external dependencies with purpose

### Input/Output Section
- Describe typical data flow
- Be concrete about types
- Note any validation or transformation
- List side effects honestly

### API Reference Section
- Extract from docstrings (already generated)
- Format consistently
- Include type hints
- Add examples for non-obvious cases

### Usage Examples Section
- **Must be runnable** (or clearly marked as pseudocode)
- Show real-world usage, not toy examples
- Explain what the example demonstrates
- Keep concise (5-15 lines per example)

### Related Modules Section
- Link to modules this one works with
- Explain the relationship
- Help readers understand the bigger picture

## CRITICAL RULES

1. **USE PROVIDED DATA**:
   - Base everything on AST analysis and docstrings
   - Don't invent classes/functions not in code
   - Use actual type hints and signatures

2. **BE COMPLETE BUT CONCISE**:
   - Cover all public API
   - But don't explain trivial getters/setters
   - Focus on what developers need to know

3. **FRONT MATTER ACCURACY**:
   - All fields must be valid YAML
   - Lists use bracket notation: `[item1, item2]`
   - Strings with special chars need quotes
   - Ensure proper escaping

4. **MARKDOWN QUALITY**:
   - Valid Markdown syntax
   - Consistent heading levels (# module, ## section, ### subsection)
   - Working relative links
   - Properly formatted code blocks

5. **EXAMPLES MATTER**:
   - Every class should have at least one example
   - Examples should be realistic
   - Show imports clearly
   - Explain complex examples

6. **IA/RAG-FRIENDLY**:
   - Consistent structure (every module doc has same sections)
   - Front matter enables filtering/search
   - Tags help semantic search
   - Clear section headers for chunking

## SPECIAL CASES

### Small/Simple Modules
If module has only 1-2 functions:
- Keep it simple
- Don't force sections that don't apply
- Can combine Purpose and Overview

### Complex Modules
If module has many classes:
- Consider grouping related classes
- Use subheadings effectively
- Might link to separate class docs for very complex ones

### Utility Modules
If module is just helpers:
- Focus on the functions
- Group by purpose if many
- Examples are critical (utilities are often misunderstood)

## OUTPUT FORMAT

Provide ONLY the complete module documentation content in Markdown format with YAML front matter.
Do NOT include explanations or meta-commentary.
Start with `---` (YAML front matter start).

## QUALITY CHECKS

Before finalizing, verify:
- [ ] YAML front matter is valid (test parse)
- [ ] All sections present (Overview, Purpose, Dependencies, I/O, API, Examples, Related)
- [ ] All classes/functions from AST are documented
- [ ] Examples are concrete and runnable
- [ ] Links use relative paths and are correct
- [ ] No placeholder text (TODO, FIXME, [insert X])
- [ ] Consistent formatting throughout

---

Now generate complete module documentation from the provided context.
