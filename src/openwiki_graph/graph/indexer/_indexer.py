from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from graphrag_toolkit.lexical_graph.lexical_graph_index import (
    BuildConfig,
    ExtractionConfig,
    IndexingConfig,
    LexicalGraphIndex,
)
from graphrag_toolkit.lexical_graph.storage import (
    GraphStoreFactory,
    VectorStoreFactory,
)
from llama_index.core.node_parser import MarkdownNodeParser, NodeParser, SentenceSplitter

from ...models import OpenWikiPage
from ...wiki.loader import OpenWikiLoader
from ._extractor import SkippingLLMPropositionExtractor
from ..enricher import ClaimsEnricher

logger = logging.getLogger(__name__)


class OpenWikiGraphIndexer:
    """Orchestrates OpenWiki → LexicalGraph pipeline.

    Stage flow: OpenWikiLoader → ClaimsEnricher → LexicalGraphIndex.
    Claims-bearing pages bypass LLM proposition extraction via
    SkippingLLMPropositionExtractor; all other pages use the LLM.
    """

    # SentenceSplitter fallback defaults — override via constructor args or
    # OPENWIKI_CHUNK_SIZE / OPENWIKI_CHUNK_OVERLAP environment variables.
    DEFAULT_CHUNK_SIZE = 512
    DEFAULT_CHUNK_OVERLAP = 50

    def __init__(
        self,
        wiki_root: str | Path,
        graph_store: str,
        vector_store: str,
        extraction_llm: Any = None,
        tenant_id: Any = None,
        extraction_dir: str | Path | None = None,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
        chunking: list[NodeParser] | None = None,
        wiki_id: str = "",
    ) -> None:
        """
        Args:
            wiki_root: Directory containing OpenWiki Markdown pages.
            graph_store: Connection string for the graph backend
                (e.g. ``bolt://localhost:7687`` for Neo4j).
            vector_store: Connection string for the vector backend
                (e.g. ``pgvector://...``).
            extraction_llm: LLM override for proposition/topic extraction.
                Defaults to ``GraphRAGConfig.extract_llm``.
            tenant_id: Optional tenant isolator for multi-tenant graphs.
            extraction_dir: Directory for extraction checkpoint files.
            chunk_size: Token limit for the ``SentenceSplitter`` fallback stage.
                Resolved in order: argument → ``OPENWIKI_CHUNK_SIZE`` env var →
                ``DEFAULT_CHUNK_SIZE`` (512).  Ignored when ``chunking`` is provided.
            chunk_overlap: Token overlap for the ``SentenceSplitter`` fallback stage.
                Resolved in order: argument → ``OPENWIKI_CHUNK_OVERLAP`` env var →
                ``DEFAULT_CHUNK_OVERLAP`` (50).  Ignored when ``chunking`` is provided.
            chunking: Explicit list of LlamaIndex ``NodeParser`` instances that
                replaces the default two-stage pipeline entirely.  Pass ``[]`` to
                disable chunking.
        """
        self.wiki_root = Path(wiki_root)
        self._graph_conn = graph_store
        self._vector_conn = vector_store
        self._extraction_llm = extraction_llm
        self._tenant_id = tenant_id
        self._wiki_id = wiki_id
        self._extraction_dir = str(extraction_dir) if extraction_dir else None
        self._chunk_size = (
            chunk_size
            if chunk_size is not None
            else int(os.environ.get("OPENWIKI_CHUNK_SIZE", self.DEFAULT_CHUNK_SIZE))
        )
        self._chunk_overlap = (
            chunk_overlap
            if chunk_overlap is not None
            else int(os.environ.get("OPENWIKI_CHUNK_OVERLAP", self.DEFAULT_CHUNK_OVERLAP))
        )
        self._chunking = chunking

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_chunking(self) -> list[NodeParser]:
        if self._chunking is not None:
            return list(self._chunking)
        # Two-stage default: split at Markdown headers first (structure-aware),
        # then apply SentenceSplitter as a token-limit safety net for any section
        # that exceeds chunk_size.
        return [
            MarkdownNodeParser(),
            SentenceSplitter(chunk_size=self._chunk_size, chunk_overlap=self._chunk_overlap),
        ]

    def _make_index(self, enable_versioning: bool = False) -> LexicalGraphIndex:
        chunking = self._build_chunking()
        extraction_config = ExtractionConfig(
            # Disabled here so we can inject SkippingLLMPropositionExtractor
            # ourselves at the correct pipeline position.
            enable_proposition_extraction=False,
            extraction_llm=self._extraction_llm,
        )
        indexing_config = IndexingConfig(
            chunking=chunking,
            extraction=extraction_config,
            build=BuildConfig(enable_versioning=enable_versioning),
        )

        graph_store = GraphStoreFactory.for_graph_store(self._graph_conn)
        vector_store = VectorStoreFactory.for_vector_store(self._vector_conn)

        index = LexicalGraphIndex(
            graph_store=graph_store,
            vector_store=vector_store,
            tenant_id=self._tenant_id,
            extraction_dir=self._extraction_dir,
            indexing_config=indexing_config,
        )

        # Splice SkippingLLMPropositionExtractor after chunking components.
        # The toolkit adds NodeParser(s) first; our extractor must follow them
        # so it sees the chunked nodes rather than full documents.
        chunking_count = sum(
            1 for c in index.extraction_components if isinstance(c, NodeParser)
        )
        index.extraction_components.insert(
            chunking_count,
            SkippingLLMPropositionExtractor(llm=extraction_config.extraction_llm),
        )
        logger.debug(
            "Extraction pipeline: %s",
            [type(c).__name__ for c in index.extraction_components],
        )
        return index

    def _load_documents(self) -> list:
        loader = OpenWikiLoader(self.wiki_root, wiki_id=self._wiki_id)
        pages: list[OpenWikiPage] = loader.load_pages()
        logger.info("Loaded %d pages from %s", len(pages), self.wiki_root)
        documents = ClaimsEnricher().enrich(pages)
        return documents

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def index(self, show_progress: bool = True) -> None:
        """Full index: load all wiki pages and build the lexical graph."""
        index = self._make_index(enable_versioning=False)
        documents = self._load_documents()
        index.extract_and_build(nodes=documents, show_progress=show_progress)

    def update(self, show_progress: bool = True) -> None:
        """Incremental update: re-index with versioning so stale nodes are retired.

        Changed pages are re-extracted; unchanged pages are skipped via the
        toolkit's built-in source-ID deduplication.
        """
        index = self._make_index(enable_versioning=True)
        documents = self._load_documents()
        index.extract_and_build(nodes=documents, show_progress=show_progress)

