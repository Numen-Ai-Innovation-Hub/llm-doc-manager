"""
Command-line interface for LLM Doc Manager.

Provides interactive commands for scanning, processing, and applying documentation changes.
"""

import click
import sys
import json
import traceback
from pathlib import Path
from typing import Optional

from .config import Config, ConfigManager, LLMConfig
from .queue import QueueManager, TaskStatus
from .scanner import Scanner
from .processor import Processor, ProcessResult
from .applier import Applier, Suggestion
from .hashing import HashStorage
from .detector import ChangeDetector
from .generator import DocsGenerator
from .constants import TASK_TYPE_LABELS
from .database import DatabaseManager
from ..utils.marker_validator import MarkerValidator, ValidationLevel
from ..utils.llm_client import LLMClientFactory
from ..utils.logger_setup import LoggerManager
from ..utils.response_schemas import (
    ModuleDocstring,
    ClassDocstring,
    MethodDocstring,
    ValidationResult
)
from ..utils.review_formatter import format_task_for_review


def _get_hierarchical_blocks(changed_names: set, blocks: list) -> list:
    """
    Get all blocks that should have tasks created based on hierarchical changes.

    When a child element changes, all parent elements should also have tasks created:
    - COMMENT change → include METHOD, CLASS, MODULE parents
    - METHOD change → include CLASS, MODULE parents
    - CLASS change → include MODULE parent
    - MODULE change → only MODULE itself

    Args:
        changed_names: Set of scope names that changed (from detect_changes)
        blocks: List of all DetectedBlock objects

    Returns:
        List of blocks that should have tasks created (including parents)
    """
    # Use set to avoid duplicates, then convert to list
    blocks_to_process_set = set()

    # First pass: collect all directly changed blocks
    changed_blocks = []
    for block in blocks:
        if block.function_name in changed_names:
            blocks_to_process_set.add(id(block))  # Use object id as unique identifier
            changed_blocks.append(block)

    # Second pass: find all parent blocks
    # A parent contains a child if its line range fully encompasses the child's range
    for block in blocks:
        # Skip if already included as directly changed
        if id(block) in blocks_to_process_set:
            continue

        # Check if this block is a parent of any changed block
        for changed_block in changed_blocks:
            # Parent must contain child's entire range AND be a different block
            is_parent = (
                block.start_line <= changed_block.start_line and
                block.end_line >= changed_block.end_line and
                # Ensure it's not the same block (compare line ranges)
                not (block.start_line == changed_block.start_line and
                     block.end_line == changed_block.end_line)
            )

            if is_parent:
                blocks_to_process_set.add(id(block))
                # Once identified as parent, no need to check other children
                break

    # Return blocks in original order (preserve file order)
    return [block for block in blocks if id(block) in blocks_to_process_set]


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """LLM Documentation Manager - Automated documentation validation and generation."""
    LoggerManager.setup_logging(console=True)


@cli.command()
@click.option('--overwrite', is_flag=True, help='Overwrite existing configuration')
def init(overwrite):
    """Initialize configuration in current directory."""
    config_manager = ConfigManager()

    if config_manager.init_config(overwrite=overwrite):
        click.echo("✓ Configuration initialized successfully")
        click.echo(f"  Config file: {config_manager.config_file}")
        click.echo("\nNext steps:")
        click.echo("  1. Edit config file to set your LLM API key")
        click.echo("  2. Run 'llm-doc-manager sync' to detect changes and create tasks")
    else:
        click.echo("Configuration already exists. Use --overwrite to replace it.")


