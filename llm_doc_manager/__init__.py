"""
LLM Documentation Manager

A tool for automatically validating, creating, and updating docstrings,
code comments, and project documentation using Large Language Models.
"""

__version__ = "0.1.0"
__author__ = "AI Innovation Hub"

from .scanner import Scanner
from .queue import QueueManager, DocTask
from .processor import Processor
from .applier import Applier
from .config import Config

__all__ = [
    "Scanner",
    "QueueManager",
    "DocTask",
    "Processor",
    "Applier",
    "Config",
]
