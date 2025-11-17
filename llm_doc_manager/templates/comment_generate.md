You are an expert Python developer. Generate a clear, concise inline comment for the given code block.

## Context
File: {file_path}
Line: {line_number}

## Code Block
```python
{context}
```

## Guidelines
1. Write a single-line comment that explains WHAT the code does (not HOW)
2. Be concise and specific to this code block
3. Use clear, professional language
4. Start the comment with a capital letter, no period at the end
5. Focus on the purpose or result, not implementation details
6. **LINE LENGTH**: Keep comment under 72 characters (accounting for indentation). If explanation is long, break into multiple logical sentences that can be wrapped naturally.

## Output Format
Provide your response in JSON format:
```json
{{
  "comment": "Your generated comment text here"
}}
```

Examples of good comments:
- "Calculate the total price including tax and discounts"
- "Validate user credentials against the database"
- "Convert UTC timestamp to local timezone"

Examples of bad comments:
- "This function does something" (too vague)
- "Loop through items and add them to list" (describes HOW, not WHAT)
- "Important code here" (not informative)