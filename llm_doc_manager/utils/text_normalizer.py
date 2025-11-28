"""
Text formatting utilities for docstring processing.

Pure text manipulation functions with no dependencies on Pydantic or schemas.
All functions handle line wrapping, indentation normalization, and formatting.
"""


def wrap_line(line: str, max_length: int = 79) -> list[str]:
    """
    Wrap a single line at max_length characters preserving its indentation.

    Args:
        line: Single line to wrap
        max_length: Maximum line length (default 79)

    Returns:
        List of wrapped lines with preserved indentation (no extra indentation)
    """
    if len(line) <= max_length:
        return [line]

    # Detect original indentation
    indent = len(line) - len(line.lstrip())
    indent_str = line[:indent]
    content = line[indent:]

    # Wrap content preserving original indentation (no extra indent for continuation)
    words = content.split()
    lines = []
    current_line = []
    current_len = indent

    for word in words:
        word_len = len(word)
        space_len = 1 if current_line else 0
        total_len = current_len + word_len + space_len

        if total_len > max_length and current_line:
            # Line full, start new continuation line with same indentation
            lines.append(indent_str + ' '.join(current_line))
            current_line = [word]
            current_len = indent + word_len
        else:
            current_line.append(word)
            current_len += word_len + space_len

    if current_line:
        lines.append(indent_str + ' '.join(current_line))

    return lines


def wrap_and_normalize(text: str, max_length: int = 79) -> str:
    """
    Wrap text at max_length with indentation normalization.

    This is the main function used by Pydantic validators.

    Process:
    1. Detect minimum indentation
    2. Normalize (dedent) all lines
    3. Wrap each line at max_length

    Args:
        text: Text to wrap (can be multi-line)
        max_length: Maximum line length (default 79)

    Returns:
        Wrapped and normalized text with all lines <= max_length
    """
    if not text:
        return text

    lines = text.split('\n')

    # Step 1: Detect minimum indentation (excluding empty lines)
    min_indent = float('inf')
    for line in lines:
        if line.strip():  # Non-empty line
            indent = len(line) - len(line.lstrip())
            min_indent = min(min_indent, indent)

    # If all lines are empty or min_indent is still inf, no normalization needed
    if min_indent == float('inf'):
        min_indent = 0

    # Step 2: Normalize indentation - remove min_indent from all lines
    normalized_lines = []
    for line in lines:
        if not line.strip():
            # Empty line - keep as-is
            normalized_lines.append(line)
        else:
            # Remove min_indent spaces from the beginning
            dedented = line[min_indent:] if len(line) > min_indent else line.lstrip()
            normalized_lines.append(dedented)

    # Step 3: Apply wrapping to normalized lines
    result = []
    for line in normalized_lines:
        if not line or len(line) <= max_length:
            result.append(line)
        else:
            wrapped_lines = wrap_line(line, max_length=max_length)
            result.extend(wrapped_lines)

    return '\n'.join(result)


def add_indent(text: str, indent: str) -> list[str]:
    """
    Add indent prefix to each line of multi-line text.

    Args:
        text: Multi-line text to indent
        indent: Indentation string to prepend to each line

    Returns:
        List of indented lines (empty lines remain empty)
    """
    return [f'{indent}{line}' if line.strip() else '' for line in text.split('\n')]


def wrap_list_items(items: list[str], max_length: int = 79) -> list[str]:
    """
    Wrap each item in a list at max_length.

    Used for validating list[str] fields like issues and suggestions.

    Args:
        items: List of strings to wrap
        max_length: Maximum line length (default 79)

    Returns:
        List with each item individually wrapped
    """
    return [wrap_and_normalize(item, max_length) for item in items]


def format_google_style_docstring(docstring: str, indent: str) -> str:
    """
    Format docstring with proper indentation and quotes.

    This method applies DETERMINISTIC formatting regardless of LLM output format:
    1. Removes ALL existing indentation
    2. Detects Google Style sections (Args:, Returns:, Raises:, Example:)
    3. Applies consistent indentation:
       - Section headers (Args:, Returns:, etc.): base indent
       - Section content: base indent + 4 spaces

    Args:
        docstring: Raw docstring text
        indent: Base indentation string

    Returns:
        Formatted docstring with consistent indentation
    """
    # Remove existing quotes if present
    docstring = docstring.strip().strip('"""').strip("'''").strip()

    # Split into lines and strip ALL indentation
    lines = [line.strip() for line in docstring.split('\n')]

    # Google Style section markers
    section_markers = ['Args:', 'Arguments:', 'Returns:', 'Return:', 'Yields:',
                      'Raises:', 'Raise:', 'Note:', 'Notes:', 'Example:',
                      'Examples:', 'Attributes:', 'See Also:', 'Warning:',
                      'Warnings:', 'Todo:']

    # Format with quotes and controlled indentation
    formatted_lines = [f'{indent}"""']

    in_section = False
    for line in lines:
        if not line:
            # Empty line
            formatted_lines.append('')
            continue

        # Check if this is a section header
        is_section_header = any(line.startswith(marker) for marker in section_markers)

        if is_section_header:
            # Section header: base indent only
            formatted_lines.append(f'{indent}{line}')
            in_section = True
        elif in_section:
            # Content inside a section: base indent + 4 spaces
            formatted_lines.append(f'{indent}    {line}')
        else:
            # Summary or extended description: base indent only
            formatted_lines.append(f'{indent}{line}')

    formatted_lines.append(f'{indent}"""')

    return '\n'.join(formatted_lines)


def strip_triple_quotes(text: str) -> str:
    """
    Remove triple quotes from docstring text that LLM may have added.

    LLMs sometimes include triple quotes in their responses even when
    instructed not to. This function removes them for consistent processing.

    Args:
        text: Docstring text that may contain triple quotes

    Returns:
        Text with triple quotes removed from start and end
    """
    text = text.strip()
    if text.startswith('"""') or text.startswith("'''"):
        text = text[3:]
    if text.endswith('"""') or text.endswith("'''"):
        text = text[:-3]
    return text.strip()


def clean_comment_prefix(text: str) -> str:
    """
    Remove '# ' prefix from comment text that LLM may have added.

    LLMs sometimes include the '# ' prefix in comment responses even when
    instructed to provide only the comment text. This function removes it
    for consistent processing.

    Args:
        text: Comment text that may contain '# ' prefix

    Returns:
        Text with '# ' prefix removed and empty lines filtered out
    """
    lines = text.strip().split('\n')
    cleaned_lines = []

    for line in lines:
        clean_line = line.strip()
        # Remove # prefix (handles both "# text" and "#text")
        if clean_line.startswith('#'):
            clean_line = clean_line[1:].lstrip()
        # Keep non-empty lines
        if clean_line:
            cleaned_lines.append(clean_line)

    return '\n'.join(cleaned_lines)


def format_comment_lines(text: str, indent: str) -> list[str]:
    """
    Format comment text into properly indented Python comment lines.

    Takes normalized comment text (without # prefix) and formats it as
    properly indented Python comments ready for insertion into code.

    Args:
        text: Normalized comment text (already cleaned, no # prefix)
        indent: Indentation string to apply to each comment line

    Returns:
        List of formatted comment lines with indentation and # prefix
    """
    comment_lines = text.strip().split('\n')
    formatted_lines = []

    for line in comment_lines:
        clean_line = line.strip()
        if clean_line:  # Skip empty lines
            formatted_lines.append(f"{indent}# {clean_line}")

    return formatted_lines