@cli.command()
@click.option('--path', multiple=True, help='Paths to scan (can specify multiple)')
@click.option('--force', is_flag=True, help='Force rescan even if files are unchanged')
def sync(path, force):
    """Sync markers with hash-based change detection and create tasks."""

    try:
        # Load config
        config_manager = ConfigManager()
        config = config_manager.load()

        # Override config with command-line options
        if path:
            config.scanning.paths = list(path)

        # Initialize components
        queue_manager = QueueManager()
        scanner = Scanner(config)
        validator = MarkerValidator()

        # Check for pending tasks before sync (unless --force)
        if not force:
            pending_tasks = queue_manager.get_pending_tasks()
            if pending_tasks:
                click.echo(f"⚠️  Cannot sync: {len(pending_tasks)} pending task(s) in queue")
                click.echo("\nPlease complete the current workflow first:")
                click.echo("  1. Run 'llm-doc-manager process' to generate suggestions")
                click.echo("  2. Run 'llm-doc-manager review' to review suggestions")
                click.echo("  3. Run 'llm-doc-manager apply' to apply accepted changes")
                click.echo("\nOr use --force to ignore pending tasks, or clear with 'llm-doc-manager clear'")
                sys.exit(1)

        # Initialize hash storage
        db_path = Path.cwd() / '.llm-doc-manager' / 'llm_doc_manager.db'
        storage = HashStorage(str(db_path))
        detector = ChangeDetector(storage)

        # Step 1: Scan for markers
        click.echo("🔍 Scanning project for documentation markers...")
        scan_result = scanner.scan()

        # Display validation issues first (if any)
        if scan_result.validation_issues:
            errors = [i for i in scan_result.validation_issues if i.level == ValidationLevel.ERROR]
            warnings = [i for i in scan_result.validation_issues if i.level == ValidationLevel.WARNING]

            if errors:
                click.echo(f"\n❌ Validation Errors ({len(errors)}):")
                for issue in errors:
                    click.echo(f"  {issue}")
                click.echo("\n⚠️  Fix these errors before processing.")
                sys.exit(1)

            if warnings:
                click.echo(f"\n⚠️  Validation Warnings ({len(warnings)}):")
                for issue in warnings:
                    click.echo(f"  {issue}")
                click.echo("\n💡 Warnings don't block processing, but should be reviewed.")

        click.echo(f"  Files scanned: {scan_result.files_scanned}")
        click.echo(f"  Blocks found: {scan_result.blocks_found}")

        if scan_result.errors:
            click.echo(f"\n⚠ Scan errors: {len(scan_result.errors)}")
            for error in scan_result.errors[:5]:
                click.echo(f"  - {error}")

        # Step 2: Process files with validation results saved to database
        click.echo("\n🔄 Detecting changes and creating tasks...")

        tasks_created = 0
        files_with_changes = 0
        token_savings = 0

        for file_path, blocks in scan_result.file_blocks.items():
            if not blocks:
                continue

            # Check if file has validation issues (already checked above, this is per-file)
            file_issues = [i for i in scan_result.validation_issues if i.file_path == file_path]
            has_errors = any(i.level == ValidationLevel.ERROR for i in file_issues)

            if has_errors:
                # Skip files with validation errors
                continue

            # Detect changes (returns tuple: LIST of reports and current_hashes)
            change_reports, current_hashes = detector.detect_changes(file_path, blocks)

            # Check if there are any real changes (skip NONE scope)
            has_changes = any(report.scope != 'NONE' for report in change_reports) or force

            if not has_changes:
                # No changes - don't create tasks
                click.echo(f"  ⊘ {file_path} - {change_reports[0].reason}")
                # Estimate token savings (assuming ~500 tokens per block)
                token_savings += len(blocks) * 500
                continue

            files_with_changes += 1

            # Read file content for validator
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                click.echo(f"  ❌ Error reading {file_path}: {e}")
                continue

            # Save validation results to database (pass blocks to avoid re-detection)
            validator.save_validation_results(str(file_path), content, file_issues, blocks)

            # Collect all changed names from all reports to avoid duplicates
            all_changed_names = set()
            for report in change_reports:
                if report.scope != 'NONE':
                    all_changed_names.update(report.changed_items + report.new_items)

            # Display change summary
            if force:
                click.echo(f"  🔄 {file_path} - Forced rescan")
            else:
                for change_report in change_reports:
                    if change_report.scope == 'NONE':
                        continue
                    elif change_report.scope == 'FILE':
                        click.echo(f"  📄 {file_path} - New file")
                    elif change_report.scope == 'MODULE':
                        changed_names = set(change_report.changed_items + change_report.new_items)
                        click.echo(f"  📦 {file_path} - {change_report.reason}:")
                        for name in sorted(changed_names):
                            click.echo(f"     {name}")
                    elif change_report.scope == 'CLASS':
                        changed_names = set(change_report.changed_items + change_report.new_items)
                        click.echo(f"  🔹 {file_path} - {change_report.reason}:")
                        for name in sorted(changed_names):
                            click.echo(f"     {name}")
                    elif change_report.scope == 'METHOD':
                        changed_names = set(change_report.changed_items + change_report.new_items)
                        click.echo(f"  🔸 {file_path} - {change_report.reason}:")
                        for name in sorted(changed_names):
                            click.echo(f"     {name}")
                    elif change_report.scope == 'COMMENT':
                        changed_names = set(change_report.changed_items + change_report.new_items)
                        click.echo(f"  💬 {file_path} - {change_report.reason}:")
                        for name in sorted(changed_names):
                            click.echo(f"     {name}")

            # Create tasks using MarkerValidator (if force OR new file, create all tasks)
            if force or any(r.scope == 'FILE' for r in change_reports):
                # Create tasks for ALL blocks (pass blocks to avoid re-detection)
                file_tasks = validator.create_tasks_from_validation(str(file_path), blocks)
                tasks_created += file_tasks
                # No token savings when processing all blocks
            else:
                # Create tasks for changed blocks AND their hierarchical parents
                changed_blocks = _get_hierarchical_blocks(all_changed_names, blocks)
                file_tasks = validator.create_tasks_from_validation(str(file_path), changed_blocks)
                tasks_created += file_tasks

                # Calculate token savings for blocks that won't be processed
                # This includes blocks that didn't change AND are not parents of changed blocks
                processed_block_ids = {id(block) for block in changed_blocks}
                for block in blocks:
                    if id(block) not in processed_block_ids:
                        token_savings += 500

            # Update stored hashes after creating tasks (reuse calculated hashes)
            detector.update_stored_hashes(file_path, current_hashes)

        # Display summary
        click.echo(f"\n✓ Sync complete!")
        click.echo(f"  Files with changes: {files_with_changes}/{scan_result.files_scanned}")
        click.echo(f"  Tasks created: {tasks_created}")

        if token_savings > 0:
            click.echo(f"  💰 Estimated token savings: ~{token_savings:,} tokens (unchanged blocks)")

        if tasks_created > 0:
            click.echo(f"\nNext: Run 'llm-doc-manager process' to generate suggestions")
        else:
            click.echo("\nNo changes detected. All documentation is up to date!")

            # Natural sequence: If queue is empty (no pending tasks), check docs
            # This happens after apply when all marker-based docs are complete
            pending_count = len(queue_manager.get_pending_tasks())
            if pending_count == 0:
                click.echo("\n📚 Queue is empty. Checking if documentation generation is needed...")

                try:
                    # Initialize components for docs generation
                    db_manager = DatabaseManager()

                    # Strategy: Use different LLM providers for different tasks
                    # - OpenAI (gpt-4o-mini): Fast and cheap for inline docstrings/comments
                    # - Anthropic (claude-3-7-sonnet): 1M context window for comprehensive docs

                    # Processor uses OpenAI config (fast for docstrings/comments)
                    # Config already initialized with OpenAI provider from .env
                    processor = Processor(config, queue_manager)

                    # DocsGenerator uses Anthropic config (large context for comprehensive docs)
                    config_docs = Config(llm=LLMConfig(provider="anthropic"))
                    api_key_docs = config_manager.get_api_key(config_docs)

                    llm_client_docs = LLMClientFactory.create(
                        provider=config_docs.llm.provider,
                        model=config_docs.llm.model,
                        api_key=api_key_docs,
                        base_url=config_docs.llm.base_url,
                        temperature=config_docs.llm.temperature,
                        max_tokens=config_docs.llm.max_tokens
                    )

                    docs_generator = DocsGenerator(
                        config=config_docs,
                        db=db_manager,
                        detector=detector,
                        llm_client=llm_client_docs
                    )

                    # Check if docs need regeneration (incremental)
                    if not force:
                        docs_changes = detector.detect_docs_changes(
                            project_root=config_docs.project_root,
                            db_connection=db_manager.get_connection()
                        )

                        if not docs_changes["docs_changed"]:
                            click.echo("✓ Documentation is up to date. No changes detected in source files.")
                            click.echo(f"  📂 Documentation available at: docs/")
                            # Skip generation - all docs are current
                            return

                        # Show what needs updating
                        click.echo("📝 Changes detected. Documentation needs updating:")
                        if docs_changes["readme"]:
                            click.echo("  • readme.md")
                        if docs_changes["architecture"]:
                            click.echo("  • architecture.md")
                        if docs_changes["glossary"]:
                            click.echo("  • glossary.md")
                        if docs_changes["whereiwas"]:
                            click.echo("  • whereiwas.md")
                        if docs_changes["modules"]:
                            click.echo(f"  • {len(docs_changes['modules'])} module docs")

                    # Generate documentation (force or changes detected)
                    click.echo("\n🔄 Generating project documentation...")
                    result = docs_generator.generate_all_docs(force=force)

                    # Display results
                    if result["generated_files"]:
                        click.echo(f"\n✓ Documentation generated!")
                        click.echo(f"  Generated: {len(result['generated_files'])} files")
                        for file_path in result["generated_files"][:10]:  # Show first 10
                            click.echo(f"    ✓ {file_path}")
                        if len(result["generated_files"]) > 10:
                            click.echo(f"    ... and {len(result['generated_files']) - 10} more")

                    if result["skipped_files"]:
                        click.echo(f"  Skipped (up to date): {len(result['skipped_files'])} files")

                    if result["errors"]:
                        click.echo(f"\n⚠️  Generation errors ({len(result['errors'])}):")
                        for error in result["errors"][:5]:
                            click.echo(f"    ❌ {error}")

                    click.echo(f"\n📂 Documentation available at: docs/")
                    click.echo(f"  📖 Start with: docs/readme.md or docs/index.md")

                except Exception as doc_error:
                    click.echo(f"\n⚠️  Documentation generation failed: {doc_error}")
                    click.echo("   (This does not affect marker-based documentation)")
                    # Don't fail the entire sync command
                    pass

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        traceback.print_exc()
        sys.exit(1)



