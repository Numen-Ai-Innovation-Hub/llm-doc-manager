"""
Documentation generator orchestrator.

This module coordinates the entire documentation generation process,
using AST analysis, LLM prompts, and template rendering to create
comprehensive project documentation.
"""

import ast
import json
import logging
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict

from llm_doc_manager.src.config import Config
from llm_doc_manager.src.database import DatabaseManager
from llm_doc_manager.src.detector import ChangeDetector
from llm_doc_manager.utils.ast_analyzer import ASTAnalyzer, ModuleInfo


logger = logging.getLogger(__name__)


@dataclass
class DocsMetadata:
    """Metadata for generated documentation."""
    generated_at: str
    source_files: List[str]
    module_count: int
    total_loc: int
    entry_points: List[str]
    architecture_pattern: str


class DocsGenerator:
    """
    Orchestrates documentation generation for entire project.

    This class coordinates:
    - AST analysis of all source files
    - LLM-based content generation
    - Template rendering
    - docs/ structure creation
    - index.json generation
    - Incremental regeneration
    """

    def __init__(
        self,
        config: Config,
        db: DatabaseManager,
        detector: ChangeDetector,
        llm_client: Any
    ):
        """
        Initialize documentation generator.

        Args:
            config: Application configuration
            db: Database connection
            detector: Change detector for incremental updates
            llm_client: LLM client (must have _call_llm method)
        """
        self.config = config
        self.db = db
        self.detector = detector
        self.llm = llm_client

        # Paths
        self.project_root = Path(config.project_root)
        self.analyzer = ASTAnalyzer(self.project_root)
        self.docs_dir = self.project_root / "docs"
        self.module_dir = self.docs_dir / "module"
        self.templates_dir = Path(__file__).parent.parent / "templates"

        # Cache for AST analysis results
        self._module_cache: Dict[str, ModuleInfo] = {}
        self._import_graph: Optional[Dict[str, List[str]]] = None

    def generate_all_docs(self, force: bool = False) -> Dict[str, Any]:
        """
        Generate complete documentation suite.

        This is the main entry point that coordinates all documentation
        generation steps in the correct order.

        Args:
            force: If True, regenerate all docs even if unchanged

        Returns:
            Dictionary with generation results and statistics
        """
        logger.info("Starting documentation generation")
        start_time = datetime.now()

        results = {
            "generated_files": [],
            "skipped_files": [],
            "errors": [],
            "metadata": None
        }

        try:
            # 1. Create docs/ structure
            self._create_docs_structure()

            # 2. Analyze all Python modules
            logger.info("Analyzing Python modules with AST")
            modules = self._analyze_all_modules()
            logger.info(f"Analyzed {len(modules)} modules")

            # 3. Build import graph
            logger.info("Building import dependency graph")
            self._import_graph = self.analyzer.build_import_graph()

            # 4. Detect entry points
            logger.info("Detecting entry points")
            entry_points = self.analyzer.detect_entry_points()

            # 5. Calculate project-level metrics
            total_loc = sum(m.lines_of_code for m in modules.values())

            # 6. Detect architecture pattern
            architecture_pattern = self._detect_architecture_pattern(modules)

            # 7. Create metadata object
            metadata = DocsMetadata(
                generated_at=datetime.now().isoformat(),
                source_files=list(modules.keys()),
                module_count=len(modules),
                total_loc=total_loc,
                entry_points=entry_points,
                architecture_pattern=architecture_pattern
            )
            results["metadata"] = asdict(metadata)

            # 8. Generate each documentation file
            # Order matters - some docs reference others

            # 8.1 README (executive summary)
            readme_result = self._generate_readme(modules, metadata, force)
            if readme_result["generated"]:
                results["generated_files"].append("docs/readme.md")
            else:
                results["skipped_files"].append("docs/readme.md")

            # 8.2 Architecture
            arch_result = self._generate_architecture(modules, metadata, force)
            if arch_result["generated"]:
                results["generated_files"].append("docs/architecture.md")
            else:
                results["skipped_files"].append("docs/architecture.md")

            # 8.3 Glossary
            glossary_result = self._generate_glossary(modules, metadata, force)
            if glossary_result["generated"]:
                results["generated_files"].append("docs/glossary.md")
            else:
                results["skipped_files"].append("docs/glossary.md")

            # 8.4 Development Journal (whereiwas)
            whereiwas_result = self._generate_whereiwas(metadata, force)
            if whereiwas_result["generated"]:
                results["generated_files"].append("docs/whereiwas.md")
            else:
                results["skipped_files"].append("docs/whereiwas.md")

            # 8.5 Module-level API docs
            for module_path, module_info in modules.items():
                module_result = self._generate_module_doc(
                    module_path,
                    module_info,
                    modules,
                    force
                )
                if module_result["generated"]:
                    results["generated_files"].append(module_result["doc_path"])
                else:
                    results["skipped_files"].append(module_result["doc_path"])

            # 8.6 index.json (complete metadata for RAG)
            index_result = self._generate_index_json(modules, metadata, force)
            if index_result["generated"]:
                results["generated_files"].append("docs/index.json")
            else:
                results["skipped_files"].append("docs/index.json")

            # 8.7 index.md (navigation hub)
            # Must be last - references all other files
            index_md_result = self._generate_index_md(modules, metadata, force)
            if index_md_result["generated"]:
                results["generated_files"].append("docs/index.md")
            else:
                results["skipped_files"].append("docs/index.md")

            # 9. Validate generated documentation
            validation_errors = self._validate_generated_docs()
            results["errors"].extend(validation_errors)

            duration = (datetime.now() - start_time).total_seconds()
            logger.info(
                f"Documentation generation completed in {duration:.2f}s. "
                f"Generated: {len(results['generated_files'])}, "
                f"Skipped: {len(results['skipped_files'])}, "
                f"Errors: {len(results['errors'])}"
            )

        except Exception as e:
            logger.exception("Documentation generation failed")
            results["errors"].append(f"Fatal error: {str(e)}")

        return results

    def _create_docs_structure(self) -> None:
        """Create docs/ directory structure."""
        self.docs_dir.mkdir(exist_ok=True)
        self.module_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Created docs structure at {self.docs_dir}")

    def _analyze_all_modules(self) -> Dict[str, ModuleInfo]:
        """
        Analyze all Python modules in project.

        Returns:
            Dictionary mapping relative module paths to ModuleInfo objects
        """
        modules = {}

        # Find all Python files
        python_files = list(self.project_root.rglob("*.py"))

        for file_path in python_files:
            # Skip non-source files
            if self._should_skip_file(file_path):
                continue

            try:
                relative_path = file_path.relative_to(self.project_root)
                module_info = self.analyzer.extract_module_info(str(file_path))
                modules[str(relative_path)] = module_info
                self._module_cache[str(relative_path)] = module_info

            except Exception as e:
                logger.warning(f"Failed to analyze {file_path}: {e}")

        return modules

    def _should_skip_file(self, file_path: Path) -> bool:
        """Determine if file should be skipped in analysis."""
        skip_patterns = [
            "__pycache__",
            ".git",
            ".venv",
            "venv",
            "env",
            ".pytest_cache",
            "build",
            "dist",
            ".egg-info"
        ]

        return any(pattern in str(file_path) for pattern in skip_patterns)

    def _detect_architecture_pattern(
        self,
        modules: Dict[str, ModuleInfo]
    ) -> str:
        """
        Detect architectural pattern from module structure.

        Analyzes directory structure and dependencies to identify
        common patterns: Layered, MVC, Clean Architecture, Pipeline, etc.

        Args:
            modules: Dictionary of analyzed modules

        Returns:
            Architecture pattern name
        """
        # Get directory structure
        directories = set()
        for path in modules.keys():
            parts = Path(path).parts
            if len(parts) > 1:
                directories.add(parts[0])

        # Pattern detection heuristics

        # Layered: presence of ui/cli, core/domain, data/infrastructure
        layered_indicators = {"ui", "cli", "core", "domain", "data", "infrastructure"}
        if len(directories & layered_indicators) >= 2:
            return "Layered Architecture"

        # MVC: models, views, controllers
        mvc_indicators = {"models", "views", "controllers", "templates"}
        if len(directories & mvc_indicators) >= 2:
            return "MVC"

        # Clean Architecture: entities, usecases, adapters
        clean_indicators = {"entities", "usecases", "use_cases", "adapters", "interfaces"}
        if len(directories & clean_indicators) >= 2:
            return "Clean Architecture"

        # Pipeline: stages, pipeline, processors
        pipeline_indicators = {"pipeline", "stages", "processors"}
        if len(directories & pipeline_indicators) >= 1:
            return "Pipeline Architecture"

        # Flat with utils: common in tools/scripts
        if "utils" in directories or "helpers" in directories:
            return "Utility-based Architecture"

        return "Custom Architecture"

    def _generate_readme(
        self,
        modules: Dict[str, ModuleInfo],
        metadata: DocsMetadata,
        force: bool
    ) -> Dict[str, Any]:
        """
        Generate docs/readme.md (executive summary).

        Args:
            modules: All analyzed modules
            metadata: Project metadata
            force: Force regeneration

        Returns:
            Result dictionary with 'generated' flag and 'content'
        """
        logger.info("Generating readme.md")

        doc_path = self.docs_dir / "readme.md"

        # Check if regeneration needed
        if not force and self._is_doc_current("docs/readme.md", modules):
            logger.debug("readme.md is current, skipping")
            return {"generated": False, "doc_path": "docs/readme.md"}

        # Load template
        template = self._load_template("docs_readme.md")

        # Prepare context
        context = self._prepare_readme_context(modules, metadata)

        # Render with LLM
        try:
            content = self._render_with_llm(template, context)

            # Write to file
            doc_path.write_text(content, encoding="utf-8")

            # Store in database
            self._store_doc_metadata(
                doc_path="docs/readme.md",
                doc_type="readme",
                source_files=list(modules.keys()),
                content=content
            )

            logger.info(f"Generated {doc_path}")
            return {"generated": True, "doc_path": "docs/readme.md", "content": content}

        except Exception as e:
            logger.error(f"Failed to generate readme.md: {e}")
            raise

    def _generate_architecture(
        self,
        modules: Dict[str, ModuleInfo],
        metadata: DocsMetadata,
        force: bool
    ) -> Dict[str, Any]:
        """Generate docs/architecture.md."""
        logger.info("Generating architecture.md")

        doc_path = self.docs_dir / "architecture.md"

        if not force and self._is_doc_current("docs/architecture.md", modules):
            logger.debug("architecture.md is current, skipping")
            return {"generated": False, "doc_path": "docs/architecture.md"}

        template = self._load_template("docs_architecture.md")
        context = self._prepare_architecture_context(modules, metadata)

        try:
            content = self._render_with_llm(template, context)
            doc_path.write_text(content, encoding="utf-8")

            self._store_doc_metadata(
                doc_path="docs/architecture.md",
                doc_type="architecture",
                source_files=list(modules.keys()),
                content=content
            )

            logger.info(f"Generated {doc_path}")
            return {"generated": True, "doc_path": "docs/architecture.md", "content": content}

        except Exception as e:
            logger.error(f"Failed to generate architecture.md: {e}")
            raise

    def _generate_glossary(
        self,
        modules: Dict[str, ModuleInfo],
        metadata: DocsMetadata,
        force: bool
    ) -> Dict[str, Any]:
        """Generate docs/glossary.md."""
        logger.info("Generating glossary.md")

        doc_path = self.docs_dir / "glossary.md"

        if not force and self._is_doc_current("docs/glossary.md", modules):
            logger.debug("glossary.md is current, skipping")
            return {"generated": False, "doc_path": "docs/glossary.md"}

        template = self._load_template("docs_glossary.md")
        context = self._prepare_glossary_context(modules, metadata)

        try:
            content = self._render_with_llm(template, context)
            doc_path.write_text(content, encoding="utf-8")

            self._store_doc_metadata(
                doc_path="docs/glossary.md",
                doc_type="glossary",
                source_files=list(modules.keys()),
                content=content
            )

            logger.info(f"Generated {doc_path}")
            return {"generated": True, "doc_path": "docs/glossary.md", "content": content}

        except Exception as e:
            logger.error(f"Failed to generate glossary.md: {e}")
            raise

    def _generate_whereiwas(
        self,
        metadata: DocsMetadata,
        force: bool
    ) -> Dict[str, Any]:
        """Generate docs/whereiwas.md (development journal)."""
        logger.info("Generating whereiwas.md")

        doc_path = self.docs_dir / "whereiwas.md"

        # whereiwas uses git history, different change detection
        if not force and doc_path.exists():
            # Check if git history has new commits since last generation
            last_gen_time = self._get_last_generation_time("docs/whereiwas.md")
            if last_gen_time and not self._has_new_commits_since(last_gen_time):
                logger.debug("whereiwas.md is current, skipping")
                return {"generated": False, "doc_path": "docs/whereiwas.md"}

        template = self._load_template("docs_whereiwas.md")
        context = self._prepare_whereiwas_context(metadata)

        try:
            content = self._render_with_llm(template, context)
            doc_path.write_text(content, encoding="utf-8")

            self._store_doc_metadata(
                doc_path="docs/whereiwas.md",
                doc_type="whereiwas",
                source_files=[],  # No specific source files
                content=content
            )

            logger.info(f"Generated {doc_path}")
            return {"generated": True, "doc_path": "docs/whereiwas.md", "content": content}

        except Exception as e:
            logger.error(f"Failed to generate whereiwas.md: {e}")
            raise

    def _generate_module_doc(
        self,
        module_path: str,
        module_info: ModuleInfo,
        all_modules: Dict[str, ModuleInfo],
        force: bool
    ) -> Dict[str, Any]:
        """
        Generate complete documentation for a single module.

        Creates docs/module/path/to/module.md with:
        - YAML front matter
        - Overview and purpose
        - Dependencies
        - API reference
        - Usage examples
        - Related modules

        Args:
            module_path: Relative path to module (e.g., "src/generator.py")
            module_info: AST analysis results
            all_modules: All modules (for dependency resolution)
            force: Force regeneration

        Returns:
            Result dictionary
        """
        logger.debug(f"Generating documentation for {module_path}")

        # Calculate doc path (mirror source structure in module/)
        module_parts = Path(module_path).with_suffix("").parts
        doc_rel_path = Path("docs/module") / Path(*module_parts).with_suffix(".md")
        doc_path = self.project_root / doc_rel_path

        if not force and self._is_doc_current(str(doc_rel_path), {module_path: module_info}):
            logger.debug(f"{doc_rel_path} is current, skipping")
            return {"generated": False, "doc_path": str(doc_rel_path)}

        # Create parent directories
        doc_path.parent.mkdir(parents=True, exist_ok=True)

        template = self._load_template("docs_module.md")
        context = self._prepare_module_context(module_path, module_info, all_modules)

        try:
            content = self._render_with_llm(template, context)
            doc_path.write_text(content, encoding="utf-8")

            self._store_doc_metadata(
                doc_path=str(doc_rel_path),
                doc_type="module",
                source_files=[module_path],
                content=content,
                metadata=self._extract_module_metadata(module_info)
            )

            logger.debug(f"Generated {doc_rel_path}")
            return {"generated": True, "doc_path": str(doc_rel_path), "content": content}

        except Exception as e:
            logger.error(f"Failed to generate docs for {module_path}: {e}")
            raise

    def _generate_index_json(
        self,
        modules: Dict[str, ModuleInfo],
        metadata: DocsMetadata,
        force: bool
    ) -> Dict[str, Any]:
        """
        Generate docs/index.json (complete project metadata for RAG).

        This JSON file contains:
        - Project metadata
        - All modules with complete info
        - Import graph
        - Entry points
        - Statistics

        Args:
            modules: All analyzed modules
            metadata: Project metadata
            force: Force regeneration

        Returns:
            Result dictionary
        """
        logger.info("Generating index.json")

        doc_path = self.docs_dir / "index.json"

        if not force and self._is_doc_current("docs/index.json", modules):
            logger.debug("index.json is current, skipping")
            return {"generated": False, "doc_path": "docs/index.json"}

        # Build complete index
        index = {
            "metadata": asdict(metadata),
            "modules": {},
            "import_graph": self._import_graph or {},
            "statistics": self._calculate_statistics(modules)
        }

        # Add each module's complete info
        for module_path, module_info in modules.items():
            index["modules"][module_path] = {
                "path": module_info.module_path,
                "name": module_info.module_name,
                "doc_path": f"docs/module/{module_path.replace('.py', '.md')}",
                "docstring": module_info.module_docstring,
                "imports_internal": module_info.imports_internal,
                "imports_external": module_info.imports_external,
                "exports": module_info.exports,
                "classes": [
                    {
                        "name": cls["name"],
                        "docstring": cls.get("docstring"),
                        "methods": [m["name"] for m in cls.get("methods", [])]
                    }
                    for cls in module_info.classes
                ],
                "functions": [
                    {
                        "name": func["name"],
                        "docstring": func.get("docstring"),
                        "signature": func.get("signature")
                    }
                    for func in module_info.functions
                ],
                "lines_of_code": module_info.lines_of_code,
                "complexity": module_info.complexity
            }

        # Write JSON
        try:
            with open(doc_path, "w", encoding="utf-8") as f:
                json.dump(index, f, indent=2, ensure_ascii=False)

            # Calculate hash for change detection
            content_str = json.dumps(index, sort_keys=True)

            self._store_doc_metadata(
                doc_path="docs/index.json",
                doc_type="index_json",
                source_files=list(modules.keys()),
                content=content_str
            )

            logger.info(f"Generated {doc_path}")
            return {"generated": True, "doc_path": "docs/index.json"}

        except Exception as e:
            logger.error(f"Failed to generate index.json: {e}")
            raise

    def _generate_index_md(
        self,
        modules: Dict[str, ModuleInfo],
        metadata: DocsMetadata,
        force: bool
    ) -> Dict[str, Any]:
        """
        Generate docs/index.md (navigation hub).

        This is the main landing page that links to all other docs.
        Must be generated last as it references all other files.

        Args:
            modules: All analyzed modules
            metadata: Project metadata
            force: Force regeneration

        Returns:
            Result dictionary
        """
        logger.info("Generating index.md")

        doc_path = self.docs_dir / "index.md"

        if not force and self._is_doc_current("docs/index.md", modules):
            logger.debug("index.md is current, skipping")
            return {"generated": False, "doc_path": "docs/index.md"}

        # Build content dynamically (no LLM needed)
        lines = [
            "# Documentation Index",
            "",
            f"**Generated**: {metadata.generated_at}",
            f"**Modules**: {metadata.module_count}",
            f"**Lines of Code**: {metadata.total_loc}",
            f"**Architecture**: {metadata.architecture_pattern}",
            "",
            "## Overview",
            "",
            "- [**README**](readme.md) - Executive summary and quick start",
            "- [**Architecture**](architecture.md) - System design and patterns",
            "- [**Glossary**](glossary.md) - Domain terminology",
            "- [**Development Journal**](whereiwas.md) - Project history and status",
            "",
            "## API Reference",
            "",
            "Complete module documentation:",
            ""
        ]

        # Group modules by top-level directory
        modules_by_dir: Dict[str, List[str]] = {}
        for module_path in sorted(modules.keys()):
            parts = Path(module_path).parts
            top_dir = parts[0] if len(parts) > 1 else "root"
            if top_dir not in modules_by_dir:
                modules_by_dir[top_dir] = []
            modules_by_dir[top_dir].append(module_path)

        # Add links to each module doc
        for dir_name in sorted(modules_by_dir.keys()):
            lines.append(f"### {dir_name}/")
            lines.append("")

            for module_path in modules_by_dir[dir_name]:
                module_info = modules[module_path]
                # Convert src/generator.py -> module/src/generator.md
                doc_path = Path("module") / Path(module_path).with_suffix(".md")

                # Extract brief description from docstring
                brief = module_info.module_docstring or "No description"
                if len(brief) > 100:
                    brief = brief[:97] + "..."

                lines.append(f"- [**{module_info.module_name}**]({doc_path}) - {brief}")

            lines.append("")

        lines.extend([
            "## Metadata",
            "",
            "- [**index.json**](index.json) - Complete project metadata (JSON format for RAG/LLM)",
            "",
            "---",
            "",
            f"**Auto-generated**: Yes | **Last Updated**: {metadata.generated_at}"
        ])

        content = "\n".join(lines)

        try:
            doc_path.write_text(content, encoding="utf-8")

            self._store_doc_metadata(
                doc_path="docs/index.md",
                doc_type="index_md",
                source_files=list(modules.keys()),
                content=content
            )

            logger.info(f"Generated {doc_path}")
            return {"generated": True, "doc_path": "docs/index.md", "content": content}

        except Exception as e:
            logger.error(f"Failed to generate index.md: {e}")
            raise

    # ========================================================================
    # HELPER METHODS: Context Preparation
    # ========================================================================

    def _prepare_readme_context(
        self,
        modules: Dict[str, ModuleInfo],
        metadata: DocsMetadata
    ) -> Dict[str, str]:
        """Prepare context for README template."""
        # Extract project info from setup.py or pyproject.toml if exists
        project_name = self.project_root.name
        version = "0.1.0"  # Default
        description = "Python project"  # Default

        # Try to read from pyproject.toml
        pyproject = self.project_root / "pyproject.toml"
        if pyproject.exists():
            # Simple extraction (could use toml library)
            content = pyproject.read_text()
            for line in content.split("\n"):
                if line.startswith("name"):
                    project_name = line.split("=")[1].strip().strip('"')
                elif line.startswith("version"):
                    version = line.split("=")[1].strip().strip('"')
                elif line.startswith("description"):
                    description = line.split("=")[1].strip().strip('"')

        # Build project structure representation
        structure_lines = []
        for module_path in sorted(modules.keys()):
            structure_lines.append(f"  {module_path}")
        project_structure = "\n".join(structure_lines[:20])  # First 20 files

        # Identify key components (most imported modules)
        import_counts = {}
        for module_path, module_info in modules.items():
            import_counts[module_path] = len(module_info.imports_internal)
        key_components = sorted(
            import_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:7]

        key_components_str = "\n".join([
            f"- {path}: {modules[path].module_docstring or 'No description'}"
            for path, _ in key_components
        ])

        # Tech stack
        external_deps = set()
        for module_info in modules.values():
            external_deps.update(module_info.imports_external)
        tech_stack = "\n".join([f"- {dep}" for dep in sorted(external_deps)[:10]])

        return {
            "project_name": project_name,
            "version": version,
            "description": description,
            "project_structure": project_structure,
            "key_components": key_components_str,
            "entry_points": "\n".join([f"- {ep}" for ep in metadata.entry_points]),
            "tech_stack": tech_stack,
            "existing_readme": ""  # Could read from root README if exists
        }

    def _prepare_architecture_context(
        self,
        modules: Dict[str, ModuleInfo],
        metadata: DocsMetadata
    ) -> Dict[str, str]:
        """Prepare context for architecture template."""
        # Build import graph representation
        import_graph_str = json.dumps(self._import_graph or {}, indent=2)

        # Modules info (summary)
        modules_info_lines = []
        for path, info in list(modules.items())[:20]:  # First 20
            modules_info_lines.append(
                f"{path}: {info.lines_of_code} LOC, "
                f"{len(info.classes)} classes, {len(info.functions)} functions"
            )
        modules_info = "\n".join(modules_info_lines)

        # Directory structure
        dirs = set()
        for path in modules.keys():
            parts = Path(path).parts
            for i in range(len(parts)):
                dirs.add("/".join(parts[:i+1]))
        directory_structure = "\n".join(sorted(dirs))

        # Metrics
        metrics = self._calculate_statistics(modules)
        metrics_str = json.dumps(metrics, indent=2)

        return {
            "import_graph": import_graph_str,
            "modules_info": modules_info,
            "directory_structure": directory_structure,
            "entry_points": "\n".join([f"- {ep}" for ep in metadata.entry_points]),
            "metrics": metrics_str
        }

    def _prepare_glossary_context(
        self,
        modules: Dict[str, ModuleInfo],
        metadata: DocsMetadata
    ) -> Dict[str, str]:
        """Prepare context for glossary template."""
        # Extract all docstrings
        module_docstrings = [
            f"## {info.module_name}\n{info.module_docstring or 'No docstring'}"
            for info in modules.values()
        ]

        # Extract class definitions
        class_definitions = []
        for module_info in modules.values():
            for cls in module_info.classes:
                class_definitions.append(
                    f"**{cls['name']}**: {cls.get('docstring', 'No docstring')}"
                )

        # Extract function definitions
        function_definitions = []
        for module_info in modules.values():
            for func in module_info.functions:
                function_definitions.append(
                    f"**{func['name']}**: {func.get('docstring', 'No docstring')}"
                )

        # Important names (constants, enums)
        # This would require deeper AST analysis - simplified here
        important_names = "N/A"

        # Code comments - would need source parsing
        code_comments = "N/A"

        return {
            "module_docstrings": "\n\n".join(module_docstrings[:20]),
            "class_definitions": "\n".join(class_definitions[:30]),
            "function_definitions": "\n".join(function_definitions[:30]),
            "important_names": important_names,
            "code_comments": code_comments
        }

    def _prepare_whereiwas_context(
        self,
        metadata: DocsMetadata
    ) -> Dict[str, str]:
        """Prepare context for whereiwas template (git history)."""
        try:
            # Get git log (last 60 days)
            result = subprocess.run(
                [
                    "git", "log",
                    "--since=60 days ago",
                    "--pretty=format:%H|%an|%ae|%ad|%s",
                    "--date=iso"
                ],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                logger.warning(f"Git log failed: {result.stderr}")
                git_commits = "No git history available"
            else:
                git_commits = result.stdout

            # Get current branch
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=5
            )
            current_branch = result.stdout.strip() if result.returncode == 0 else "unknown"

            # Count commits
            commits_list = git_commits.split("\n") if git_commits != "No git history available" else []
            commit_count = len([c for c in commits_list if c.strip()])

            # Extract contributors
            contributors = set()
            for commit in commits_list:
                if "|" in commit:
                    parts = commit.split("|")
                    if len(parts) >= 3:
                        contributors.add(f"{parts[1]} <{parts[2]}>")

            # Date range
            if commits_list:
                first_date = commits_list[-1].split("|")[3] if len(commits_list[-1].split("|")) >= 4 else "unknown"
                last_date = commits_list[0].split("|")[3] if len(commits_list[0].split("|")) >= 4 else "unknown"
                date_range = f"{first_date} to {last_date}"
            else:
                date_range = "N/A"

        except Exception as e:
            logger.warning(f"Failed to get git history: {e}")
            git_commits = "Git not available or not a git repository"
            current_branch = "unknown"
            commit_count = 0
            contributors = set()
            date_range = "N/A"

        return {
            "git_commits": git_commits,
            "current_branch": current_branch,
            "commit_count": str(commit_count),
            "date_range": date_range,
            "contributors": ", ".join(sorted(contributors)),
            "version": "0.1.0",  # Would read from setup
            "last_release": "N/A",
            "open_issues": "N/A"
        }

    def _prepare_module_context(
        self,
        module_path: str,
        module_info: ModuleInfo,
        all_modules: Dict[str, ModuleInfo]
    ) -> Dict[str, str]:
        """Prepare context for module documentation template."""
        # Find dependencies (modules that import this one)
        depends_on = module_info.imports_internal
        used_by = [
            path for path, info in all_modules.items()
            if module_path in info.imports_internal
        ]

        # Read source code
        source_path = self.project_root / module_path
        try:
            source_code = source_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Could not read source for {module_path}: {e}")
            source_code = "Source code not available"

        # Calculate source hash
        source_hash = hashlib.sha256(source_code.encode()).hexdigest()

        # Format classes
        classes_str = json.dumps(module_info.classes, indent=2)

        # Format functions
        functions_str = json.dumps(module_info.functions, indent=2)

        return {
            "module_path": module_path,
            "module_name": module_info.module_name,
            "module_docstring": module_info.module_docstring or "No module docstring",
            "classes": classes_str,
            "functions": functions_str,
            "imports_internal": ", ".join(module_info.imports_internal) or "None",
            "imports_external": ", ".join(module_info.imports_external) or "None",
            "exports": ", ".join(module_info.exports) or "None",
            "loc": str(module_info.lines_of_code),
            "complexity": module_info.complexity,
            "has_tests": str(self._has_tests(module_path)),
            "depends_on": ", ".join(depends_on) or "None",
            "used_by": ", ".join(used_by) or "None",
            "source_code": source_code[:5000],  # Limit to 5000 chars
            "source_hash": source_hash
        }

    # ========================================================================
    # HELPER METHODS: Utilities
    # ========================================================================

    def _load_template(self, template_name: str) -> str:
        """Load template file from templates/ directory."""
        template_path = self.templates_dir / template_name
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")
        return template_path.read_text(encoding="utf-8")

    def _render_with_llm(self, template: str, context: Dict[str, str]) -> str:
        """
        Render template with context using LLM.

        Args:
            template: Template content with {placeholders}
            context: Dictionary of values to fill in

        Returns:
            Generated content from LLM
        """
        # Fill in template placeholders
        prompt = template
        for key, value in context.items():
            placeholder = f"{{{key}}}"
            prompt = prompt.replace(placeholder, str(value))

        # Call LLM (via processor's _call_llm method)
        response, _ = self.llm._call_llm(prompt)
        return response

    def _is_doc_current(
        self,
        doc_path: str,
        source_modules: Dict[str, ModuleInfo]
    ) -> bool:
        """
        Check if documentation is current (source hasn't changed).

        Args:
            doc_path: Relative path to doc file
            source_modules: Source modules that contribute to this doc

        Returns:
            True if doc is current, False if needs regeneration
        """
        # Query database for last generation
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT source_hash FROM generated_documentation WHERE doc_path = ?",
            (doc_path,)
        )
        result = cursor.fetchone()

        if not result:
            return False  # Never generated

        stored_hash = result[0]

        # Calculate current hash of source files
        current_hash = self._calculate_combined_hash(source_modules)

        return stored_hash == current_hash

    def _calculate_combined_hash(
        self,
        modules: Dict[str, ModuleInfo]
    ) -> str:
        """Calculate combined hash of multiple source files."""
        hasher = hashlib.sha256()

        for module_path in sorted(modules.keys()):
            source_path = self.project_root / module_path
            try:
                content = source_path.read_bytes()
                hasher.update(content)
            except Exception as e:
                logger.warning(f"Could not hash {module_path}: {e}")

        return hasher.hexdigest()

    def _store_doc_metadata(
        self,
        doc_path: str,
        doc_type: str,
        source_files: List[str],
        content: str,
        metadata: Optional[Dict] = None
    ) -> None:
        """
        Store documentation metadata in database.

        Args:
            doc_path: Relative path to generated doc
            doc_type: Type of document (readme, architecture, module, etc.)
            source_files: List of source files this doc is based on
            content: Generated content (for hash calculation)
            metadata: Optional additional metadata (JSON)
        """
        # Calculate hashes
        source_hash = self._calculate_combined_hash({
            path: self._module_cache.get(path)
            for path in source_files
            if path in self._module_cache
        })
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        # Convert metadata to JSON
        metadata_json = json.dumps(metadata) if metadata else None

        # Upsert into database
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO generated_documentation
            (doc_path, doc_type, file_path, source_hash, content_hash, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(doc_path) DO UPDATE SET
                doc_type = excluded.doc_type,
                file_path = excluded.file_path,
                source_hash = excluded.source_hash,
                content_hash = excluded.content_hash,
                metadata = excluded.metadata,
                generated_at = CURRENT_TIMESTAMP
        """, (
            doc_path,
            doc_type,
            ",".join(source_files),  # Store as comma-separated
            source_hash,
            content_hash,
            metadata_json
        ))
        conn.commit()

    def _extract_module_metadata(self, module_info: ModuleInfo) -> Dict:
        """Extract metadata from ModuleInfo for storage."""
        return {
            "classes": [cls["name"] for cls in module_info.classes],
            "functions": [func["name"] for func in module_info.functions],
            "exports": module_info.exports,
            "imports_count": len(module_info.imports_internal) + len(module_info.imports_external),
            "complexity": module_info.complexity,
            "loc": module_info.lines_of_code
        }

    def _calculate_statistics(
        self,
        modules: Dict[str, ModuleInfo]
    ) -> Dict[str, Any]:
        """Calculate project-wide statistics."""
        total_loc = sum(m.lines_of_code for m in modules.values())
        total_classes = sum(len(m.classes) for m in modules.values())
        total_functions = sum(len(m.functions) for m in modules.values())

        complexity_counts = {"low": 0, "medium": 0, "high": 0, "very_high": 0}
        for module in modules.values():
            complexity_counts[module.complexity] += 1

        return {
            "total_modules": len(modules),
            "total_loc": total_loc,
            "total_classes": total_classes,
            "total_functions": total_functions,
            "avg_loc_per_module": total_loc // len(modules) if modules else 0,
            "complexity_distribution": complexity_counts
        }

    def _has_tests(self, module_path: str) -> bool:
        """Check if module has associated tests."""
        # Look for test_<module>.py or tests/<module>/test_*.py
        module_name = Path(module_path).stem

        test_patterns = [
            self.project_root / "tests" / f"test_{module_name}.py",
            self.project_root / "test" / f"test_{module_name}.py",
            self.project_root / f"test_{module_name}.py"
        ]

        return any(p.exists() for p in test_patterns)

    def _get_last_generation_time(self, doc_path: str) -> Optional[datetime]:
        """Get timestamp of last generation for a doc."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT generated_at FROM generated_documentation WHERE doc_path = ?",
            (doc_path,)
        )
        result = cursor.fetchone()

        if result:
            return datetime.fromisoformat(result[0])
        return None

    def _has_new_commits_since(self, timestamp: datetime) -> bool:
        """Check if there are new git commits since timestamp."""
        try:
            result = subprocess.run(
                [
                    "git", "log",
                    f"--since={timestamp.isoformat()}",
                    "--oneline"
                ],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=5
            )

            return bool(result.stdout.strip())
        except Exception as e:
            logger.warning(f"Could not check git history: {e}")
            return True  # Assume changed if can't verify

    def _validate_generated_docs(self) -> List[str]:
        """
        Validate generated documentation for common issues.

        Returns:
            List of validation errors
        """
        errors = []

        # Check all expected files exist
        expected_files = [
            "docs/readme.md",
            "docs/index.md",
            "docs/architecture.md",
            "docs/glossary.md",
            "docs/whereiwas.md",
            "docs/index.json"
        ]

        for file_path in expected_files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                errors.append(f"Missing expected file: {file_path}")

        # Validate index.json is valid JSON
        index_json_path = self.docs_dir / "index.json"
        if index_json_path.exists():
            try:
                json.loads(index_json_path.read_text())
            except json.JSONDecodeError as e:
                errors.append(f"Invalid JSON in index.json: {e}")

        # Could add more validations:
        # - YAML front matter parsing
        # - Link validation
        # - Markdown syntax check

        return errors