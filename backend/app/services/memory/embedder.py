"""Embedder factory: create LangChain Embeddings instances based on provider configuration.

Per D-22, D-23, D-25: Mirrors get_llm() pattern with openai/ollama provider routing.
Uses settings.embedding_provider and settings.embedding_model for defaults.
"""

from langchain_community.embeddings import OllamaEmbeddings
from langchain_openai import OpenAIEmbeddings

from app.core.config import settings


def get_embedder(config: dict | None = None) -> OpenAIEmbeddings | OllamaEmbeddings:
    """Create an Embeddings instance from config or Settings defaults.

    Args:
        config: Optional dict with keys: provider, model.
                Falls back to Settings defaults for missing keys.

    Returns:
        A LangChain Embeddings instance (OpenAIEmbeddings or OllamaEmbeddings).

    Raises:
        ValueError: If the embedding provider string is not recognized.
    """
    config = config or {}
    provider = config.get("provider", settings.embedding_provider)
    model = config.get("model", settings.embedding_model)

    if provider == "openai":
        return OpenAIEmbeddings(
            model=model,
            api_key=settings.openai_api_key or None,
        )
    elif provider == "ollama":
        return OllamaEmbeddings(
            model=model,
            base_url=settings.ollama_base_url,
        )

    raise ValueError(f"Unknown embedding provider: {provider}")
