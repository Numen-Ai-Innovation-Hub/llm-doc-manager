"""
Configuration management for LLM Doc Manager.

Handles loading, saving, and validating configuration settings.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field, asdict

from ..utils.logger_setup import get_logger

logger = get_logger(__name__)

# Load environment variables from .env file in tool's directory
try:
    from dotenv import load_dotenv
    # Get the tool's root directory (parent of llm_doc_manager package)
    TOOL_ROOT = Path(__file__).parent.parent.parent
    ENV_FILE = TOOL_ROOT / ".env"
    if ENV_FILE.exists():
        load_dotenv(ENV_FILE)
except ImportError:
    pass  # python-dotenv not installed, skip


@dataclass
class LLMConfig:
    """LLM provider configuration."""
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.5
    max_tokens: int = 4000

    def __post_init__(self):
        """Load configuration from environment variables based on provider."""
        # Map provider to environment variable prefix
        prefix_map = {
            'openai': 'OPENAI',
            'anthropic': 'ANTHROPIC',
            'ollama': 'OLLAMA'
        }

        prefix = prefix_map.get(self.provider.lower())
        if not prefix:
            raise ValueError(f"Provider '{self.provider}' não suportado. Use: {list(prefix_map.keys())}")

        # Load from environment if not explicitly set (allow override from code)
        self.provider = os.getenv(f"{prefix}_PROVIDER", self.provider)
        self.model = os.getenv(f"{prefix}_MODEL", self.model)

        # API key and base_url: load from env if not set
        if not self.api_key:
            self.api_key = os.getenv(f"{prefix}_API_KEY")
        if not self.base_url:
            base_url_env = os.getenv(f"{prefix}_BASE_URL")
            if base_url_env:  # Only set if env var is not empty
                self.base_url = base_url_env

        # Load temperature and max_tokens from env
        temp_str = os.getenv(f"{prefix}_TEMPERATURE")
        if temp_str:
            self.temperature = float(temp_str)

        max_tokens_str = os.getenv(f"{prefix}_MAX_TOKENS")
        if max_tokens_str:
            self.max_tokens = int(max_tokens_str)


@dataclass
class ScanningConfig:
    """File scanning configuration."""
    paths: List[str] = field(default_factory=lambda: ["."])
    exclude: List[str] = field(default_factory=lambda: [
        "*.pyc", "__pycache__", ".venv", "venv", ".git", "node_modules"
    ])
    max_file_size_mb: int = 5


@dataclass
class OutputConfig:
    """Output and application configuration."""
    mode: str = "interactive"  # interactive, auto, pr
    backup: bool = True
    backup_dir: str = ".llm-doc-manager/backups"


@dataclass
class Config:
    """Main configuration class."""
    llm: LLMConfig = field(default_factory=LLMConfig)
    scanning: ScanningConfig = field(default_factory=ScanningConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    project_root: str = field(default_factory=lambda: os.getcwd())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Config':
        """Create Config from dictionary."""
        return cls(
            llm=LLMConfig(**data.get('llm', {})),
            scanning=ScanningConfig(**data.get('scanning', {})),
            output=OutputConfig(**data.get('output', {})),
            project_root=data.get('project_root', os.getcwd())
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert Config to dictionary."""
        return {
            'llm': asdict(self.llm),
            'scanning': asdict(self.scanning),
            'output': asdict(self.output),
            'project_root': self.project_root
        }