@cli.command()
@click.option('--limit', type=int, help='Maximum number of tasks to process')
def process(limit):
    """Process pending documentation tasks with LLM."""
    try:
        # Load config
        config_manager = ConfigManager()
        config = config_manager.load()

        # Validate config
        errors = config_manager.validate(config)
        if errors:
            click.echo("❌ Configuration errors:")
            for error in errors:
                click.echo(f"  - {error}")
            sys.exit(1)

        # Initialize components
        queue_manager = QueueManager()
        processor = Processor(config, queue_manager)

        # Get pending tasks
        pending = queue_manager.get_pending_tasks(limit=limit)

        if not pending:
            click.echo("No pending tasks found. Run 'llm-doc-manager sync' first.")
            return

        click.echo(f"🤖 Processing {len(pending)} task(s)...\n")

        # Process tasks
        total_tokens = 0
        successful = 0
        failed = 0

        with click.progressbar(pending, label='Processing tasks') as tasks:
            for task in tasks:
                result = processor.process_task(task)

                if result.success:
                    successful += 1
                    total_tokens += result.tokens_used
                else:
                    failed += 1

        # Display summary
        click.echo(f"\n✓ Processing complete!")
        click.echo(f"  Successful: {successful}")
        click.echo(f"  Failed: {failed}")
        click.echo(f"  Total tokens used: {total_tokens:,}")

        if successful > 0:
            click.echo(f"\nSuggestions saved to database")
            click.echo(f"Next: Run 'llm-doc-manager review' to review suggestions")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        traceback.print_exc()
        sys.exit(1)


