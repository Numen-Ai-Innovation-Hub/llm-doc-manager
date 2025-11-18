"""
Centralized logging configuration for llm-doc-manager.

Provides a simple, consistent logging interface across all modules.
"""

import logging
import sys
from pathlib import Path
from typing import Optional


class LoggerManager:
    """Manages logging configuration for the application."""

    _initialized = False
    _log_file = None

    @classmethod
    def setup_logging(cls, log_file: Optional[str] = None, level: str = "INFO"):
        """
        Setup logging configuration.

        Args:
            log_file (Optional[str]): Path to log file. If None, logs to console only.
            level (str): Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        if cls._initialized:
            return

        # Convert string level to logging constant
        numeric_level = getattr(logging, level.upper(), logging.INFO)

        # Create formatter
        formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Setup root logger
        root_logger = logging.getLogger('llm_doc_manager')
        root_logger.setLevel(numeric_level)
        root_logger.handlers.clear()

        # Console handler (always enabled)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        # File handler (optional)
        if log_file:
            cls._log_file = Path(log_file)
            cls._log_file.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(cls._log_file, encoding='utf-8')
            file_handler.setLevel(numeric_level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)

        cls._initialized = True

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        Get a logger for a specific module.

        Args:
            name (str): Module name (usually __name__)

        Returns:
            logging.Logger: Configured logger instance
        """
        if not cls._initialized:
            cls.setup_logging()

        return logging.getLogger(f'llm_doc_manager.{name}')


def get_logger(name: str) -> logging.Logger:
    """
    Convenience function to get a logger.

    Args:
        name (str): Module name (usually __name__)

    Returns:
        logging.Logger: Configured logger instance
    """
    return LoggerManager.get_logger(name)