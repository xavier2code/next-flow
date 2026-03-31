"""LLM factory: create LangChain ChatModel instances based on provider configuration.

Per D-07: Simple factory function get_llm(config) to create instances.
Per D-08: API keys and URLs from environment variables via Settings.
Per D-09: Configurable default provider and model via Settings.
Per D-10: LLM instances created with streaming=True by default.
"""

from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from app.core.config import settings


def get_llm(config: dict | None = None) -> ChatOpenAI | ChatOllama:
    """Create an LLM instance from agent config or Settings defaults.

    Args:
        config: Optional dict with keys: provider, model, temperature, max_tokens.
                Falls back to Settings defaults for missing keys.

    Returns:
        A LangChain ChatModel instance (ChatOpenAI or ChatOllama).

    Raises:
        ValueError: If the provider string is not recognized.
    """
    config = config or {}
    provider = config.get("provider", settings.default_provider)
    model = config.get("model", settings.default_model)
    temperature = config.get("temperature", 0.7)
    max_tokens = config.get("max_tokens", 4096)

    if provider == "openai":
        kwargs = dict(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            streaming=True,  # D-10
            api_key=settings.openai_api_key or None,
        )
        if settings.openai_api_base:
            kwargs["base_url"] = settings.openai_api_base
        return ChatOpenAI(**kwargs)
    elif provider == "ollama":
        return ChatOllama(
            model=model,
            temperature=temperature,
            num_predict=max_tokens,
            base_url=settings.ollama_base_url,
        )

    raise ValueError(f"Unknown provider: {provider}")
