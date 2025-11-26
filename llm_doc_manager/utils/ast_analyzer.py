# @llm-module-start
"""
Analyzes Python code using Abstract Syntax Tree (AST) for documentation generation.

This module provides tools for static analysis of Python modules, enabling the extraction of metadata, building of dependency graphs, detection of entry points, and calculation of code metrics. Key components include the `ASTAnalyzer` class for performing the analysis, and the `ModuleInfo` and `ImportRelationship` data classes for structuring the extracted information. Use this module when you need to generate documentation or understand the structure and dependencies of a Python project.

Typical usage example:
from llm_doc_manager.utils.ast_analyzer import ASTAnalyzer
analyzer = ASTAnalyzer()
module_info = analyzer.extract_module_info('path/to/module.py')
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
    Stores information extracted from a Python module.

    This class encapsulates details about a module, including its path, name,
    docstring, and various components such as imports, classes, and functions.
    It serves as a structured representation of the module's content for analysis.

    Attributes:
        module_path (str): The file path of the module.
        module_name (str): The name of the module.
        module_docstring (Optional[str]): The docstring of the module, if any.
        imports_internal (List[str]): List of internal imports used in the module.
        imports_external (List[str]): List of external imports used in the module.
        classes (List[Dict]): List of classes defined in the module.
        functions (List[Dict]): List of functions defined in the module.
        exports (List[str]): List of exported names from the module.
        lines_of_code (int): The total number of lines of code in the module.
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

    This class captures the details of how one module imports another, including the type of import and the specific names being imported. It is primarily used for analyzing dependencies between modules in a codebase.

    Attributes:
        from_module (str): The name of the module initiating the import.
        to_module (str): The name of the module being imported.
        import_type (str): The type of import, either 'import' or 'from_import'.
        imported_names (List[str]): A list of names that are imported from the module.
    """
    from_module: str
    to_module: str
    import_type: str  # 'import', 'from_import'
    imported_names: List[str] = field(default_factory=list)
# @llm-class-end

