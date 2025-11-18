"""
Main entry point for running llm_doc_manager as a module.

This allows the package to be run with: python -m llm_doc_manager
"""

from .src.cli import main

if __name__ == '__main__':
    main()
