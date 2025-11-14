# LLM Doc Manager

Automated Python docstring validation and generation using Large Language Models.

## Overview

LLM Doc Manager is a precision tool that helps you automatically generate and validate Python docstrings using AI. It uses delimiter-based markers to identify functions that need documentation, sends the complete function code to an LLM, and applies generated docstrings following Google Style standards.

## Key Features

- ✅ **Delimiter-based markers** - Precise function identification with `@llm-doc-start` / `@llm-doc-end`
- ✅ **Google Style only** - Zero configuration, standardized documentation format
- ✅ **Multiple LLM providers** - Anthropic Claude, OpenAI GPT, Ollama (local)
- ✅ **Auto-detection** - Automatically determines if docstring needs generation or validation
- ✅ **Safe operation** - Automatic backups before any changes
- ✅ **Interactive review** - Review and approve changes before applying
- ✅ **Database-driven queue** - SQLite-based task management with persistent state
- ✅ **Auto-cleanup** - Applied tasks automatically removed from queue
- ✅ **Portable** - Install once, use in any Python project

## Installation

### From source (editable mode)

```bash
# Navigate to the project directory
cd path/to/llm_doc_manager

# Install in editable mode
pip install -e .
```

### Direct installation

```bash
pip install path/to/llm_doc_manager
```

### Verify installation

```bash
llm-doc-manager --help
```

## Quick Start

### 1. Add delimiter markers to your code

```python
# @llm-doc-start
def process_payment(amount: float, currency: str) -> dict:
    """Process payment transaction."""
    if amount <= 0:
        raise ValueError("Amount must be positive")

    result = {
        "status": "processed",
        "amount": amount,
        "currency": currency,
        "timestamp": datetime.now()
    }
    return result
# @llm-doc-end

# @llm-doc-start
def calculate_discount(price, quantity):
    # No docstring - will be generated
    if quantity >= 10:
        return price * 0.9
    return price
# @llm-doc-end
```

**How it works:**
- The tool extracts the **complete function code** between delimiters
- If a docstring exists and is valid → **validates** it against the actual implementation
- If no docstring or placeholder (`TODO`, `TO_REVIEW`, etc.) → **generates** a new docstring
- All docstrings follow **Google Style** format (hardcoded, no configuration needed)

### 2. Initialize in your project

```bash
cd /path/to/your/project
llm-doc-manager init
```

This creates `.llm-doc-manager/` directory with:
- `config.yaml` - Configuration file
- `queue.db` - SQLite database for task queue
- `backups/` - Automatic backups before changes

### 3. Configure API key

**Option A: Environment variable (recommended)**

```bash
# Windows (PowerShell)
$env:ANTHROPIC_API_KEY="your-api-key-here"

# Windows (CMD)
set ANTHROPIC_API_KEY=your-api-key-here

# Linux/Mac
export ANTHROPIC_API_KEY="your-api-key-here"
```

**Option B: .env file in project root**

Create `.env` file in your project:
```
ANTHROPIC_API_KEY=your-api-key-here
```

**Option C: Config file (not recommended)**

Edit `.llm-doc-manager/config.yaml`:
```yaml
llm:
  api_key: "your-api-key-here"  # Not secure if versioned
```

### 4. Scan your code

```bash
llm-doc-manager scan
```

Output:
```
🔍 Scanning project for documentation markers...

✓ Scan complete!
  Files scanned: 15
  Tasks created: 8

Next: Run 'llm-doc-manager process' to generate suggestions
```

**What happens:**
- Scans all `.py` files in current directory (recursively)
- Finds all `@llm-doc-start` / `@llm-doc-end` pairs
- Extracts complete function code
- Detects if docstring exists and is valid
- Creates tasks in `queue.db` (pending status)

### 5. Process with LLM

```bash
llm-doc-manager process
```

Output:
```
🤖 Processing 8 task(s)...

Processing tasks  [####################################]  100%

✓ Processing complete!
  Successful: 8
  Failed: 0
  Total tokens used: 12,450

Suggestions saved to queue database.
Next: Run 'llm-doc-manager review' to review suggestions
```

