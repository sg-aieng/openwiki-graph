from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from llama_index.core.llms import LLM
    from llama_index.core.embeddings import BaseEmbedding

from ..config import LLMConfig

# Native output dimensions for common embedding models.
# Used to pre-configure GraphRAGConfig.embed_dimensions so pgvector tables are
# created with the right column width on first run.  Bedrock's default is 1024;
# OpenAI models produce 1536 or 3072.  Override with the EMBEDDINGS_DIMENSIONS
# environment variable for any model not listed here.
_KNOWN_DIMENSIONS: dict[str, int] = {
    # OpenAI
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
    # Ollama common models
    "nomic-embed-text": 768,
    "mxbai-embed-large": 1024,
    "all-minilm": 384,
    "snowflake-arctic-embed": 1024,
    "bge-m3": 1024,
}


def get_embed_dimensions(embed_model: "BaseEmbedding") -> int | None:
    """Return the output dimension count for *embed_model*, or None if unknown.

    Checks an explicit ``dimensions`` field first (OpenAI v3 models support
    truncated output via this field), then falls back to ``_KNOWN_DIMENSIONS``.
    Returns ``None`` for unknown models — the caller should leave
    ``GraphRAGConfig.embed_dimensions`` at its default or ask the user to set
    ``EMBEDDINGS_DIMENSIONS``.
    """
    explicit = getattr(embed_model, "dimensions", None)
    if explicit is not None:
        return int(explicit)
    model_name = (
        getattr(embed_model, "model_name", None)
        or getattr(embed_model, "model", None)
        or ""
    )
    return _KNOWN_DIMENSIONS.get(str(model_name).lower())


def build_llm(cfg: LLMConfig) -> tuple["LLM | None", "BaseEmbedding | None"]:
    """Build a (llm, embed_model) pair from config.

    Returns (None, None) for bedrock — the graphrag-toolkit creates Bedrock
    clients itself using ambient AWS credentials.
    """
    provider = cfg.provider or "bedrock"

    if provider == "bedrock":
        return None, None

    if provider == "openai":
        try:
            from llama_index.llms.openai import OpenAI
            from llama_index.embeddings.openai import OpenAIEmbedding
        except ImportError as exc:
            raise ImportError(
                "OpenAI provider requires: pip install llama-index-llms-openai llama-index-embeddings-openai"
            ) from exc
        llm_kwargs = {"model": cfg.model} if cfg.model else {}
        emb_kwargs = {"model": cfg.embed_model} if cfg.embed_model else {}
        return OpenAI(**llm_kwargs), OpenAIEmbedding(**emb_kwargs)

    if provider == "ollama":
        try:
            from llama_index.llms.ollama import Ollama
            from llama_index.embeddings.ollama import OllamaEmbedding
        except ImportError as exc:
            raise ImportError(
                "Ollama provider requires: pip install llama-index-llms-ollama llama-index-embeddings-ollama"
            ) from exc
        base = {"base_url": cfg.base_url} if cfg.base_url else {}
        llm_kwargs = {"model": cfg.model, **base} if cfg.model else base
        emb_kwargs = {"model_name": cfg.embed_model, **base} if cfg.embed_model else base
        return Ollama(**llm_kwargs), OllamaEmbedding(**emb_kwargs)

    raise ValueError(f"Unknown provider {provider!r}")
