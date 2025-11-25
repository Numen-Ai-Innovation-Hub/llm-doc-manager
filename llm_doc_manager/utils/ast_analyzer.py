"""
AST-based code analysis for documentation generation.

Provides static analysis of Python modules to extract metadata,
build dependency graphs, detect entry points, and calculate metrics.
"""

import ast
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class ModuleInfo:
    """Information extracted from a Python module."""
    module_path: str
    module_name: str
    module_docstring: Optional[str] = None
    imports_internal: List[str] = field(default_factory=list)
    imports_external: List[str] = field(default_factory=list)
    classes: List[Dict] = field(default_factory=list)
    functions: List[Dict] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)
    lines_of_code: int = 0
    complexity: str = "unknown"


@dataclass
class ImportRelationship:
    """Represents an import relationship between modules."""
    from_module: str
    to_module: str
    import_type: str  # 'import', 'from_import'
    imported_names: List[str] = field(default_factory=list)


class ASTAnalyzer:
    """
    Analyzes Python code using AST (Abstract Syntax Tree).

    Extracts module information, builds import graphs, detects entry points,
    and calculates code metrics for documentation generation.
    """

    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize AST analyzer.

        Args:
            project_root: Root directory of the project.
                         If None, uses current working directory.
        """
        self.project_root = project_root or Path.cwd()

    def extract_module_info(self, file_path: str) -> ModuleInfo:
        """
        Extract comprehensive information from a Python module.

        Args:
            file_path: Path to the Python file

        Returns:
            ModuleInfo object with extracted data
        """
        file_path = Path(file_path)
        module_name = file_path.stem

        # Read file content
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception as e:
            # Return minimal info if file can't be read
            return ModuleInfo(
                module_path=str(file_path),
                module_name=module_name,
                lines_of_code=0
            )

        # Parse AST
        try:
            tree = ast.parse(content, filename=str(file_path))
        except SyntaxError:
            # Return minimal info if syntax error
            return ModuleInfo(
                module_path=str(file_path),
                module_name=module_name,
                lines_of_code=len(content.split('\n'))
            )

        # Extract module docstring
        module_docstring = ast.get_docstring(tree)

        # Extract imports
        imports_internal = []
        imports_external = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if self._is_internal_import(alias.name):
                        imports_internal.append(alias.name)
                    else:
                        imports_external.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if self._is_internal_import(module):
                    imports_internal.append(module)
                else:
                    imports_external.append(module)

        # Extract classes
        classes = []
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                class_info = {
                    'name': node.name,
                    'docstring': ast.get_docstring(node),
                    'methods': [m.name for m in node.body if isinstance(m, ast.FunctionDef)],
                    'line_number': node.lineno
                }
                classes.append(class_info)

        # Extract functions (module-level only)
        functions = []
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                func_info = {
                    'name': node.name,
                    'docstring': ast.get_docstring(node),
                    'parameters': [arg.arg for arg in node.args.args],
                    'line_number': node.lineno,
                    'is_async': isinstance(node, ast.AsyncFunctionDef)
                }
                functions.append(func_info)

        # Extract __all__ (explicit exports)
        exports = []
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == '__all__':
                        if isinstance(node.value, ast.List):
                            exports = [
                                elt.s for elt in node.value.elts
                                if isinstance(elt, ast.Str)
                            ]

        # If no __all__, consider all public classes and functions as exports
        if not exports:
            exports = [c['name'] for c in classes if not c['name'].startswith('_')]
            exports += [f['name'] for f in functions if not f['name'].startswith('_')]

        # Calculate LOC
        lines_of_code = len(content.split('\n'))

        # Calculate complexity (simple heuristic)
        complexity = self._calculate_complexity(lines_of_code, len(classes), len(functions))

        return ModuleInfo(
            module_path=str(file_path),
            module_name=module_name,
            module_docstring=module_docstring,
            imports_internal=list(set(imports_internal)),
            imports_external=list(set(imports_external)),
            classes=classes,
            functions=functions,
            exports=exports,
            lines_of_code=lines_of_code,
            complexity=complexity
        )

    def build_import_graph(self, project_root: Optional[Path] = None) -> List[ImportRelationship]:
        """
        Build complete import graph for the project.

        Args:
            project_root: Root directory to scan. If None, uses self.project_root

        Returns:
            List of ImportRelationship objects
        """
        project_root = project_root or self.project_root
        relationships = []

        # Find all Python files
        python_files = list(project_root.rglob('*.py'))

        for file_path in python_files:
            try:
                content = file_path.read_text(encoding='utf-8')
                tree = ast.parse(content, filename=str(file_path))

                from_module = self._get_module_path(file_path, project_root)

                # Extract imports
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            relationships.append(ImportRelationship(
                                from_module=from_module,
                                to_module=alias.name,
                                import_type='import',
                                imported_names=[alias.asname or alias.name]
                            ))
                    elif isinstance(node, ast.ImportFrom):
                        module = node.module or ""
                        names = [alias.name for alias in node.names]
                        relationships.append(ImportRelationship(
                            from_module=from_module,
                            to_module=module,
                            import_type='from_import',
                            imported_names=names
                        ))
            except Exception:
                # Skip files with parsing errors
                continue

        return relationships

    def detect_entry_points(self, project_root: Optional[Path] = None) -> Dict[str, str]:
        """
        Detect entry points in the project.

        Args:
            project_root: Root directory to scan

        Returns:
            Dictionary mapping entry point type to file path
        """
        project_root = project_root or self.project_root
        entry_points = {}

        # Check for __main__.py
        main_file = project_root / '__main__.py'
        if main_file.exists():
            entry_points['main'] = str(main_file)

        # Check for CLI entry points (files with cli, main, or app in name)
        for file_path in project_root.rglob('*.py'):
            name_lower = file_path.stem.lower()
            if name_lower in ['cli', 'main', 'app', '__main__']:
                if 'cli' in name_lower:
                    entry_points['cli'] = str(file_path)
                elif 'main' in name_lower or '__main__' in name_lower:
                    if 'main' not in entry_points:
                        entry_points['main'] = str(file_path)
                elif 'app' in name_lower:
                    entry_points['app'] = str(file_path)

        # Check for setup.py entry points
        setup_py = project_root / 'setup.py'
        if setup_py.exists():
            try:
                content = setup_py.read_text(encoding='utf-8')
                tree = ast.parse(content)

                # Look for entry_points in setup() call
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        if isinstance(node.func, ast.Name) and node.func.id == 'setup':
                            for keyword in node.keywords:
                                if keyword.arg == 'entry_points':
                                    # Found entry_points definition
                                    entry_points['setup'] = str(setup_py)
                                    break
            except Exception:
                pass

        return entry_points

    def calculate_metrics(self, file_path: str) -> Dict[str, any]:
        """
        Calculate code metrics for a file.

        Args:
            file_path: Path to Python file

        Returns:
            Dictionary with metrics (LOC, functions, classes, complexity, etc.)
        """
        file_path = Path(file_path)

        try:
            content = file_path.read_text(encoding='utf-8')
            tree = ast.parse(content)
        except Exception:
            return {
                'lines_of_code': 0,
                'functions': 0,
                'classes': 0,
                'complexity': 'unknown',
                'has_tests': False
            }

        # Count elements
        num_functions = sum(1 for node in ast.walk(tree) if isinstance(node, ast.FunctionDef))
        num_classes = sum(1 for node in ast.walk(tree) if isinstance(node, ast.ClassDef))
        lines_of_code = len(content.split('\n'))

        # Check for tests
        has_tests = 'test' in file_path.name.lower() or 'tests' in str(file_path).lower()

        # Calculate complexity
        complexity = self._calculate_complexity(lines_of_code, num_classes, num_functions)

        return {
            'lines_of_code': lines_of_code,
            'functions': num_functions,
            'classes': num_classes,
            'complexity': complexity,
            'has_tests': has_tests
        }

    def _is_internal_import(self, import_name: str) -> bool:
        """
        Check if an import is internal to the project.

        Args:
            import_name: Import module name

        Returns:
            True if internal, False if external
        """
        # Simple heuristic: starts with '.' or matches project structure
        if import_name.startswith('.'):
            return True

        # Check if it's a submodule of the project
        project_name = self.project_root.name
        if import_name.startswith(project_name):
            return True

        return False

    def _get_module_path(self, file_path: Path, project_root: Path) -> str:
        """
        Convert file path to module path.

        Args:
            file_path: Path to Python file
            project_root: Project root directory

        Returns:
            Module path (e.g., 'src.scanner')
        """
        try:
            relative = file_path.relative_to(project_root)
            parts = list(relative.parts[:-1]) + [relative.stem]
            return '.'.join(parts)
        except ValueError:
            return file_path.stem

    def _calculate_complexity(self, loc: int, num_classes: int, num_functions: int) -> str:
        """
        Calculate complexity level based on LOC and structure.

        Args:
            loc: Lines of code
            num_classes: Number of classes
            num_functions: Number of functions

        Returns:
            Complexity level: 'low', 'medium', 'high', 'very_high'
        """
        # Simple heuristic
        score = 0

        if loc > 500:
            score += 3
        elif loc > 200:
            score += 2
        elif loc > 100:
            score += 1

        if num_classes > 5:
            score += 2
        elif num_classes > 2:
            score += 1

        if num_functions > 20:
            score += 2
        elif num_functions > 10:
            score += 1

        if score >= 6:
            return 'very_high'
        elif score >= 4:
            return 'high'
        elif score >= 2:
            return 'medium'
        else:
            return 'low'