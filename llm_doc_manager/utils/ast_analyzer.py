# @llm-module-start
import ast
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field

# @llm-class-start
@dataclass
class ModuleInfo:
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
    from_module: str
    to_module: str
    import_type: str
    imported_names: List[str] = field(default_factory=list)
# @llm-class-end

# @llm-class-start
class ASTAnalyzer:
    # @llm-doc-start
    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
    # @llm-doc-end

    # @llm-doc-start
    def extract_module_info(self, file_path: str) -> ModuleInfo:
        file_path = Path(file_path)
        module_name = file_path.stem

        # @llm-comm-start
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
        module_docstring = ast.get_docstring(tree)
        imports_internal = []
        imports_external = []
        # @llm-comm-end

        # @llm-comm-start
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
        if not exports:
            exports = [c['name'] for c in classes if not c['name'].startswith('_')]
            exports += [f['name'] for f in functions if not f['name'].startswith('_')]
        # @llm-comm-end

        # @llm-comm-start
        lines_of_code = len(content.split('\n'))
        # @llm-comm-end

        # @llm-comm-start
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
        # @llm-comm-start
        project_root = project_root or self.project_root
        relationships = []
        # @llm-comm-end

        # @llm-comm-start
        if restrict_to_files:
            python_files = [Path(f) if Path(f).is_absolute() else (project_root / f) for f in restrict_to_files]
        else:
            python_files = list(project_root.rglob('*.py'))
        # @llm-comm-end

        # @llm-comm-start
        for file_path in python_files:
            try:
                # @llm-comm-start
                content = file_path.read_text(encoding='utf-8')
                tree = ast.parse(content, filename=str(file_path))
                from_module = self._get_module_path(file_path, project_root)
                # @llm-comm-end

                # @llm-comm-start
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
        # @llm-comm-start
        project_root = project_root or self.project_root
        entry_points = {}
        # @llm-comm-end

        # @llm-comm-start
        main_file = project_root / '__main__.py'
        if main_file.exists():
            entry_points['main'] = str(main_file)
        # @llm-comm-end

        # @llm-comm-start
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

        setup_py = project_root / 'setup.py'

        # @llm-comm-start
        if setup_py.exists():
            try:
                content = setup_py.read_text(encoding='utf-8')
                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        if isinstance(node.func, ast.Name) and node.func.id == 'setup':
                            for keyword in node.keywords:
                                if keyword.arg == 'entry_points':
                                    entry_points['setup'] = str(setup_py)
                                    break
            except Exception:
                pass
        # @llm-comm-end

        return entry_points
    # @llm-doc-end

    # @llm-doc-start
    def calculate_metrics(self, file_path: str) -> Dict[str, any]:
        file_path = Path(file_path)

        # @llm-comm-start
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
        num_functions = sum(1 for node in ast.walk(tree) if isinstance(node, ast.FunctionDef))
        num_classes = sum(1 for node in ast.walk(tree) if isinstance(node, ast.ClassDef))
        lines_of_code = len(content.split('\n'))
        # @llm-comm-end

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
        if import_name.startswith('.'):
            return False

        project_name = self.project_root.name
        if import_name.startswith(project_name):
            return True

        return False
    # @llm-doc-end

    # @llm-doc-start
    def _get_module_path(self, file_path: Path, project_root: Path) -> str:
        try:
            relative = file_path.relative_to(project_root)
            parts = list(relative.parts[:-1]) + [relative.stem]
            return '.'.join(parts)
        except ValueError:
            return file_path.stem
    # @llm-doc-end
# @llm-class-end
# @llm-module-end