def _sort_tasks_hierarchically(tasks):
    """
    Sort tasks by FILE > MODULE > CLASS > METHOD > COMMENT hierarchy.

    Sorting order:
    1. file_path (ASC) - group by file
    2. task_type hierarchy - MODULE > CLASS > METHOD > COMMENT
    3. line_number (ASC) - line order within file

    Args:
        tasks: List of DocTask objects

    Returns:
        Sorted list of DocTask objects
    """
    # Define hierarchy order
    TYPE_HIERARCHY = {
        'generate_module': 1,
        'validate_module': 2,
        'generate_class': 3,
        'validate_class': 4,
        'generate_docstring': 5,
        'validate_docstring': 6,
        'generate_comment': 7,
        'validate_comment': 8,
    }

    def sort_key(task):
        return (
            task.file_path,                          # Primary: group by file
            TYPE_HIERARCHY.get(task.task_type, 99),  # Secondary: hierarchy
            task.line_number                         # Tertiary: line order
        )

    return sorted(tasks, key=sort_key)


@cli.command()
def review():
    """Review and accept/reject suggestions interactively."""
    try:
        # Load config
        config_manager = ConfigManager()
        config = config_manager.load()

        # Initialize components
        queue_manager = QueueManager()

        # Get completed tasks
        completed = queue_manager.get_tasks_by_status(TaskStatus.COMPLETED)

        # Sort hierarchically: FILE > MODULE > CLASS > METHOD > COMMENT
        completed = _sort_tasks_hierarchically(completed)

        if not completed:
            click.echo("No suggestions to review. Run 'llm-doc-manager process' first.")
            return

        click.echo(f"📋 Reviewing {len(completed)} suggestion(s)\n")

        accepted = []
        skipped = []
        dismissed = []

        for i, task in enumerate(completed, 1):
            click.echo(f"{'='*60}")
            # Build header
            click.echo(f"[{i}/{len(completed)}] {task.file_path}:{task.line_number}")
            # Show human-readable type label
            type_label = TASK_TYPE_LABELS.get(task.task_type, task.task_type)
            click.echo(f"Type: {type_label}")
            if task.scope_name:
                click.echo(f"Name: {task.scope_name}")

            # Get suggestion from task (stored in database)
            if task.suggestion:
                # Format structured output for human-readable display
                formatted_output = format_task_for_review(task)
                click.echo(formatted_output)
            click.echo(f"{'='*60}")

                # Get user choice
                choice = click.prompt(
                    "\n[a]ccept, [s]kip, [d]ismiss, [q]uit",
                    type=click.Choice(['a', 's', 'd', 'q'], case_sensitive=False),
                    default='a'
                )

                if choice == 'a':
                    accepted.append(task)
                    queue_manager.accept_task(task.id)
                    click.echo("✓ Accepted\n")
                elif choice == 's':
                    skipped.append(task)
                    click.echo("⊘ Skipped\n")
                elif choice == 'd':
                    dismissed.append(task)
                    queue_manager.update_task_status(task.id, TaskStatus.SKIPPED)
                    click.echo("✗ Dismissed\n")
                elif choice == 'q':
                    click.echo("Exiting review...")
                    break
            else:
                click.echo("⚠ No suggestion found for this task\n")
                skipped.append(task)

        # Summary
        click.echo(f"\n{'='*60}")
        click.echo("Review Summary:")
        click.echo(f"  Accepted: {len(accepted)}")
        click.echo(f"  Skipped: {len(skipped)}")
        click.echo(f"  Dismissed: {len(dismissed)}")

        # Accepted tasks are now marked in database
        if accepted:
            click.echo(f"\nNext: Run 'llm-doc-manager apply' to apply accepted changes")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