# @llm-class-start
class ASTAnalyzer:
    """
    Analyzes Python code using AST (Abstract Syntax Tree). This class extracts module information, builds import graphs, detects entry points, and calculates code metrics for documentation generation. It is primarily responsible for providing insights into the structure and dependencies of Python projects.

    Attributes:
        project_root (Path): Root directory of the project, defaults to current working directory.
    """

    # @llm-doc-start
    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize AST analyzer for a project directory.

        This constructor sets up the Abstract Syntax Tree (AST) analyzer by defining the
        root directory of the project. If no directory is provided, it defaults to the
        current working directory.

        Args:
            project_root (Optional[Path]): Root directory of the project. If None,
            uses the current working directory.

        Returns:
            None: This constructor does not return a value.

        Raises:
            None: This constructor does not raise any exceptions.
        """
        self.project_root = project_root or Path.cwd()
    # @llm-doc-end

    # @llm-doc-start
    def extract_module_info(self, file_path: str) -> ModuleInfo:
        """
        Extracts comprehensive information from a Python module.

        This function reads a Python file, parses its Abstract Syntax Tree (AST),
        and extracts various details including the module's docstring, internal and
        external imports, classes, functions, and explicit exports.

        Args:
            file_path (str): Path to the Python file.

        Returns:
            ModuleInfo: An object containing extracted data such as module path,
            name, docstring, internal and external imports, classes, functions,
            exports, and lines of code.

        Raises:
            Exception: If reading the file fails, it returns a ModuleInfo object
            with zero lines of code.
            SyntaxError: If the file contains invalid Python syntax, it returns a
            ModuleInfo object with the number of lines in the content.
        """
        file_path = Path(file_path)
        module_name = file_path.stem

        # @llm-comm-start
        # Attempt to read the file content and handle any exceptions
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
        # Attempt to parse the provided content into an AST and handle syntax errors
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
        # Retrieve the module's docstring and initialize import lists
        module_docstring = ast.get_docstring(tree)
        imports_internal = []
        imports_external = []
        # @llm-comm-end

        # @llm-comm-start
        # Categorize imported modules as internal or external based on their names
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
        # Collect information about classes defined in the AST tree
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
        # Collect module-level function details including name, docstring, and parameters
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
        # Collect the explicit exports defined in the __all__ variable
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
        # Gather all public class and function names as exports if none specified
        if not exports:
            exports = [c['name'] for c in classes if not c['name'].startswith('_')]
            exports += [f['name'] for f in functions if not f['name'].startswith('_')]
        # @llm-comm-end

        # @llm-comm-start
        # Count the number of lines in the provided content string
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
        Builds a complete import graph for the project.

        This function analyzes Python files in the specified project root directory
        and constructs a list of import relationships between modules.

        Args:
            project_root (Optional[Path]): Root directory to scan. If None, uses
            self.project_root.
            restrict_to_files (Optional[List[str]]): List of specific files to
            restrict the analysis to. If None, all Python files in the project
            root are considered.

        Returns:
            List[ImportRelationship]: A list of ImportRelationship objects that
            represent the relationships between imported and importing modules.

        Raises:
            Exception: If an error occurs while reading a file or parsing its
            content, the function catches the exception and continues with the
            next file.
        """
        # @llm-comm-start
        # Set the project root and initialize an empty list for relationships
        project_root = project_root or self.project_root
        relationships = []
        # @llm-comm-end

        # @llm-comm-start
        # Determine the list of Python files based on specified restrictions
        if restrict_to_files:
            python_files = [Path(f) if Path(f).is_absolute() else (project_root / f) for f in restrict_to_files]
        else:
            python_files = list(project_root.rglob('*.py'))
        # @llm-comm-end

        # @llm-comm-start
        # Extract import relationships from Python files in the project
        for file_path in python_files:
            try:
                # @llm-comm-start
                # Read file content, parse it into an AST, and determine module path
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

        This function scans the specified project root directory for various entry
        points, including `__main__.py`, CLI files, and entry points defined in
        `setup.py`. It returns a dictionary mapping the type of entry point to
        its corresponding file path.

        Args:
            project_root (Optional[Path]): Root directory to scan. If not provided,
            the function uses the instance's project root.

        Returns:
            Dict[str, str]: Dictionary mapping entry point type to file path.

        Raises:
            Exception: If an error occurs while reading or parsing `setup.py`.
        """
        # @llm-comm-start
        # Set project root to the provided value or use the default project root
        project_root = project_root or self.project_root
        entry_points = {}
        # @llm-comm-end

        # @llm-comm-start
        # Identify and store the path of __main__.py if it exists in the project
        main_file = project_root / '__main__.py'
        if main_file.exists():
            entry_points['main'] = str(main_file)
        # @llm-comm-end

        # @llm-comm-start
        # Identify Python files serving as CLI entry points in the project
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
        # Extract entry_points from the setup() function in setup.py file
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

        This function analyzes a Python file to compute various metrics, including the
        number of lines of code, functions, classes, and whether the file contains tests.

        Args:
            file_path (str): Path to the Python file to be analyzed.

        Returns:
            Dict[str, any]: A dictionary containing the metrics:
            - 'lines_of_code': Number of lines in the file.
            - 'functions': Number of function definitions found.
            - 'classes': Number of class definitions found.
            - 'has_tests': Boolean indicating if the file name suggests it contains tests.

        Raises:
            Exception: If reading the file or parsing its content fails.
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
        # Count the number of functions, classes, and lines of code in the tree
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
        Checks if an import is internal to the project.

        This function uses a simple heuristic to determine if the provided import
        name is internal by checking if it starts with a dot or matches the project
        structure.

        Args:
            import_name (str): Import module name to check.

        Returns:
            bool: True if the import is internal, False if it is external.

        Raises:
            None: This function does not raise any exceptions.
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
        Convert file path to module path.

        This function transforms a given file path into a module path relative to a specified project root. If the file path is not relative to the project root, it returns the stem of the file path.

        Args:
            file_path (Path): Path to the Python file to be converted.
            project_root (Path): Root directory of the project used for relative pathing.

        Returns:
            str: Module path in dot notation (e.g., 'src.scanner') or the stem of the
            file path if it cannot be converted.

        Raises:
            ValueError: When the file path is not relative to the project root.
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