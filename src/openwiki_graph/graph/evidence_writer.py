from __future__ import annotations

import logging
from typing import Sequence

from graphrag_toolkit.lexical_graph.storage import GraphStoreFactory

from ..models import OpenWikiPage

logger = logging.getLogger(__name__)

# Write a flat evidence_uris list onto the __Source__ node identified by doc_id.
# Rationale: __Statement__ nodes are created by TopicExtractor via LLM re-extraction
# from raw text, so their .value property never matches the verbatim claim statement
# text.  The __Source__ node is the stable anchor for claim evidence — it already
# carries the full EVIDENCE_KEY JSON from the enricher, and this query adds a
# convenient flat list of all evidence URIs across all claims for that page.
_SET_SOURCE_EVIDENCE_QUERY = """\
MATCH (src:`__Source__`)
WHERE src.doc_id = $page_doc_id
SET src.evidence_uris = $evidence_uris
RETURN count(src) AS updated
"""


class ClaimsEvidenceWriter:
    """Post-index step: writes evidence_uris onto __Source__ nodes.

    After ``extract_and_build`` the toolkit has created ``__Source__`` nodes
    that already carry full claim evidence under the ``openwiki::claims::evidence``
    property (set by the enricher).  This writer adds a flat ``evidence_uris``
    list — all resource URI strings across every claim on a page — for queries
    that only need the URI list without parsing the full JSON payload.

    ``__Statement__`` node values are produced by LLM re-extraction inside
    ``TopicExtractor`` and do not match the verbatim claim statement text, so
    per-statement evidence cannot be reliably written via text matching.

    Run this **after** ``OpenWikiGraphIndexer.index()`` or ``update()``; it is
    a no-op for pages that have no claims.
    """

    def __init__(self, graph_store: str, pages: Sequence[OpenWikiPage]) -> None:
        """
        Args:
            graph_store: Connection string for the graph backend.
            pages: Pages to process; non-claim pages are skipped silently.
        """
        self._graph_conn = graph_store
        self._pages = list(pages)

    def write(self) -> int:
        """Write evidence_uris onto __Source__ nodes for claim-bearing pages.

        Returns:
            Number of source nodes updated.
        """
        claim_pages = [p for p in self._pages if p.claims]
        if not claim_pages:
            return 0

        graph_store = GraphStoreFactory.for_graph_store(self._graph_conn)
        count = 0
        for page in claim_pages:
            evidence_uris = [
                e.resource
                for claim in page.claims
                for e in claim.evidence
            ]
            logger.debug(
                "Writing %d evidence URI(s) for page %r",
                len(evidence_uris),
                page.doc_id,
            )
            graph_store.execute_query(
                _SET_SOURCE_EVIDENCE_QUERY,
                parameters={
                    "page_doc_id": page.doc_id,
                    "evidence_uris": evidence_uris,
                },
            )
            count += 1
        logger.info(
            "Wrote evidence_uris for %d page(s) (%d source node(s))",
            len(claim_pages),
            count,
        )
        return count
