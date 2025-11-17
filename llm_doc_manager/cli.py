"""
Command-line interface for LLM Doc Manager.

Provides interactive commands for scanning, processing, and applying documentation changes.
"""

import click
import sys
from pathlib import Path
from typing import Optional

from .config import Config, ConfigManager
from .queue import QueueManager, TaskStatus
from .scanner import Scanner
from .processor import Processor, ProcessResult
from .applier import Applier, Suggestion


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
        click.echo("  2. Run 'llm-doc-manager scan' to find documentation tasks")
    else:
        click.echo("Configuration already exists. Use --overwrite to replace it.")


@cli.command()
@click.option('--path', multiple=True, help='Paths to scan (can specify multiple)')
def scan(path):
    """Scan files for documentation markers."""
    try:
        # Load config
        config_manager = ConfigManager()
        config = config_manager.load()

        # Override config with command-line options
        if path:
            config.scanning.paths = list(path)

        # Initialize components
        queue_manager = QueueManager()
        scanner = Scanner(config, queue_manager)

        # Perform scan
        click.echo("🔍 Scanning project for documentation markers...")
        result = scanner.scan()

        # Display results
        click.echo(f"\n✓ Scan complete!")
        click.echo(f"  Files scanned: {result.files_scanned}")
        click.echo(f"  Tasks created: {result.tasks_created}")

        if result.errors:
            click.echo(f"\n⚠ Errors encountered: {len(result.errors)}")
            for error in result.errors[:5]:  # Show first 5 errors
                click.echo(f"  - {error}")

        if result.tasks_created > 0:
            click.echo(f"\nNext: Run 'llm-doc-manager process' to generate suggestions")
        else:
            click.echo("\nNo markers found. Add markers to your code and scan again.")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
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
            click.echo("No pending tasks found. Run 'llm-doc-manager scan' first.")
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
        import traceback
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
            click.echo(f"[{i}/{len(completed)}] {task.file_path}:{task.line_number}")
            click.echo(f"Type: {task.task_type}")
            click.echo(f"{'='*60}")

            # Get suggestion from task (stored in database)
            if task.suggestion:
                suggestion_text = task.suggestion

                click.echo("\nSuggested change:")
                click.echo("-" * 60)
                click.echo(suggestion_text)  # Show full suggestion
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
                modified_files.add(task.file_path)  # Track modified file
                # Auto-delete applied task from queue
                queue_manager.delete_task(task.id)
            else:
                click.echo(f"✗ {task.file_path}:{task.line_number}")
                failed += 1

        # Remove all markers from modified files (final cleanup pass)
        if modified_files:
            click.echo(f"\n🧹 Cleaning up markers from {len(modified_files)} file(s)...")
            for file_path in modified_files:
                if applier.remove_all_markers(file_path):
                    click.echo(f"  ✓ Removed markers from {file_path}")
                else:
                    click.echo(f"  ⚠ Could not remove markers from {file_path}")

        click.echo(f"\n✓ Applied {applied} change(s)")
        if failed:
            click.echo(f"✗ Failed to apply {failed} change(s)")

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