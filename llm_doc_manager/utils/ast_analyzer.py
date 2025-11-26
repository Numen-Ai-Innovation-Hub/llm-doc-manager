# @llm-module-start
"""
AST-based code analysis for documentation generation.

This module provides static analysis of Python modules to extract metadata,
build dependency graphs, detect entry points, and calculate code metrics. Key
components include the `ASTAnalyzer` class for analyzing code, `ModuleInfo` for
storing module metadata, and `ImportRelationship` for representing import
relationships. Use this module to automate the extraction of useful information
from Python codebases.

Typical usage:
from llm_doc_manager.utils.ast_analyzer import ASTAnalyzer
analyzer = ASTAnalyzer(project_root='path/to/project')
"""

import ast
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field

# @llm-class-start
@dataclass
class ModuleInfo:
    """
    Information extracted from a Python module.

    This class encapsulates details about a Python module, including its path,
    name, docstring, and imports. It also tracks defined classes, functions, and
    the total lines of code in the module.

    Attributes:
        module_path (str): The file path of the module.
        module_name (str): The name of the module.
        module_docstring (Optional[str]): The docstring of the module, if
        available.
        imports_internal (List[str]): List of internal module imports.
        imports_external (List[str]): List of external module imports.
        classes (List[Dict]): List of classes defined in the module.
        functions (List[Dict]): List of functions defined in the module.
        exports (List[str]): List of exported names from the module.
        lines_of_code (int): Total number of lines of code in the module.
    """
    module_path: str
    module_name: str
    module_docstring: Optional[str] = None
    imports_internal: List[str] = field(default_factory=list)
    imports_external: List[str] = field(default_factory=list)
    classes: List[Dict] = field(default_factory=list)
    functions: List[Dict] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)
    lines_of_code: int = 0
# @llm-class-end

# @llm-class-start
@dataclass
class ImportRelationship:
    """
    Represents an import relationship between modules.

    This class encapsulates the relationship where one module imports another,
    including the type of import and the specific names imported.

    Attributes:
        from_module (str): The module from which the import originates.
        to_module (str): The module that is being imported.
        import_type (str): The type of import ('import' or 'from_import').
        imported_names (List[str]): A list of specific names imported from the
        module.
    """
    from_module: str
    to_module: str
    import_type: str  # 'import', 'from_import'
    imported_names: List[str] = field(default_factory=list)
# @llm-class-end

