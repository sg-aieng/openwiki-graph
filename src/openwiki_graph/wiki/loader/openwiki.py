from __future__ import annotations

from pathlib import Path

from ...models import OpenWikiPage, Page
from ..claims import load_claims
from .base import MarkdownDirectoryLoader, parse_frontmatter


class OpenWikiLoader(MarkdownDirectoryLoader):
    """Loads OpenWiki-formatted Markdown pages with .claims/ sidecars."""

    def _parse(self, path: Path) -> OpenWikiPage | None:
        raw = path.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(raw)

        if not meta.get("type"):
            return None

        raw_doc_id = str(path.relative_to(self.root).with_suffix(""))
        doc_id = f"{self._wiki_id}::{raw_doc_id}" if self._wiki_id else raw_doc_id

        raw_related = meta.get("relatedPages") or []
        related_pages = (
            [f"{self._wiki_id}::{rp}" for rp in raw_related]
            if self._wiki_id
            else raw_related
        )

        claims_path = (
            self.root / ".claims" / path.relative_to(self.root).with_suffix(".json")
        )

        return OpenWikiPage(
            path=path,
            doc_id=doc_id,
            title=meta.get("title", path.stem),
            description=meta.get("description", ""),
            text=body,
            tags=meta.get("tags") or [],
            related_pages=related_pages,
            wiki_type=meta.get("type", ""),
            claims=load_claims(claims_path),
        )

    def _extra_metadata(self, page: Page) -> dict:
        if not isinstance(page, OpenWikiPage):
            return {}
        return {
            "wiki_type": page.wiki_type,
            "raw_claims": ", ".join(c.statement for c in page.claims),
        }
