from __future__ import annotations

try:
    import tomllib
except ImportError:  # Python < 3.11
    import tomli as tomllib  # type: ignore[no-redef]

from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_CONFIG_FILE = "openwiki-graph.toml"


SUPPORTED_PROVIDERS = {"bedrock", "openai", "ollama"}


@dataclass
class WikiConfig:
    root: str = ""
    repo_root: str = ""  # root of the repository being documented
    id: str = ""         # namespace prefix for multi-repo graphs (e.g. "producer-api")


@dataclass
class PipelineConfig:
    full_rebuild: bool = False              # use full drop+rebuild instead of incremental update
    skip_reconcile_deletions: bool = False  # skip the default deletion reconciliation step


@dataclass
class StoresConfig:
    graph: str = ""
    vector: str = ""


@dataclass
class LLMConfig:
    provider: str = "bedrock"   # bedrock | openai | ollama
    model: str = ""             # provider-specific default used when empty
    embed_model: str = ""       # embedding model; provider default used when empty
    base_url: str = ""          # ollama only


@dataclass
class IndexingConfig:
    extraction_dir: str | None = None
    chunk_size: int | None = None
    chunk_overlap: int | None = None


@dataclass
class AppConfig:
    wiki: WikiConfig = field(default_factory=WikiConfig)
    stores: StoresConfig = field(default_factory=StoresConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    indexing: IndexingConfig = field(default_factory=IndexingConfig)
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)


def load_config(path: str | Path | None = None) -> AppConfig:
    """Load AppConfig from a TOML file.

    Returns an empty AppConfig (all defaults) when the file does not exist,
    so the caller never has to check for the file's presence itself.

    Args:
        path: Path to the TOML config file. Defaults to ``openwiki-graph.toml``
              in the current working directory.

    Raises:
        ValueError: If the file exists but contains invalid TOML or an
                    unrecognised top-level section.
    """
    resolved = Path(path or DEFAULT_CONFIG_FILE)
    if not resolved.exists():
        return AppConfig()

    with resolved.open("rb") as fh:
        try:
            data = tomllib.load(fh)
        except Exception as exc:
            raise ValueError(f"Could not parse {resolved}: {exc}") from exc

    return _parse(data, resolved)


def _parse(data: dict, source: Path) -> AppConfig:
    known = {"wiki", "stores", "llm", "indexing", "pipeline"}
    unknown = set(data) - known
    if unknown:
        raise ValueError(
            f"{source}: unknown section(s) {sorted(unknown)}. "
            f"Valid sections: {sorted(known)}"
        )

    wiki_data = data.get("wiki", {})
    stores_data = data.get("stores", {})
    llm_data = data.get("llm", {})
    indexing_data = data.get("indexing", {})
    pipeline_data = data.get("pipeline", {})

    chunk_size = indexing_data.get("chunk_size")
    chunk_overlap = indexing_data.get("chunk_overlap")

    if chunk_size is not None and not isinstance(chunk_size, int):
        raise ValueError(f"{source}: [indexing] chunk_size must be an integer")
    if chunk_overlap is not None and not isinstance(chunk_overlap, int):
        raise ValueError(f"{source}: [indexing] chunk_overlap must be an integer")

    provider = llm_data.get("provider", "bedrock")
    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError(
            f"{source}: [llm] provider {provider!r} is not supported. "
            f"Choose one of: {sorted(SUPPORTED_PROVIDERS)}"
        )

    return AppConfig(
        wiki=WikiConfig(
            root=wiki_data.get("root", ""),
            repo_root=wiki_data.get("repo_root", ""),
            id=wiki_data.get("id", ""),
        ),
        stores=StoresConfig(
            graph=stores_data.get("graph", ""),
            vector=stores_data.get("vector", ""),
        ),
        llm=LLMConfig(
            provider=provider,
            model=llm_data.get("model", ""),
            embed_model=llm_data.get("embed_model", ""),
            base_url=llm_data.get("base_url", ""),
        ),
        indexing=IndexingConfig(
            extraction_dir=indexing_data.get("extraction_dir"),
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        ),
        pipeline=PipelineConfig(
            full_rebuild=bool(pipeline_data.get("full_rebuild", False)),
            skip_reconcile_deletions=bool(pipeline_data.get("skip_reconcile_deletions", False)),
        ),
    )
