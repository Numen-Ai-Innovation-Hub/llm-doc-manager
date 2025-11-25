You are an expert project chronicler creating a development journal from git history.

## TASK
Generate whereiwas.md - a development journal that tracks project evolution, current state, and next steps.

## INPUT CONTEXT

### Git Commit History (last 30-60 days)
{git_commits}

### Current Branch
{current_branch}

### Recent Activity Summary
- Total commits: {commit_count}
- Active period: {date_range}
- Contributors: {contributors}

### Project State
- Version: {version}
- Last release: {last_release}
- Open issues/TODOs (if available): {open_issues}

## OUTPUT REQUIREMENTS

Generate whereiwas.md with the following structure:

### 1. Header
```markdown
# Development Journal

Last Updated: {current_date}
Branch: {branch_name}
```

### 2. Current State (Top Section)
Brief summary (2-3 sentences):
- What was most recently worked on?
- Current focus area
- Status (stable, in development, broken)

### 3. Recent Work (Grouped by Date)

For each date with activity (most recent first):

```markdown
## YYYY-MM-DD

**Focus**: [Identified theme from commit messages]

### Changes
- [Summarized change 1]
- [Summarized change 2]
- [Pattern or trend observed]

**Commits**: hash1, hash2, hash3

---
```

### 4. Development Patterns (Analysis)

After listing recent work, analyze patterns:

```markdown
## Development Patterns

### Primary Activities
1. **Pattern Name** (X commits): Description of what was done repeatedly
2. **Another Pattern** (Y commits): Another recurring theme

### Key Milestones
- **Date**: Significant achievement or turning point
- **Date**: Another milestone

### Tech Debt / Refactoring
- [List of refactoring work identified from commits]
```

### 5. Next Steps (Forward-Looking)

Based on recent activity, suggest what's likely coming next:

```markdown
## Next Steps

### Immediate (Inferred from recent work)
- [ ] Item based on incomplete work
- [ ] Logical next step from recent changes
- [ ] Issue mentioned in commits

### Planned (From TODOs/issues if available)
- [ ] Known planned feature
- [ ] Documented TODO

### Technical Debt
- [ ] Refactoring needed (identified from code/comments)
```

## COMMIT MESSAGE ANALYSIS

### Categorizing Commits

Identify commit types from conventional commit prefixes or content:

- **feat**: New features
- **fix**: Bug fixes
- **refactor**: Code restructuring
- **docs**: Documentation changes
- **test**: Test additions/changes
- **chore**: Maintenance (dependencies, config)
- **perf**: Performance improvements

### Grouping Strategy

**By Date**:
- Group commits by day
- Identify the daily focus/theme

**By Type**:
- Count types: X features, Y fixes, Z refactorings
- Identify what phase project is in (heavy development, stabilization, maintenance)

### Pattern Recognition

Look for:
- **Burst activity**: Many commits in short time (sprint? deadline?)
- **Iterative work**: Multiple commits on same file/feature (refinement)
- **Bug fix cycles**: Commit → fix → another fix (indicates complexity or rushing)
- **Refactoring waves**: Series of refactor commits (code health focus)

## THEME IDENTIFICATION

For each day/period, identify the **focus** in one phrase:

Good examples:
- "Authentication system implementation"
- "Performance optimization and caching"
- "Bug fixes and stabilization"
- "Database migration and schema updates"
- "Documentation improvements"
- "Dependency updates and security patches"

Bad examples (too vague):
- "Various changes"
- "Improvements"
- "Updates"

## NEXT STEPS INFERENCE

### From Recent Work

If recent commits show:
- Incomplete feature → Suggest completing it
- New component → Suggest testing/documentation
- Refactoring → Suggest continuing or applying to other areas
- Bug fixes → Suggest regression tests

### From Code Analysis (if available)

- TODO comments → Add to Next Steps
- FIXME comments → Add to Technical Debt
- Placeholder code → Suggest implementation

### From Patterns

- If many features lately → Suggest stabilization/testing
- If many refactorings → Suggest new features (code health restored)
- If many fixes → Suggest systematic testing or architecture review

## CRITICAL RULES

1. **BE OBJECTIVE**:
   - Base on actual commits, not speculation
   - Use commit messages as primary source
   - Don't invent context not present

2. **FIND PATTERNS**:
   - Don't just list commits - find themes
   - Group related work together
   - Identify development phases

3. **BE CONCISE**:
   - Summarize, don't repeat every commit message
   - Group similar commits: "Fixed 3 validation bugs" not listing each
   - Focus on **what** was done, not **how** (that's in commits)

4. **FORWARD-LOOKING**:
   - Next Steps should be actionable
   - Base on recent trajectory
   - Be realistic (don't suggest moonshots)

5. **HONEST ASSESSMENT**:
   - If project is in flux, say so
   - If lots of fixes, acknowledge stability work needed
   - If progressing well, note that too

## OUTPUT FORMAT

Provide ONLY the complete whereiwas.md content in Markdown format.
Do NOT include explanations or meta-commentary.
Start directly with the content.

## EXAMPLE (adapt to actual project):

```markdown
# Development Journal

**Last Updated**: 2025-11-25
**Branch**: main
**Status**: Active development

## Current State

Primary focus is on implementing automated documentation generation system.
Recent work has concentrated on hash-based change detection to optimize
LLM API usage. System is functional but undergoing active refinement.

---

## 2025-11-24

**Focus**: Documentation architecture and planning

### Changes
- Designed comprehensive docs/ structure following Diataxis methodology
- Implemented AST analyzer for code metadata extraction
- Created LLM templates for various documentation types

**Commits**: 3b9d917, ac0a07e

---

## 2025-11-23

**Focus**: Change detection improvements

### Changes
- Implemented independent change detection for class and method levels
- Fixed critical bugs in hash storage and retrieval
- Added validation for marker name extraction

**Commits**: ad58bc8, c2b4dbd, e3fce3e

---

## Development Patterns

### Primary Activities
1. **Refactoring** (15 commits): Extensive code cleanup and consolidation
2. **Feature Development** (12 commits): New marker types and detection logic
3. **Bug Fixes** (8 commits): Stability improvements and edge case handling

### Key Milestones
- **2025-11-17**: Multiple marker type support implemented
- **2025-11-20**: Hash-based change detection functional
- **2025-11-24**: Documentation system architecture designed

### Technical Debt Addressed
- Eliminated duplicate task creation logic
- Centralized constant definitions
- Unified database schema (removed separate DBs)

---

## Next Steps

### Immediate
- [ ] Complete DocsGenerator implementation
- [ ] Integrate with CLI sync command
- [ ] Add @llm-module markers to all source files

### Planned
- [ ] Test complete workflow (sync → process → review → apply → docs)
- [ ] Validate generated documentation structure
- [ ] Implement incremental doc regeneration

### Technical Debt
- [ ] Add comprehensive test coverage
- [ ] Document internal APIs
- [ ] Performance profiling for large projects
```

## QUALITY CHECKS

Before finalizing, verify:
- [ ] All dates have identified focus/theme
- [ ] Patterns are evident (not just listed)
- [ ] Next steps are concrete and actionable
- [ ] Based on actual commits (not speculation)
- [ ] Tone is professional but human
- [ ] Useful for both original author and new contributors

---

Now analyze the git history and generate whereiwas.md.