**What happens:**
- Reads pending tasks from queue database
- Sends complete function code to LLM with appropriate template
- LLM analyzes the **entire implementation** (not just signature)
- Generates/validates docstrings following Google Style
- Stores suggestions in database (with `suggestion` column)

### 6. Review suggestions

```bash
llm-doc-manager review
```

Interactive review interface:
```
[1/8] src/payment/processor.py:15
Type: validate_docstring
============================================================

Current docstring:
------------------------------------------------------------
Process payment transaction.
------------------------------------------------------------

Suggested improvement:
------------------------------------------------------------
Process a payment transaction with validation.

This function validates the payment amount and currency,
then processes the transaction with a timestamp.

Args:
    amount (float): Payment amount in specified currency. Must be positive.
    currency (str): ISO 4217 currency code (e.g., 'USD', 'EUR').

Returns:
    dict: Transaction result containing:
        - status (str): Processing status ('processed')
        - amount (float): Processed amount
        - currency (str): Currency code
        - timestamp (datetime): Transaction timestamp

Raises:
    ValueError: If amount is not positive.
------------------------------------------------------------

[a]ccept, [s]kip, [q]uit: a
✓ Accepted
```

**What happens:**
- Shows each suggestion one by one
- `accept` → marks task as accepted (sets `accepted=1` in database)
- `skip` → leaves task as-is
- `quit` → exits review (can resume later)

### 7. Apply changes

```bash
llm-doc-manager apply
```

Output:
```
📝 Applying 6 suggestion(s)...

✓ src/payment/processor.py:15
✓ src/payment/validator.py:42
✓ src/core/engine.py:89
✓ src/utils/helpers.py:123
✓ src/models/transaction.py:67
✓ src/services/email.py:201

✓ Applied 6 change(s)

Backups saved to: .llm-doc-manager/backups/
To rollback: llm-doc-manager rollback --file-path <file>
```

**What happens:**
- Creates backup for each file before modification
- Finds the function by searching backwards from marker line
- Replaces or inserts docstring with correct indentation
- **Automatically deletes applied tasks from queue**
- Failed applications remain in queue for retry

## Marker System

### Delimiter Markers

The tool uses delimiter-based markers for precise identification:

```python
# @llm-doc-start
def your_function(params):
    """Existing docstring or placeholder."""
    # ... implementation ...
# @llm-doc-end
```

**Rules:**
- Markers must be on their own line
- Markers can have any indentation (must match on both sides)
- Everything between markers is treated as function code
- The tool extracts the **complete function** including body

**Auto-detection logic:**
- **Has valid docstring** → Task type: `validate_docstring`
- **No docstring OR placeholder** → Task type: `generate_docstring`
- **Placeholders detected**: `TODO`, `TO_DO`, `FIXME`, `TO_REVIEW`, `PLACEHOLDER`

### Examples

**Example 1: Generate docstring**
```python
# @llm-doc-start
def calculate_total(items, tax_rate=0.1):
    total = sum(item['price'] * item['qty'] for item in items)
    return total * (1 + tax_rate)
# @llm-doc-end
```

**Example 2: Validate existing docstring**
```python
# @llm-doc-start
def send_email(recipient: str, subject: str, body: str) -> bool:
    """Send email to recipient."""
    # ... implementation ...
    return True
# @llm-doc-end
```

**Example 3: Replace placeholder**
```python
# @llm-doc-start
async def fetch_user_data(user_id: int) -> dict:
    """TODO"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"/users/{user_id}")
        return response.json()
# @llm-doc-end
```

## Commands Reference

### Core Workflow

| Command | Description | Parameters |
|---------|-------------|------------|
| `init` | Initialize configuration | `--overwrite` (optional) |
| `scan` | Scan for delimiter markers | `--path` (multiple, optional) |
| `process` | Process tasks with LLM | `--limit` (optional) |
| `review` | Review suggestions interactively | None |
| `apply` | Apply accepted suggestions | None |
| `status` | Show queue statistics | None |
| `clear` | Clear all tasks from queue | None |
| `rollback` | Rollback file to backup | `--file-path` (required) |

### Command Examples

