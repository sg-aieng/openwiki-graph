from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .claim import Claim


@dataclass
class Page:
    """Generic parsed Markdown page — format-agnostic."""
    path: Path
    doc_id: str
    title: str
    description: str
    text: str
    tags: list[str] = field(default_factory=list)
    related_pages: list[str] = field(default_factory=list)


@dataclass
class OpenWikiPage(Page):
    """OpenWiki-specific page with a type label and pre-verified Claims."""
    wiki_type: str = ""
    claims: list[Claim] = field(default_factory=list)