class ConfigManager:
    """Manages configuration loading, saving, and resolution."""

    DEFAULT_CONFIG_DIR = ".llm-doc-manager"
    DEFAULT_CONFIG_FILE = "config.yaml"

    def __init__(self, project_root: Optional[str] = None):
        """
        Initialize ConfigManager.

        Args:
            project_root: Root directory of the project. If None, uses current directory.
        """
        self.project_root = Path(project_root or os.getcwd())
        self.config_dir = self.project_root / self.DEFAULT_CONFIG_DIR
        self.config_file = self.config_dir / self.DEFAULT_CONFIG_FILE

    def load(self) -> Config:
        """
        Load configuration from file or create default.

        Returns:
            Loaded or default configuration
        """
        if self.config_file.exists():
            config = self._load_from_file()
        else:
            config = Config()

        # Ensure project_root is set from ConfigManager
        config.project_root = str(self.project_root)
        return config

    def _load_from_file(self) -> Config:
        """Load configuration from YAML file."""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}

            # Resolve environment variables
            data = self._resolve_env_vars(data)

            # Ensure project_root is set
            if 'project_root' not in data:
                data['project_root'] = str(self.project_root)

            return Config.from_dict(data)
        except Exception as e:
            logger.warning(f"Error loading config file: {e}")
            logger.info("Using default configuration.")
            config = Config()
            config.project_root = str(self.project_root)
            return config

    def save(self, config: Config):
        """
        Save configuration to file.

        Args:
            config: Configuration to save
        """
        self.config_dir.mkdir(parents=True, exist_ok=True)

        with open(self.config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config.to_dict(), f, default_flow_style=False, sort_keys=False)

    def init_config(self, overwrite: bool = False) -> bool:
        """
        Initialize configuration file with defaults.

        Args:
            overwrite: Whether to overwrite existing config

        Returns:
            True if config was created/updated, False otherwise
        """
        # Check if config FILE exists, not just directory
        if self.config_file.exists() and not overwrite:
            logger.info(f"Configuration already exists at: {self.config_file}")
            return False

        # If overwrite is True and config file exists, remove it
        if overwrite and self.config_file.exists():
            self.config_file.unlink()
            logger.info(f"Removed existing configuration file")

        # Create directory structure if needed
        self.config_dir.mkdir(parents=True, exist_ok=True)

        default_config = Config()
        self.save(default_config)

        logger.info(f"Configuration initialized at: {self.config_file}")
        return True

    def _resolve_env_vars(self, data: Any) -> Any:
        """
        Recursively resolve environment variables in configuration.

        Supports ${VAR_NAME} syntax.
        """
        if isinstance(data, dict):
            return {k: self._resolve_env_vars(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._resolve_env_vars(item) for item in data]
        elif isinstance(data, str):
            # Replace ${VAR_NAME} with environment variable value
            if data.startswith('${') and data.endswith('}'):
                var_name = data[2:-1]
                return os.environ.get(var_name, data)
        return data

    def get_api_key(self, config: Config) -> Optional[str]:
        """
        Get API key from config or environment.

        Args:
            config: Configuration object

        Returns:
            API key or None
        """
        if config.llm.api_key:
            return config.llm.api_key

        # Try environment variables based on provider
        env_vars = {
            'anthropic': 'ANTHROPIC_API_KEY',
            'openai': 'OPENAI_API_KEY',
            'ollama': None  # Ollama doesn't need API key
        }

        env_var = env_vars.get(config.llm.provider.lower())
        if env_var:
            return os.environ.get(env_var)

        return None

    def validate(self, config: Config) -> List[str]:
        """
        Validate configuration.

        Args:
            config: Configuration to validate

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Validate LLM config
        if config.llm.provider not in ['anthropic', 'openai', 'ollama']:
            errors.append(f"Invalid LLM provider: {config.llm.provider}")

        api_key = self.get_api_key(config)
        if config.llm.provider != 'ollama' and not api_key:
            errors.append(f"API key not found for provider: {config.llm.provider}")

        # Validate output mode
        if config.output.mode not in ['interactive', 'auto', 'pr']:
            errors.append(f"Invalid output mode: {config.output.mode}")

        return errors

    def cleanup(self) -> bool:
        """
        Remove configuration directory and all its contents.

        Returns:
            True if cleanup was successful, False otherwise
        """
        if not self.config_dir.exists():
            logger.info(f"No configuration found at: {self.config_dir}")
            return False

        try:
            import shutil
            import logging

            # Close all logging handlers to release file locks (Windows issue)
            root_logger = logging.getLogger('llm_doc_manager')
            for handler in root_logger.handlers[:]:
                handler.close()
                root_logger.removeHandler(handler)

            # Now delete the directory
            shutil.rmtree(self.config_dir)
            return True
        except Exception as e:
            # Can't log here because logger is closed
            print(f"Error removing configuration: {e}")
            return False