```bash
# Initialize
llm-doc-manager init
llm-doc-manager init --overwrite  # Overwrite existing config

# Scan
llm-doc-manager scan                    # Scan current directory
llm-doc-manager scan --path src         # Scan specific directory
llm-doc-manager scan --path src --path tests  # Multiple paths

# Process
llm-doc-manager process                 # Process all pending tasks
llm-doc-manager process --limit 10      # Process only 10 tasks

# Review
llm-doc-manager review                  # Interactive review

# Apply
llm-doc-manager apply                   # Apply accepted tasks (auto-removes from queue)

# Status
llm-doc-manager status                  # Show queue statistics

# Clear
llm-doc-manager clear                   # Clear all tasks (with confirmation)

# Rollback
llm-doc-manager rollback --file-path src/main.py
```

## Configuration

### Minimal Configuration

The tool follows **Zero Config** philosophy. Most settings are hardcoded for consistency.

Default config (`.llm-doc-manager/config.yaml`):

```yaml
llm:
  provider: anthropic
  model: claude-sonnet-4-5
  api_key: ${ANTHROPIC_API_KEY}  # Environment variable
  temperature: 0.3
  max_tokens: 4000

scanning:
  paths:
    - .  # Current directory
  exclude:
    - "*.pyc"
    - "__pycache__"
    - ".venv"
    - "venv"
    - ".git"
    - "node_modules"
  max_file_size_mb: 5

output:
  mode: interactive
  backup: true
  backup_dir: .llm-doc-manager/backups
  diff_format: unified
  auto_apply_confidence_threshold: 0.9
```

### Configuration Notes

**Hardcoded (not configurable):**
- Documentation standard: **Google Style only**
- File types: **Python (.py) only**
- Examples in docstrings: **Optional** (LLM decides based on complexity)

**Configurable:**
- LLM provider and model
- Scanning paths and exclusions
- Backup settings
- Temperature and token limits

### Supported LLM Providers

**Anthropic Claude:**
```yaml
llm:
  provider: anthropic
  model: claude-sonnet-4-5  # or claude-3-opus-20240229
  api_key: ${ANTHROPIC_API_KEY}
```

**OpenAI GPT:**
```yaml
llm:
  provider: openai
  model: gpt-4  # or gpt-4-turbo, gpt-3.5-turbo
  api_key: ${OPENAI_API_KEY}
```

**Ollama (Local):**
```yaml
llm:
  provider: ollama
  model: llama2  # or codellama, mistral, etc.
  # No API key needed
```

## Workflow Examples

### Example 1: Full workflow

```bash
# Setup
cd /path/to/your/project
llm-doc-manager init
export ANTHROPIC_API_KEY="your-key"

# Mark functions in your code with delimiters
# ... edit your Python files ...

# Process
llm-doc-manager scan
llm-doc-manager process
llm-doc-manager review
llm-doc-manager apply

# Check status
llm-doc-manager status
```

### Example 2: Incremental processing

```bash
# Scan and process in batches
llm-doc-manager scan --path src/core
llm-doc-manager process --limit 5
llm-doc-manager review
llm-doc-manager apply

# Continue with more modules
llm-doc-manager scan --path src/utils
llm-doc-manager process --limit 5
llm-doc-manager review
llm-doc-manager apply
```

### Example 3: Multiple projects

```bash
# Project A
cd ~/projects/project-a
llm-doc-manager scan
llm-doc-manager process

# Project B
cd ~/projects/project-b
llm-doc-manager scan
llm-doc-manager process

# Each project has its own .llm-doc-manager/ directory
# Same tool, different projects!
```

### Example 4: Rollback if needed

```bash
# Apply changes
llm-doc-manager apply

# Oops, need to revert one file
llm-doc-manager rollback --file-path src/processor.py

# File restored from backup
```

## Safety Features

### Automatic Backups

Every file modification creates a timestamped backup:

```
.llm-doc-manager/backups/
├── processor.py.20251113_143022.bak
├── validator.py.20251113_143025.bak
└── engine.py.20251113_143030.bak
```

### Rollback Support

```bash
# Rollback specific file to most recent backup
llm-doc-manager rollback --file-path src/payment/processor.py
```

### Review Before Apply

Changes are **never** applied automatically:
1. `process` → generates suggestions, stores in database
2. `review` → user accepts/skips each suggestion
3. `apply` → only applies accepted suggestions
4. Auto-removes successfully applied tasks from queue

