from __future__ import annotations

import logging
from pathlib import Path
from typing import Sequence

from graphrag_toolkit.lexical_graph.indexing.build.delete_sources import DeleteSources
from graphrag_toolkit.lexical_graph.storage import GraphStoreFactory, VectorStoreFactory

from ..wiki.loader import OpenWikiLoader

logger = logging.getLogger(__name__)

# Returns every __Source__ node that has a doc_id, along with its internal
# sourceId (the toolkit's UUID, used for deletion).
_LIST_SOURCES_QUERY = """\
MATCH (s:`__Source__`)
WHERE s.doc_id IS NOT NULL
RETURN s.doc_id AS doc_id, s.sourceId AS source_id
"""

# Same query scoped to a wiki_id prefix — used for multi-repo graphs so that
# only the nodes belonging to the current wiki are considered for reconciliation.
_LIST_SOURCES_SCOPED_QUERY = """\
MATCH (s:`__Source__`)
WHERE s.doc_id IS NOT NULL AND s.doc_id STARTS WITH $prefix
RETURN s.doc_id AS doc_id, s.sourceId AS source_id
"""


class DeleteReconciler:
    """Detects and removes wiki pages that have been deleted from disk.

    After an incremental update, source nodes for deleted pages remain in the
    graph because the toolkit only processes pages it is given — it has no
    awareness of pages that existed in a prior run.

    This reconciler queries the graph for all indexed ``doc_id`` values, diffs
    them against the current wiki on disk, and deletes orphaned source subgraphs
    via the toolkit's own ``DeleteSources`` pipeline (chunks, topics, statements,
    facts, entities, and all matching vector embeddings).

    When ``wiki_id`` is set the query is scoped to nodes whose ``doc_id`` starts
    with ``{wiki_id}::`` so that multi-repo graphs are not cross-contaminated.

    Run this **after** ``OpenWikiGraphIndexer.update()``; it is a no-op when no
    pages have been deleted.
    """

    def __init__(
        self,
        graph_store: str,
        vector_store: str,
        wiki_root: str | Path,
        wiki_id: str = "",
    ) -> None:
        """
        Args:
            graph_store: Connection string for the graph backend.
            vector_store: Connection string for the vector backend.
            wiki_root: Directory containing the current OpenWiki pages.
            wiki_id: Namespace prefix used when multiple repos share one graph.
                     Must match the value used when indexing.
        """
        self._graph_conn = graph_store
        self._vector_conn = vector_store
        self._wiki_root = Path(wiki_root)
        self._wiki_id = wiki_id

    def reconcile(self) -> int:
        """Delete orphaned source nodes for pages no longer on disk.

        Returns:
            Number of source documents deleted.
        """
        graph_store = GraphStoreFactory.for_graph_store(self._graph_conn)

        if self._wiki_id:
            rows = graph_store.execute_query(
                _LIST_SOURCES_SCOPED_QUERY,
                parameters={"prefix": f"{self._wiki_id}::"},
            )
        else:
            rows = graph_store.execute_query(_LIST_SOURCES_QUERY)

        indexed: dict[str, str] = {
            r["doc_id"]: r["source_id"]
            for r in rows
            if r.get("doc_id") and r.get("source_id")
        }

        if not indexed:
            logger.info("No indexed sources found; nothing to reconcile.")
            return 0

        current_doc_ids = {
            p.doc_id
            for p in OpenWikiLoader(self._wiki_root, wiki_id=self._wiki_id).load_pages()
        }
        orphaned_doc_ids = set(indexed) - current_doc_ids

        if not orphaned_doc_ids:
            logger.info("All %d indexed source(s) still present on disk.", len(indexed))
            return 0

        orphaned_source_ids = [indexed[d] for d in sorted(orphaned_doc_ids)]
        logger.info(
            "Deleting %d orphaned source(s): %s",
            len(orphaned_source_ids),
            sorted(orphaned_doc_ids),
        )

        vector_store = VectorStoreFactory.for_vector_store(self._vector_conn)
        deleter = DeleteSources(graph_store=graph_store, vector_store=vector_store)
        deleter.delete_source_documents(source_ids=orphaned_source_ids)

        logger.info("Deleted %d orphaned source(s).", len(orphaned_source_ids))
        return len(orphaned_source_ids)
