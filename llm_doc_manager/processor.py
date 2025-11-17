"""
LLM Processor for generating and validating documentation.

Handles communication with LLM providers to generate, validate, and improve documentation.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from .config import Config, ConfigManager
from .queue import DocTask, QueueManager, TaskStatus
from .docstring_utils import extract_docstring


@dataclass
class ProcessResult:
    """Result of processing a documentation task."""
    task_id: int
    success: bool
    suggestion: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
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
        self.llm_client = self._init_llm_client()
        self.templates = self._load_templates()

    def _init_llm_client(self):
        """Initialize LLM client based on configuration."""
        provider = self.config.llm.provider.lower()

        # Get API key
        config_manager = ConfigManager()
        api_key = config_manager.get_api_key(self.config)

        if provider == "anthropic":
            try:
                import anthropic
                return anthropic.Anthropic(api_key=api_key)
            except ImportError:
                raise ImportError("anthropic package not installed. Run: pip install anthropic")

        elif provider == "openai":
            try:
                import openai
                return openai.OpenAI(api_key=api_key)
            except ImportError:
                raise ImportError("openai package not installed. Run: pip install openai")

        elif provider == "ollama":
            # Ollama client (local)
            try:
                import ollama
                return ollama.Client()
            except ImportError:
                raise ImportError("ollama package not installed. Run: pip install ollama")

        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    def _load_templates(self) -> Dict[str, str]:
        """Load prompt templates."""
        templates = {}
        template_dir = Path(__file__).parent / "templates"

        template_files = {
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

            # Call LLM
            response, tokens = self._call_llm(prompt)

            # Parse response
            suggestion = self._parse_response(response, task)

            # Save suggestion to database
            self.queue_manager.update_suggestion(task.id, suggestion)

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
        Process pending tasks from the queue.

        Args:
            limit: Maximum number of tasks to process

        Returns:
            List of ProcessResults
        """
        pending_tasks = self.queue_manager.get_pending_tasks(limit=limit)
        results = []

        for task in pending_tasks:
            result = self.process_task(task)
            results.append(result)

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
            "generate_docstring": "docstring_generate",
            "validate_docstring": "docstring_validate",
            "generate_class": "class_generate",
            "validate_class": "class_validate",
            "generate_comment": "comment_generate",
            "validate_comment": "comment_validate",
        }

        template_key = template_map.get(task_type)
        if not template_key:
            # Fallback for unsupported task types
            return f"Generate or validate documentation for:\n\n{task.context}"

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

    def _call_llm(self, prompt: str) -> tuple[str, int]:
        """
        Call LLM with the prompt.

        Args:
            prompt: Formatted prompt

        Returns:
            Tuple of (response text, tokens used)
        """
        provider = self.config.llm.provider.lower()

        if provider == "anthropic":
            response = self.llm_client.messages.create(
                model=self.config.llm.model,
                max_tokens=self.config.llm.max_tokens,
                temperature=self.config.llm.temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            tokens = response.usage.input_tokens + response.usage.output_tokens
            return response.content[0].text, tokens

        elif provider == "openai":
            response = self.llm_client.chat.completions.create(
                model=self.config.llm.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=self.config.llm.temperature,
                max_tokens=self.config.llm.max_tokens
            )
            tokens = response.usage.total_tokens
            return response.choices[0].message.content, tokens

        elif provider == "ollama":
            response = self.llm_client.chat(
                model=self.config.llm.model,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            # Ollama doesn't provide token count by default
            return response['message']['content'], 0

        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def _parse_response(self, response: str, task: DocTask) -> str:
        """
        Parse LLM response.

        Args:
            response: Raw LLM response
            task: Original task

        Returns:
            Parsed suggestion
        """
        # Try to parse as JSON first (for validation tasks and comment generation)
        if task.task_type.startswith("validate_") or task.task_type in ["generate_comment"]:
            try:
                # Clean response - remove markdown code blocks if present
                cleaned = response.strip()

                # Remove ```json and ``` markers
                if cleaned.startswith('```json'):
                    cleaned = cleaned[7:]  # Remove ```json
                if cleaned.startswith('```'):
                    cleaned = cleaned[3:]  # Remove ```
                if cleaned.endswith('```'):
                    cleaned = cleaned[:-3]  # Remove trailing ```

                cleaned = cleaned.strip()

                # Parse JSON
                parsed = json.loads(cleaned)

                # Extract the appropriate field based on task type
                if task.task_type == "validate_docstring" and "improved_docstring" in parsed:
                    return parsed["improved_docstring"]
                elif task.task_type == "validate_class" and "improved_docstring" in parsed:
                    return parsed["improved_docstring"]
                elif task.task_type in ["validate_comment", "generate_comment"] and "comment" in parsed:
                    return parsed["comment"]
                elif task.task_type == "validate_comment" and "improved_comment" in parsed:
                    return parsed["improved_comment"]

            except (json.JSONDecodeError, KeyError, ValueError):
                # If parsing fails, return full response
                pass

        # For generate tasks (docstring/class) or if JSON parsing fails, return as-is
        return response.strip()
