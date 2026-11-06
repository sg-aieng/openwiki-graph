from __future__ import annotations

import json
import logging

# Matches graphrag_toolkit.lexical_graph.indexing.constants.PROPOSITIONS_KEY
PROPOSITIONS_KEY: str = "aws::graph::propositions"
# JSON-serialised claim evidence.  Stored as a string because the toolkit
# drops list-valued metadata before graph construction; a string property
# survives to the __Source__ node.  Schema: list of
# {"id": str, "statement": str, "evidence": [{"resource": str, "version": str}]}
EVIDENCE_KEY: str = "openwiki::claims::evidence"

from llama_index.core import Document

from ...models import OpenWikiPage

logger = logging.getLogger(__name__)


def _build_document(page: OpenWikiPage) -> Document:
    """Build one Document per wiki page.

    Claim-bearing pages have ``PROPOSITIONS_KEY`` pre-seeded with verified
    statement strings so ``SkippingLLMPropositionExtractor`` bypasses LLM
    extraction for every chunk of that page.  ``PROPOSITIONS_KEY`` is consumed
    at extraction time (before graph construction), so inheriting the same list
    across chunks is correct: each chunk surfaces the page's curated claims,
    and the toolkit deduplicates statements via MERGE.

    Evidence is JSON-serialised under ``EVIDENCE_KEY`` to survive the toolkit's
    metadata pipeline (list-valued keys are dropped; string-valued keys reach
    the ``__Source__`` node as properties).
    """
    text = page.text or ""
    # MarkdownNodeParser produces zero nodes for an empty body, so a claim-bearing
    # page with no text would lose all its pre-seeded propositions.  A minimal
    # placeholder ensures at least one chunk reaches the pipeline.
    if page.claims and not text.strip():
        text = "(This page has no body content.)"

    metadata: dict = {
        "doc_id": page.doc_id,
        "source": page.doc_id,  # stable wiki-relative ID, not a filesystem path
        "title": page.title,
        "description": page.description,
        "wiki_type": page.wiki_type,
        # Scalar string so the toolkit persists it on the __Source__ node;
        # list-valued metadata is dropped during graph construction.
        "tags": ", ".join(page.tags),
        "related_pages": page.related_pages,
        # Mirror the loader path so callers see consistent metadata regardless
        # of which path produced the Document.
        "raw_claims": ", ".join(c.statement for c in page.claims),
    }
    excluded = ["doc_id", "source", "raw_claims"]

    if page.claims:
        metadata[PROPOSITIONS_KEY] = [c.statement for c in page.claims]
        metadata[EVIDENCE_KEY] = json.dumps([
            {
                "id": c.id,
                "statement": c.statement,
                "evidence": [
                    {"resource": e.resource, "version": e.version}
                    for e in c.evidence
                ],
            }
            for c in page.claims
        ])
        excluded.append(EVIDENCE_KEY)

    return Document(
        text=text,
        doc_id=page.doc_id,
        metadata=metadata,
        excluded_embed_metadata_keys=excluded,
        excluded_llm_metadata_keys=excluded,
    )


class ClaimsEnricher:
    """Stage 2: converts OpenWikiPages → Documents with pre-seeded propositions.

    Emits exactly one Document per page.

    Pages WITH Claims have ``PROPOSITIONS_KEY`` set on the Document.  All
    chunks inherit it, causing ``SkippingLLMPropositionExtractor`` to bypass
    LLM extraction for the entire page and use the verified claims instead.
    Claim evidence is stored as a JSON string under ``EVIDENCE_KEY`` so it
    reaches the ``__Source__`` node as a string property.

    Pages WITHOUT Claims produce plain Documents; the LLM extracts propositions
    from their chunks as normal.
    """

    def enrich(self, pages: list[OpenWikiPage]) -> list[Document]:
        documents = []
        for page in pages:
            documents.append(_build_document(page))
            if page.claims:
                logger.debug(
                    "Pre-seeded %d claim(s) for page %r",
                    len(page.claims),
                    page.doc_id,
                )
        return documents