### Queue Persistence

All state is stored in SQLite database (`.llm-doc-manager/queue.db`):
- Can stop and resume at any time
- Tasks persist across sessions
- Safe to interrupt with Ctrl+C

## Database Schema

The queue uses SQLite with this schema:

```sql
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY,
    file_path TEXT NOT NULL,
    line_number INTEGER NOT NULL,
    task_type TEXT NOT NULL,  -- validate_docstring, generate_docstring
    marker_text TEXT,
    context TEXT,  -- Complete function code
    parameters TEXT,
    priority INTEGER DEFAULT 5,
    status TEXT DEFAULT 'pending',  -- pending, processing, completed, failed
    created_at TEXT,
    updated_at TEXT,
    error_message TEXT,
    suggestion TEXT,  -- LLM-generated docstring
    accepted INTEGER DEFAULT 0  -- 0 or 1
);
```

## Google Style Docstring Format

All docstrings follow Google Style:

```python
def function_name(param1: type, param2: type) -> return_type:
    """Brief one-line summary ending with period.

    Extended description (optional, only if needed for clarity).

    Args:
        param1 (type): Description of parameter.
        param2 (type): Description of another parameter.

    Returns:
        return_type: Description of return value.

    Raises:
        ExceptionType: When this exception occurs.

    Example (optional, only if function is complex):
        >>> function_name(arg1, arg2)
        expected_output
    """
```

**Style rules (enforced by templates):**
1. Summary: one line, present tense, ending with period
2. All parameters documented with types
3. Return value documented with type
4. Exceptions documented if raised in code
5. Extended description only if summary insufficient
6. Examples only if significantly aid understanding
7. 4-space indentation
8. Types must match function signature

## Troubleshooting

### No markers found

**Problem:** `llm-doc-manager scan` finds no tasks.

**Solution:** Add delimiter markers to your code:
```python
# @llm-doc-start
def your_function():
    pass
# @llm-doc-end
```

### API key not found

**Problem:** Error: "API key not found for provider: anthropic"

**Solution:** Set environment variable:
```bash
export ANTHROPIC_API_KEY="your-key-here"
```

### Configuration not found

**Problem:** Error: "Configuration not found"

**Solution:** Run `llm-doc-manager init` in project root first.

### Templates not found

**Problem:** Error loading templates

**Solution:** Reinstall the package:
```bash
pip install -e . --force-reinstall
```

### Backup directory issues

**Problem:** Cannot create backups

**Solution:** Check permissions on `.llm-doc-manager/backups/` directory.

## Project Structure

```
llm_doc_manager/
├── llm_doc_manager/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py              # Command-line interface
│   ├── config.py           # Configuration management
│   ├── markers.py          # Delimiter-based marker detection
│   ├── scanner.py          # File scanning
│   ├── queue.py            # SQLite task queue
│   ├── processor.py        # LLM processing
│   ├── applier.py          # Apply changes to files
│   └── templates/          # LLM prompt templates
│       ├── docstring_generate.md
│       └── docstring_validate.md
├── setup.py
├── requirements.txt
└── README.md
```

## Development

### Running Tests

```bash
pip install -e ".[dev]"
pytest
```

### Code Quality

```bash
black llm_doc_manager/
flake8 llm_doc_manager/
```

## Why Delimiter-Based?

**Previous approach (heuristics):** ❌
- Used decorators, comment markers, `TO_REVIEW` keywords
- Fragile: required exact patterns
- Limited: couldn't extract complete function code
- Ambiguous: multiple marker types caused confusion

**Current approach (delimiters):** ✅
- Explicit start/end boundaries
- Extracts complete function implementation
- Unambiguous: only one marker type
- Robust: works with any function structure
- LLM sees full context: parameters, body, exceptions

## License

MIT License

## Contributing

Contributions welcome! Please submit issues or pull requests.

## Roadmap

- [ ] Support for more languages (JavaScript, TypeScript, Java)
- [ ] Class-level documentation
- [ ] Module-level documentation
- [ ] VSCode extension
- [ ] GitHub Actions integration
- [ ] Custom prompt templates
- [ ] Documentation quality scoring
- [ ] Batch processing optimizations

---

**Created by AI Innovation Hub**
