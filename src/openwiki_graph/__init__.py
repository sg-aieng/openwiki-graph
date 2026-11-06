from __future__ import annotations


def __getattr__(name: str):
    if name == "OpenWikiGraphIndexer":
        from .graph.indexer import OpenWikiGraphIndexer
        return OpenWikiGraphIndexer
    if name == "RelatedPagesEdgeWriter":
        from .graph.edge_writer import RelatedPagesEdgeWriter
        return RelatedPagesEdgeWriter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["OpenWikiGraphIndexer", "RelatedPagesEdgeWriter"]
