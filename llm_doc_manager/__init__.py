"""
LLM Documentation Manager

A tool for automatically validating, creating, and updating docstrings,
code comments, and project documentation using Large Language Models.
"""

__version__ = "0.1.0"
__author__ = "AI Innovation Hub"

from .src.scanner import Scanner
from .src.queue import QueueManager, DocTask
from .src.processor import Processor
from .src.applier import Applier
from .src.config import Config

__all__ = [
    "Scanner",
    "QueueManager",
    "DocTask",
    "Processor",
    "Applier",
    "Config",
]
