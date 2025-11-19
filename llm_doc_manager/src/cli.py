"""
Command-line interface for LLM Doc Manager.

Provides interactive commands for scanning, processing, and applying documentation changes.
"""

import click
import sys
import traceback
from pathlib import Path
from typing import Optional

from .config import Config, ConfigManager
from .queue import QueueManager, TaskStatus, DocTask
from .scanner import Scanner
from .processor import Processor, ProcessResult
from .applier import Applier, Suggestion
from .hashing import HashStorage
from .detector import ChangeDetector
from ..utils.marker_validator import MarkerValidator, ValidationLevel


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """LLM Documentation Manager - Automated documentation validation and generation."""
    pass


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
def sync(path):
    """Sync markers with hash-based change detection and create tasks."""

    def get_task_type_from_marker(marker_type_value):
        """Map marker type to processor task type."""
        marker_to_task = {
            'docstring': 'generate_docstring',
            'class_doc': 'generate_class',
            'comment': 'generate_comment'
        }
        return marker_to_task.get(marker_type_value, 'generate_docstring')

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

        # Check for pending tasks before sync
        pending_tasks = queue_manager.get_pending_tasks()
        if pending_tasks:
            click.echo(f"⚠️  Cannot sync: {len(pending_tasks)} pending task(s) in queue")
            click.echo("\nPlease complete the current workflow first:")
            click.echo("  1. Run 'llm-doc-manager process' to generate suggestions")
            click.echo("  2. Run 'llm-doc-manager review' to review suggestions")
            click.echo("  3. Run 'llm-doc-manager apply' to apply accepted changes")
            click.echo("\nOr clear the queue with 'llm-doc-manager clear' to start fresh")
            sys.exit(1)

        # Initialize hash storage
        db_path = Path.cwd() / '.llm-doc-manager' / 'content_hashes.db'
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

        # Step 2: Detect changes using hash comparison
        click.echo("\n🔄 Detecting changes using content hashes...")

        tasks_created = 0
        files_with_changes = 0
        token_savings = 0

        for file_path, blocks in scan_result.file_blocks.items():
            if not blocks:
                continue

            # Detect changes (returns tuple: report and current_hashes)
            change_report, current_hashes = detector.detect_changes(file_path, blocks)

            if change_report.scope == 'NONE':
                # No changes - don't create tasks
                click.echo(f"  ⊘ {file_path} - {change_report.reason}")
                # Estimate token savings (assuming ~500 tokens per block)
                token_savings += len(blocks) * 500
                continue

            files_with_changes += 1

            # Display change summary
            if change_report.scope == 'FILE':
                click.echo(f"  📄 {file_path} - New file, all blocks will be processed")
                # Create tasks for all blocks
                for block in blocks:
                    task = DocTask(
                        file_path=file_path,
                        line_number=block.start_line,
                        task_type=get_task_type_from_marker(block.marker_type.value),
                        marker_text=block.marker_type.value,
                        context=block.full_code,
                        priority=1,
                        scope_name=block.function_name
                    )
                    queue_manager.add_task(task)
                    tasks_created += 1

            elif change_report.scope == 'CLASS':
                # Show specific class names in message
                changed_names = set(change_report.changed_items + change_report.new_items)
                click.echo(f"  🔹 {file_path} - {change_report.reason}:")
                for name in sorted(changed_names):
                    click.echo(f"     {name}")
                # Create tasks for changed/new classes
                for block in blocks:
                    # function_name is used for both functions AND classes
                    block_name = block.function_name
                    if block_name in changed_names:
                        task = DocTask(
                            file_path=file_path,
                            line_number=block.start_line,
                            task_type=get_task_type_from_marker(block.marker_type.value),
                            marker_text=block.marker_type.value,
                            context=block.full_code,
                            priority=2,
                            scope_name=block.function_name
                        )
                        queue_manager.add_task(task)
                        tasks_created += 1
                    else:
                        token_savings += 500

            elif change_report.scope == 'METHOD':
                # Show specific method names in message
                changed_names = set(change_report.changed_items + change_report.new_items)
                click.echo(f"  🔸 {file_path} - {change_report.reason}:")
                for name in sorted(changed_names):
                    click.echo(f"     {name}")
                # Create tasks for changed/new methods
                for block in blocks:
                    # function_name is used for both functions AND classes
                    block_name = block.function_name
                    if block_name in changed_names:
                        task = DocTask(
                            file_path=file_path,
                            line_number=block.start_line,
                            task_type=get_task_type_from_marker(block.marker_type.value),
                            marker_text=block.marker_type.value,
                            context=block.full_code,
                            priority=3,
                            scope_name=block.function_name
                        )
                        queue_manager.add_task(task)
                        tasks_created += 1
                    else:
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
            click.echo(f"Type: {task.task_type}")
            if task.scope_name:
                click.echo(f"Name: {task.scope_name}")
            click.echo(f"{'='*60}")

            # Get suggestion from task (stored in database)
            if task.suggestion:
                # Clean suggestion text (remove quotes if LLM included them)
                suggestion_text = task.suggestion.strip().strip('"""').strip("'''").strip()

                click.echo("\nSuggested change:")
                click.echo("-" * 60)
                click.echo(suggestion_text)  # Show cleaned suggestion
                click.echo("-" * 60)

                # Get user choice
                choice = click.prompt(
                    "\n[a]ccept, [s]kip, [d]ismiss, [q]uit",
                    type=click.Choice(['a', 's', 'd', 'q'], case_sensitive=False),
                    default='a'
                )

                if choice == 'a':
                    accepted.append((task, suggestion_text))
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
        db_path = Path.cwd() / '.llm-doc-manager' / 'content_hashes.db'
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

            # Create suggestion object
            suggestion = Suggestion(
                task_id=task.id,
                file_path=task.file_path,
                line_number=task.line_number,
                original_text=task.marker_text,
                suggested_text=task.suggestion,
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
                sys.exit(1)

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


def main():
    """Main entry point."""
    cli()


if __name__ == '__main__':
    main()