def apply():
    """Apply accepted suggestions to files."""
    try:
        # Load config
        config_manager = ConfigManager()
        config = config_manager.load()

        # Initialize components
        queue_manager = QueueManager()
        applier = Applier(config, queue_manager)
        scanner = Scanner(config)

        # Initialize hash storage for updating after apply
        db_path = Path.cwd() / '.llm-doc-manager' / 'llm_doc_manager.db'
        storage = HashStorage(str(db_path))
        detector = ChangeDetector(storage)

        # Get accepted tasks from database
        accepted_tasks = queue_manager.get_accepted_tasks()

        if not accepted_tasks:
            click.echo("No accepted suggestions found. Run 'llm-doc-manager review' first.")
            return

        click.echo(f"📝 Applying {len(accepted_tasks)} suggestion(s)...\n")

        applied = 0
        failed = 0
        modified_files = set()  # Track which files were modified

        for task in accepted_tasks:
            if not task.suggestion:
                click.echo(f"⚠ {task.file_path}:{task.line_number} - No suggestion")
                failed += 1
                continue

            # Deserialize suggestion from database (may be JSON string or plain string)
            suggested_text = task.suggestion

            # If it's a JSON string, parse it back to Pydantic object
            if task.task_type == "generate_module":
                try:
                    parsed = json.loads(task.suggestion)
                    suggested_text = ModuleDocstring(**parsed)
                except (json.JSONDecodeError, TypeError):
                    # Already a string (old format or validate_* task)
                    pass
            elif task.task_type == "generate_class":
                try:
                    parsed = json.loads(task.suggestion)
                    suggested_text = ClassDocstring(**parsed)
                except (json.JSONDecodeError, TypeError):
                    pass
            elif task.task_type == "generate_docstring":
                try:
                    parsed = json.loads(task.suggestion)
                    suggested_text = MethodDocstring(**parsed)
                except (json.JSONDecodeError, TypeError):
                    pass
            # Handle validate_* tasks (ValidationResult JSON)
            elif task.task_type.startswith("validate_"):
                try:
                    parsed = json.loads(task.suggestion)
                    validation_result = ValidationResult(**parsed)
                    # Extract improved_content for actual file modification
                    suggested_text = validation_result.improved_content or ""
                except (json.JSONDecodeError, TypeError):
                    # Fallback for legacy format (plain strings)
                    pass
            # For generate_comment, keep as string

            # Create suggestion object
            suggestion = Suggestion(
                task_id=task.id,
                file_path=task.file_path,
                line_number=task.line_number,
                original_text=task.marker_text,
                suggested_text=suggested_text,
                task_type=task.task_type
            )

            # Apply
            if applier.apply_suggestion(suggestion):
                click.echo(f"✓ {task.file_path}:{task.line_number}")
                applied += 1
                modified_files.add(task.file_path)
                # Auto-delete applied task from queue
                queue_manager.delete_task(task.id)
            else:
                click.echo(f"✗ {task.file_path}:{task.line_number}")
                failed += 1

        click.echo(f"\n✓ Applied {applied} change(s)")
        if failed:
            click.echo(f"✗ Failed to apply {failed} change(s)")

        # Update hashes for modified files to prevent re-detection
        if modified_files:
            click.echo(f"\n🔄 Updating content hashes for {len(modified_files)} file(s)...")
            for file_path in modified_files:
                try:
                    # Re-scan the file to get updated blocks
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    blocks = scanner.marker_detector.detect_blocks(content, file_path)

                    # Recalculate and update hashes
                    from ..utils.content_hash import ContentHasher
                    current_hashes = ContentHasher.calculate_all_hashes(file_path, blocks)
                    detector.update_stored_hashes(file_path, current_hashes)

                except Exception as e:
                    click.echo(f"⚠ Warning: Could not update hashes for {file_path}: {e}")

        if config.output.backup:
            click.echo(f"\nBackups saved to: {config.output.backup_dir}")
            click.echo("To rollback: llm-doc-manager rollback <file>")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