# @llm-class-start
class ASTAnalyzer:
    """
    Analyzes Python code using the Abstract Syntax Tree (AST).

    This class is responsible for extracting module information, building import
    graphs, detecting entry points, and calculating code metrics for documentation
    generation. It provides methods to analyze Python files and gather relevant
    data for project documentation.
    """

    # @llm-doc-start
    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize AST analyzer.

        This class analyzes the Abstract Syntax Tree (AST) of Python code.

        Args:
            project_root (Optional[Path]): Root directory of the project. If None, uses
            the current working directory.

        Returns:
            None: This constructor does not return a value.
        """
        self.project_root = project_root or Path.cwd()
    # @llm-doc-end

    # @llm-doc-start
    def extract_module_info(self, file_path: str) -> ModuleInfo:
        """
        Extracts comprehensive information from a Python module.

        This function reads a Python file, parses its Abstract Syntax Tree (AST), and
        extracts
        information such as module docstring, internal and external imports, classes,
        functions,
        and explicit exports. It returns a ModuleInfo object containing this data.

        Args:
            file_path (str): Path to the Python file.

        Returns:
            ModuleInfo: An object containing extracted data from the module.

        Raises:
            FileNotFoundError: If the specified file does not exist.
            SyntaxError: If the file contains invalid Python syntax.
        """
        file_path = Path(file_path)
        module_name = file_path.stem

        # @llm-comm-start
        # Attempt to read the content of the specified file, handling any exceptions that
        # may occur.
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception as e:
            return ModuleInfo(
                module_path=str(file_path),
                module_name=module_name,
                lines_of_code=0
            )
        # @llm-comm-end

        # @llm-comm-start
        # Attempt to parse the provided content into an Abstract Syntax Tree (AST). If
        # a SyntaxError occurs, return a ModuleInfo object with the module path, name,
        # and line count.
        try:
            tree = ast.parse(content, filename=str(file_path))
        except SyntaxError:
            return ModuleInfo(
                module_path=str(file_path),
                module_name=module_name,
                lines_of_code=len(content.split('\n'))
            )
        # @llm-comm-end

        # @llm-comm-start
        # Retrieve the module's docstring from the AST.
        module_docstring = ast.get_docstring(tree)
        imports_internal = []
        imports_external = []
        # @llm-comm-end

        # @llm-comm-start
        # Categorize imports into internal and external lists from the AST tree
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
        # @llm-comm-end

        # @llm-comm-start
        # Extracts class definitions from the AST and stores their name, docstring,
        # methods, and line number in a list.
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
        # @llm-comm-end

        # @llm-comm-start
        # Extracts module-level function definitions from the AST, including their
        # names, docstrings, parameters, line numbers, and async status.
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
        # @llm-comm-end

        # @llm-comm-start
        # Extracts the '__all__' variable from the AST, which defines explicit exports.
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
        # @llm-comm-end

        # @llm-comm-start
        # If no exports are defined, include all public classes and functions in the
        # exports.
        if not exports:
            exports = [c['name'] for c in classes if not c['name'].startswith('_')]
            exports += [f['name'] for f in functions if not f['name'].startswith('_')]
        # @llm-comm-end

        # @llm-comm-start
        # Count the number of lines in the given content string
        lines_of_code = len(content.split('\n'))
        # @llm-comm-end

        # @llm-comm-start
        # Create and return a ModuleInfo object with module details and metadata
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
        )
        # @llm-comm-end
    # @llm-doc-end

    # @llm-doc-start
    def build_import_graph(self, project_root: Optional[Path] = None, restrict_to_files: Optional[List[str]] = None) -> List[ImportRelationship]:
        """
        Build a complete import graph for the project.

        Args:
            project_root (Optional[Path]): Root directory to scan. If None, uses
            self.project_root.
            restrict_to_files (Optional[List[str]]): List of specific files to restrict
            the import graph to.

        Returns:
            List[ImportRelationship]: A list of ImportRelationship objects representing
            the import relationships found.

        Raises:
            Exception: If there is an error reading a file or parsing its content.
        """
        # @llm-comm-start
        # Set project_root to a default if not provided and initialize relationships list
        project_root = project_root or self.project_root
        relationships = []
        # @llm-comm-end

        # @llm-comm-start
        # Determine Python files to analyze based on user restrictions or project root
        if restrict_to_files:
            python_files = [Path(f) if Path(f).is_absolute() else (project_root / f) for f in restrict_to_files]
        else:
            python_files = list(project_root.rglob('*.py'))
        # @llm-comm-end

        # @llm-comm-start
        # Reads Python files, parses their AST, and collects import relationships.
        for file_path in python_files:
            try:
                # @llm-comm-start
                # Read file content, parse it into an AST, and get the module path
                content = file_path.read_text(encoding='utf-8')
                tree = ast.parse(content, filename=str(file_path))
                from_module = self._get_module_path(file_path, project_root)
                # @llm-comm-end

                # @llm-comm-start
                # Extract import relationships from the AST and store them in a list
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
                # @llm-comm-end
            except Exception:
                continue
        return relationships
        # @llm-comm-end
    # @llm-doc-end

    # @llm-doc-start
    def detect_entry_points(self, project_root: Optional[Path] = None) -> Dict[str, str]:
        """
        Detect entry points in the project.

        Args:
            project_root (Optional[Path]): Root directory to scan. If not provided,
            defaults to the instance's project_root.

        Returns:
            Dict[str, str]: A dictionary mapping entry point types (e.g., 'main',
            'cli', 'app', 'setup') to their corresponding file paths.

        Raises:
            Exception: If there is an error reading the 'setup.py' file.
        """
        # @llm-comm-start
        # Set project_root to the provided value or fallback to the default
        project_root = project_root or self.project_root
        entry_points = {}
        # @llm-comm-end

        # @llm-comm-start
        # Check if the '__main__.py' file exists in the project root and set it as the
        # main entry point if found.
        main_file = project_root / '__main__.py'
        if main_file.exists():
            entry_points['main'] = str(main_file)
        # @llm-comm-end

        # @llm-comm-start
        # Identify Python files in the project root that serve as CLI entry points by
        # checking for 'cli', 'main', or 'app' in their filenames.
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
        # @llm-comm-end

        # Check for setup.py entry points
        setup_py = project_root / 'setup.py'

        # @llm-comm-start        
        # Traverse the AST to find 'entry_points' in the setup() function call.
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
        # @llm-comm-end

        return entry_points
    # @llm-doc-end

    # @llm-doc-start
    def calculate_metrics(self, file_path: str) -> Dict[str, any]:
        """
        Calculate code metrics for a file.

        Args:
            file_path (str): Path to the Python file.

        Returns:
            Dict[str, any]: A dictionary with metrics including lines of code (LOC),
            number of functions, number of classes, and a boolean indicating if tests
            are present.

        Raises:
            IOError: If the file cannot be read.
        """
        file_path = Path(file_path)

        # @llm-comm-start
        # Read file content and parse it into an abstract syntax tree
        try:
            content = file_path.read_text(encoding='utf-8')
            tree = ast.parse(content)
        except Exception:
            return {
                'lines_of_code': 0,
                'functions': 0,
                'classes': 0,
                'has_tests': False
            }
        # @llm-comm-end

        # @llm-comm-start
        # Count the number of function and class definitions, and calculate the total
        # lines of code.
        num_functions = sum(1 for node in ast.walk(tree) if isinstance(node, ast.FunctionDef))
        num_classes = sum(1 for node in ast.walk(tree) if isinstance(node, ast.ClassDef))
        lines_of_code = len(content.split('\n'))
        # @llm-comm-end

        # Check for tests
        has_tests = 'test' in file_path.name.lower() or 'tests' in str(file_path).lower()

        return {
            'lines_of_code': lines_of_code,
            'functions': num_functions,
            'classes': num_classes,
            'has_tests': has_tests
        }
    # @llm-doc-end

    # @llm-doc-start
    def _is_internal_import(self, import_name: str) -> bool:
        """
        Check if an import is internal to the project.

        This function determines whether a given import name is considered internal to
        the project based on its naming convention.

        Args:
            import_name (str): The name of the import module.

        Returns:
            bool: True if the import is internal, False if it is external.

        Raises:
            AttributeError: If 'self.project_root' is not defined.
        """
        # Simple heuristic: starts with '.' or matches project structure
        if import_name.startswith('.'):
            return True

        # Check if it's a submodule of the project
        project_name = self.project_root.name
        if import_name.startswith(project_name):
            return True

        return False
    # @llm-doc-end

    # @llm-doc-start
    def _get_module_path(self, file_path: Path, project_root: Path) -> str:
        """
        Convert a file path to a module path.

        This function converts a given file path into a module path by determining the
        relative path from the project root and formatting it appropriately.

        Args:
            file_path (Path): Path to the Python file.
            project_root (Path): Project root directory.

        Returns:
            str: The module path (e.g., 'src.scanner').

        Raises:
            ValueError: If the file_path is not a subpath of project_root.
        """
        try:
            relative = file_path.relative_to(project_root)
            parts = list(relative.parts[:-1]) + [relative.stem]
            return '.'.join(parts)
        except ValueError:
            return file_path.stem
    # @llm-doc-end
# @llm-class-end
# @llm-module-end