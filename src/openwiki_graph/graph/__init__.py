from __future__ import annotations


def __getattr__(name: str):
    if name == "OpenWikiGraphIndexer":
        from .indexer import OpenWikiGraphIndexer
        return OpenWikiGraphIndexer
    if name == "RelatedPagesEdgeWriter":
        from .edge_writer import RelatedPagesEdgeWriter
        return RelatedPagesEdgeWriter
    if name == "ClaimsEvidenceWriter":
        from .evidence_writer import ClaimsEvidenceWriter
        return ClaimsEvidenceWriter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["ClaimsEvidenceWriter", "OpenWikiGraphIndexer", "RelatedPagesEdgeWriter"]