def status():
    """Show queue status and statistics."""
    try:
        queue_manager = QueueManager()
        stats = queue_manager.get_stats()

        click.echo("📊 Queue Status\n")
        click.echo(f"  Total tasks: {stats.get('total', 0)}")
        click.echo(f"  Pending: {stats.get('pending', 0)}")
        click.echo(f"  Processing: {stats.get('processing', 0)}")
        click.echo(f"  Completed: {stats.get('completed', 0)}")
        click.echo(f"  Failed: {stats.get('failed', 0)}")
        click.echo(f"  Skipped: {stats.get('skipped', 0)}")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
def clear():
    """Clear all tasks from the queue."""
    try:
        queue_manager = QueueManager()

        if click.confirm("Clear ALL tasks from queue?"):
            queue_manager.clear_all()
            click.echo("✓ Cleared all tasks")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--file-path', required=True, help='File path to rollback')
def rollback(file_path):
    """Rollback a file to its last backup."""
    try:
        config_manager = ConfigManager()
        config = config_manager.load()

        queue_manager = QueueManager()
        applier = Applier(config, queue_manager)

        if applier.rollback(file_path):
            click.echo(f"✓ Rolled back: {file_path}")
            click.echo("⚠ Run 'llm-doc-manager sync' to update content hashes")
        else:
            click.echo(f"✗ Could not rollback: {file_path}")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
def cleanup():
    """Remove configuration directory (.llm-doc-manager)."""
    try:
        config_manager = ConfigManager()

        if click.confirm("⚠️  This will delete the entire .llm-doc-manager directory. Continue?"):
            if config_manager.cleanup():
                click.echo("✓ Cleanup complete")
                click.echo("\nYou can now safely uninstall the package:")
                click.echo("  pip uninstall llm-doc-manager -y")
            else:
                click.echo("✗ Cleanup failed - configuration directory not found or could not be deleted")
                click.echo(f"  Directory: {config_manager.config_dir}")
                sys.exit(1)

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


def main():
    """Main entry point."""
    cli()


if __name__ == '__main__':
    main()
