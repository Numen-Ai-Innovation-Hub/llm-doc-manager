"""
LLM Processor for generating and validating documentation.

Handles communication with LLM providers to generate, validate, and improve documentation.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass

from .config import Config, ConfigManager
from .queue import DocTask, QueueManager, TaskStatus
from .constants import TASK_PROCESSING_ORDER
from ..utils.docstring_handler import extract_docstring
from ..utils.logger_setup import get_logger
from ..utils.llm_client import LLMClientFactory
from ..utils.response_schemas import (
    ModuleDocstring,
    ClassDocstring,
    MethodDocstring,
    CommentText,
    ValidationResult
)

logger = get_logger(__name__)


# Mapping task_type -> Pydantic schema for Structured Outputs
TASK_SCHEMAS = {
    "generate_module": ModuleDocstring,
    "generate_class": ClassDocstring,
    "generate_docstring": MethodDocstring,
    "generate_comment": CommentText,
    "validate_module": ValidationResult,
    "validate_class": ValidationResult,
    "validate_docstring": ValidationResult,
    "validate_comment": ValidationResult,
}


@dataclass
class ProcessResult:
    """Result of processing a documentation task."""
    task_id: int
    success: bool
    suggestion: Optional[str] = None
    error: Optional[str] = None
    tokens_used: int = 0


class Processor:
    """Processes documentation tasks using LLM."""

    def __init__(self, config: Config, queue_manager: QueueManager):
        """
        Initialize Processor.

        Args:
            config: Configuration object
            queue_manager: Queue manager for updating task status
        """
        self.config = config
        self.queue_manager = queue_manager

        # Inicializa LLMClient usando Factory
        config_manager = ConfigManager()
        api_key = config_manager.get_api_key(config)

        self.llm_client = LLMClientFactory.create(
            provider=config.llm.provider,
            model=config.llm.model,
            api_key=api_key,
            base_url=config.llm.base_url,
            temperature=config.llm.temperature,
            max_tokens=config.llm.max_tokens
        )

        self.templates = self._load_templates()

    def _load_templates(self) -> Dict[str, str]:
        """Load prompt templates."""
        templates = {}
        template_dir = Path(__file__).parent.parent / "templates"

        template_files = {
            "module_generate": "module_generate.md",
            "module_validate": "module_validate.md",
            "docstring_generate": "docstring_generate.md",
            "docstring_validate": "docstring_validate.md",
            "class_generate": "class_generate.md",
            "class_validate": "class_validate.md",
            "comment_generate": "comment_generate.md",
            "comment_validate": "comment_validate.md",
        }

        for key, filename in template_files.items():
            template_path = template_dir / filename
            if template_path.exists():
                with open(template_path, 'r', encoding='utf-8') as f:
                    templates[key] = f.read()

        return templates

    def process_task(self, task: DocTask) -> ProcessResult:
        """
        Process a single documentation task.

        Args:
            task: Task to process

        Returns:
            ProcessResult with the outcome
        """
        try:
            # Update task status to processing
            self.queue_manager.update_task_status(task.id, TaskStatus.PROCESSING)

            # Generate prompt based on task type
            prompt = self._generate_prompt(task)

            # Get schema for this task type (for Structured Outputs)
            schema = TASK_SCHEMAS.get(task.task_type)

            # Call LLM with structured schema
            response, tokens = self.llm_client.call(prompt, json_schema=schema)

            # Parse response and format as docstring/comment
            suggestion = self._parse_and_format_response(response, task)

            # Convert Pydantic objects to JSON string for database storage
            if isinstance(suggestion, (ModuleDocstring, ClassDocstring, MethodDocstring)):
                suggestion_for_db = suggestion.model_dump_json()
            else:
                # Already a string (CommentText or ValidationResult)
                suggestion_for_db = suggestion

            # Save suggestion to database
            self.queue_manager.update_suggestion(task.id, suggestion_for_db)

            # Update task status to completed
            self.queue_manager.update_task_status(task.id, TaskStatus.COMPLETED)

            return ProcessResult(
                task_id=task.id,
                success=True,
                suggestion=suggestion,
                tokens_used=tokens
            )

        except Exception as e:
            # Update task status to failed
            self.queue_manager.update_task_status(
                task.id,
                TaskStatus.FAILED,
                error_message=str(e)
            )

            return ProcessResult(
                task_id=task.id,
                success=False,
                error=str(e)
            )

    def process_queue(self, limit: Optional[int] = None) -> List[ProcessResult]:
        """
        Process pending tasks from the queue following TASK_PROCESSING_ORDER.

        Tasks are processed in this fixed sequence:
        1. generate_module (module-level docstrings)
        2. validate_module
        3. generate_class (class docstrings)
        4. validate_class
        5. generate_docstring (method/function docstrings)
        6. validate_docstring
        7. generate_comment (inline comments)
        8. validate_comment

        This ensures module documentation is completed before class docs,
        and class docs before method docs.

        Args:
            limit: Maximum number of tasks to process

        Returns:
            List of ProcessResults
        """
        # Get all pending tasks
        all_pending = self.queue_manager.get_pending_tasks(limit=None)

        # Group tasks by type
        tasks_by_type: Dict[str, List[DocTask]] = {}
        for task in all_pending:
            task_type = task.task_type
            if task_type not in tasks_by_type:
                tasks_by_type[task_type] = []
            tasks_by_type[task_type].append(task)

        # Process tasks in TASK_PROCESSING_ORDER
        results = []
        processed_count = 0

        for task_type in TASK_PROCESSING_ORDER:
            if limit and processed_count >= limit:
                break

            tasks_of_type = tasks_by_type.get(task_type, [])

            for task in tasks_of_type:
                if limit and processed_count >= limit:
                    break

                logger.info(f"Processing task {task.id} of type '{task_type}'")
                result = self.process_task(task)
                results.append(result)
                processed_count += 1

        logger.info(
            f"Processed {processed_count} tasks in order: "
            f"{', '.join([t for t in TASK_PROCESSING_ORDER if t in tasks_by_type])}"
        )

        return results

    def _generate_prompt(self, task: DocTask) -> str:
        """
        Generate prompt for LLM based on task.

        Args:
            task: Documentation task

        Returns:
            Formatted prompt string
        """
        task_type = task.task_type

        # Map task type to template key
        template_map = {
            "generate_module": "module_generate",
            "validate_module": "module_validate",
            "generate_docstring": "docstring_generate",
            "validate_docstring": "docstring_validate",
            "generate_class": "class_generate",
            "validate_class": "class_validate",
            "generate_comment": "comment_generate",
            "validate_comment": "comment_validate",
        }

        template_key = template_map.get(task_type)
        if not template_key:
            # Raise exception for unsupported task types
            valid_types = ', '.join(template_map.keys())
            raise ValueError(
                f"Unsupported task_type: '{task_type}'\n"
                f"Valid task types are: {valid_types}\n"
                f"This error indicates a mismatch between the task creator (cli.py) and processor.\n"
                f"Check that cli.py is using one of the supported task types."
            )

        template = self.templates.get(template_key, "")

        # For validate tasks, extract current docstring/comment
        if task_type.startswith("validate_"):
            current_docstring = self._extract_current_docstring(task.context)
            prompt = template.format(
                file_path=task.file_path,
                line_number=task.line_number,
                context=task.context,
                current_docstring=current_docstring
            )
        else:
            # For generate tasks
            prompt = template.format(
                file_path=task.file_path,
                line_number=task.line_number,
                context=task.context
            )

        return prompt

    def _extract_current_docstring(self, context: str) -> str:
        """
        Extract current docstring from context.

        Args:
            context: Code context

        Returns:
            Current docstring or empty string
        """
        # Use centralized utility function
        docstring = extract_docstring(context)
        return docstring if docstring else ""


    def _parse_and_format_response(self, response: str, task: DocTask):
        """
        Parse structured LLM response and return schema object or formatted string.

        With Structured Outputs, the response is guaranteed to be valid JSON
        matching the Pydantic schema for the task type. This method parses
        the JSON and returns either:
        - Pydantic schema objects (for generate_* tasks) - formatting done in applier
        - Formatted strings (for validate_* tasks and generate_comment)

        Args:
            response: JSON string from LLM (structured output)
            task: Original task

        Returns:
            Union[ModuleDocstring, ClassDocstring, MethodDocstring, str]: Schema object or formatted string
        """
        try:
            parsed_json = json.loads(response)
            task_type = task.task_type

            # GENERATE tasks - return Pydantic object (formatting in applier)
            if task_type == "generate_module":
                return ModuleDocstring(**parsed_json)

            elif task_type == "generate_class":
                return ClassDocstring(**parsed_json)

            elif task_type == "generate_docstring":
                return MethodDocstring(**parsed_json)

            elif task_type == "generate_comment":
                # Comments are simple strings - return directly
                schema_obj = CommentText(**parsed_json)
                return schema_obj.comment

            # VALIDATE tasks - return full ValidationResult JSON
            elif task_type.startswith("validate_"):
                validation = ValidationResult(**parsed_json)

                # Store full ValidationResult as JSON (preserves issues/suggestions)
                # This allows the review command to display rationale
                return validation.model_dump_json()

            else:
                logger.warning(f"Unknown task type: {task_type}")
                return response

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Error parsing structured response: {e}")
            # In case of error, return raw response
            return response.strip()
