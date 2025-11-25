"""
LLM Client for unified LLM provider management.

Provides a clean abstraction over multiple LLM providers with automatic
client selection via Factory pattern.
"""

from abc import ABC, abstractmethod
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class BaseLLMClient(ABC):
    """Base class for all LLM clients."""

    def __init__(
        self,
        model: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.5,
        max_tokens: int = 4000
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

        # Inicializa o cliente específico
        self.client = self._init_client()

    @abstractmethod
    def _init_client(self):
        """Initialize provider-specific client."""
        pass

    @abstractmethod
    def call(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Tuple[str, int]:
        """
        Execute LLM call.

        Args:
            prompt: Texto do prompt
            temperature: Sobrescreve preset (opcional)
            max_tokens: Sobrescreve preset (opcional)

        Returns:
            Tuple[str, int]: (resposta_texto, total_tokens)
        """
        pass


class OpenAIClient(BaseLLMClient):
    """OpenAI LLM client."""

    def _init_client(self):
        """Initialize OpenAI client."""
        try:
            import openai
            if self.base_url:
                return openai.OpenAI(api_key=self.api_key, base_url=self.base_url)
            return openai.OpenAI(api_key=self.api_key)
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")

    def call(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Tuple[str, int]:
        temp = temperature if temperature is not None else self.temperature
        max_tok = max_tokens if max_tokens is not None else self.max_tokens

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temp,
                max_tokens=max_tok
            )
            tokens = response.usage.total_tokens
            return response.choices[0].message.content, tokens
        except Exception as e:
            logger.error(f"Erro ao chamar OpenAI API: {e}")
            raise


class AnthropicClient(BaseLLMClient):
    """Anthropic LLM client."""

    def _init_client(self):
        """Initialize Anthropic client."""
        try:
            import anthropic
            if self.base_url:
                return anthropic.Anthropic(api_key=self.api_key, base_url=self.base_url)
            return anthropic.Anthropic(api_key=self.api_key)
        except ImportError:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")

    def call(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Tuple[str, int]:
        temp = temperature if temperature is not None else self.temperature
        max_tok = max_tokens if max_tokens is not None else self.max_tokens

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tok,
                temperature=temp,
                messages=[{"role": "user", "content": prompt}]
            )
            tokens = response.usage.input_tokens + response.usage.output_tokens
            return response.content[0].text, tokens
        except Exception as e:
            logger.error(f"Erro ao chamar Anthropic API: {e}")
            raise


class OllamaClient(BaseLLMClient):
    """Ollama LLM client (local)."""

    def _init_client(self):
        """Initialize Ollama client."""
        try:
            import ollama
            return ollama.Client(host=self.base_url) if self.base_url else ollama.Client()
        except ImportError:
            raise ImportError("ollama package not installed. Run: pip install ollama")

    def call(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Tuple[str, int]:
        # Ollama não reporta tokens
        try:
            response = self.client.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}]
            )
            return response['message']['content'], 0
        except Exception as e:
            logger.error(f"Erro ao chamar Ollama API: {e}")
            raise


class LLMClientFactory:
    """Factory for creating LLM clients based on provider."""

    _providers = {
        'openai': OpenAIClient,
        'anthropic': AnthropicClient,
        'ollama': OllamaClient,
    }

    @classmethod
    def create(
        cls,
        provider: str,
        model: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.5,
        max_tokens: int = 4000
    ) -> BaseLLMClient:
        """
        Create LLM client based on provider.

        Args:
            provider: Nome do provider ('openai', 'anthropic', 'ollama')
            model: Nome do modelo
            api_key: API key (opcional para Ollama)
            base_url: URL base customizada (opcional)
            temperature: Temperature para geração (padrão: 0.5)
            max_tokens: Máximo de tokens para resposta (padrão: 4000)

        Returns:
            BaseLLMClient: Instância do cliente apropriado
        """
        provider = provider.lower()
        if provider not in cls._providers:
            raise ValueError(
                f"Provider '{provider}' não suportado. "
                f"Providers disponíveis: {list(cls._providers.keys())}"
            )

        client_class = cls._providers[provider]
        logger.info(f"Criando cliente {provider} (model={model}, temp={temperature}, max_tokens={max_tokens})")
        return client_class(
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens
        )