from __future__ import annotations

import logging
from typing import Sequence

from graphrag_toolkit.lexical_graph.storage import GraphStoreFactory

from ..models import OpenWikiPage

logger = logging.getLogger(__name__)

# Delete all outgoing RELATED_TO edges from a source node before re-writing them.
# This implements a replace strategy so removed relatedPages links don't linger.
_DELETE_RELATED_TO_QUERY = """\
MATCH (from:`__Source__` {doc_id: $from_id})-[r:RELATED_TO]->()
DELETE r
"""

# Both MATCH clauses must succeed; MERGE is idempotent within a single write pass.
_RELATED_TO_QUERY = """\
MATCH (from:`__Source__` {doc_id: $from_id})
MATCH (to:`__Source__` {doc_id: $to_id})
MERGE (from)-[:RELATED_TO]->(to)
"""


class RelatedPagesEdgeWriter:
    """Post-index step: writes RELATED_TO edges from relatedPages frontmatter.

    For each wiki page that lists related pages, this writer adds a
    ``(from:__Source__)-[:RELATED_TO]->(to:__Source__)`` edge in the graph.
    The `:Source` nodes are matched by their ``doc_id`` property, which the
    enricher stores in document metadata (scalar metadata survives the toolkit's
    metadata pipeline and lands as node properties).

    Run this **after** ``OpenWikiGraphIndexer.index()`` so the `:Source` nodes
    already exist.
    """

    def __init__(self, graph_store: str, pages: Sequence[OpenWikiPage]) -> None:
        """
        Args:
            graph_store: Connection string for the graph backend
                (e.g. ``bolt://localhost:7687`` for Neo4j).
            pages: Pages to write edges for, typically from
                ``OpenWikiLoader.load_pages()``.
        """
        self._graph_conn = graph_store
        self._pages = list(pages)

    def write(self) -> int:
        """Write RELATED_TO edges for all pages that have relatedPages.

        Returns:
            The number of edge-write operations attempted.
        """
        graph_store = GraphStoreFactory.for_graph_store(self._graph_conn)
        count = 0
        for page in self._pages:
            # Always clear stale outgoing edges first so removed relatedPages
            # links don't survive an update run.
            graph_store.execute_query(
                _DELETE_RELATED_TO_QUERY,
                parameters={"from_id": page.doc_id},
            )
            for related_id in page.related_pages:
                logger.debug(
                    "Writing RELATED_TO: %r → %r", page.doc_id, related_id
                )
                graph_store.execute_query(
                    _RELATED_TO_QUERY,
                    parameters={"from_id": page.doc_id, "to_id": related_id},
                )
                count += 1
        logger.info("Wrote %d RELATED_TO edge(s)", count)
        return count
