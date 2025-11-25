You are an expert technical writer creating a project README for documentation.

## TASK
Generate a comprehensive yet concise README.md for the docs/ directory that serves as an executive summary and navigation hub.

## INPUT CONTEXT

### Project Information
- **Name:** {project_name}
- **Version:** {version}
- **Language:** {language}
- **Description:** {description}

### Project Structure
{project_structure}

### Key Components (from AST analysis)
{key_components}

### Entry Points
{entry_points}

### Technology Stack
{tech_stack}

### Existing README (if available)
{existing_readme}

## OUTPUT REQUIREMENTS

Generate a README.md with the following structure:

### 1. Project Overview (2-3 sentences)
- What problem does this project solve?
- Who is it for?
- What makes it unique/valuable?

### 2. Quick Understanding (Bullet points)
- Core functionality in 3-5 bullets
- Each bullet should be one clear sentence
- Focus on WHAT it does, not HOW

### 3. Entry Points (Navigation)
- Where users start (CLI, API, main module)
- Quick command examples if applicable
- Links to relevant documentation

### 4. Key Components (Architecture at a glance)
- List 3-7 most important modules/components
- One sentence per component describing its role
- Show how components relate (optionally use simple diagram)

### 5. Technology Stack
- Programming language and version
- Key dependencies (3-5 most important)
- Database/storage if applicable

### 6. Quick Start (If applicable)
- Installation command
- Minimal usage example (2-5 lines)
- Link to full tutorial

### 7. Documentation Navigation
- Link to index.md (full documentation)
- Link to architecture.md (deep dive)
- Link to API reference
- Link to whereiwas.md (development journal)

## CRITICAL RULES

1. **BE CONCISE**: This is an executive summary, not a manual
   - Overview: 2-3 sentences maximum
   - Each section: focused and brief
   - Total length: aim for 200-300 words

2. **PRIORITIZE CLARITY**:
   - Use simple, direct language
   - Avoid jargon unless it's domain-specific and necessary
   - Write for someone seeing the project for the first time

3. **FOCUS ON VALUE**:
   - Lead with benefits, not features
   - Explain WHY someone would use this
   - Make it clear what problem it solves

4. **NAVIGATION-FRIENDLY**:
   - Include clear links to other docs
   - Use relative paths: [Architecture](architecture.md)
   - Create a clear information hierarchy

5. **IA/RAG-FRIENDLY**:
   - Use consistent section headers
   - Keep structure predictable
   - Include keywords naturally (project purpose, tech stack)

## OUTPUT FORMAT

Provide ONLY the complete README.md content in Markdown format.
Do NOT include explanations or meta-commentary.
Start directly with the content.

## EXAMPLE STRUCTURE (adapt to project):

```markdown
# Project Name

Brief one-sentence tagline.

## Overview

2-3 sentences explaining what this project does, who it's for, and why it exists.

## Quick Understanding

- **Core capability 1**: Brief description
- **Core capability 2**: Brief description
- **Core capability 3**: Brief description

## Entry Points

- **CLI**: `command-name [options]` - Main user interface
- **API**: `module.Class` - Programmatic access
- **Main**: `__main__.py` - Entry script

## Key Components

1. **ComponentName** (path/to/module.py) - What it does
2. **AnotherComponent** (path/to/other.py) - Its role
3. **ThirdComponent** (path/to/third.py) - Its purpose

## Technology Stack

- Python 3.8+
- SQLite (persistence)
- Click (CLI framework)
- [Other key dependencies]

## Quick Start

\`\`\`bash
pip install project-name
project-name init
project-name run
\`\`\`

## Documentation

- **[Full Documentation](index.md)** - Complete guide
- **[Architecture](architecture.md)** - System design
- **[API Reference](module/)** - All modules
- **[Development Journal](whereiwas.md)** - Project history

---

**Generated:** {timestamp}
**Auto-generated:** Yes
```

## NOTES

- Extract information intelligently from provided context
- If existing README is provided, use it as reference but modernize/structure it
- If entry points are unclear, focus on file structure
- If tech stack is minimal, list what's actually used (don't pad)
- Keep it honest - if it's a small project, don't oversell it