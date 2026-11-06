from __future__ import annotations

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterator

import yaml
from llama_index.core import Document

from ...models import Page

_DEFAULT_SKIP_NAMES = frozenset({"index.md"})


def _resolve_skip_names(override: set[str] | None) -> frozenset[str]:
    if override is not None:
        return frozenset(override)
    env = os.environ.get("OPENWIKI_SKIP_NAMES")
    if env:
        return frozenset(name.strip() for name in env.split(",") if name.strip())
    return _DEFAULT_SKIP_NAMES


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Split YAML frontmatter from body. Returns (meta, body)."""
    if not text.startswith("---\n"):
        return {}, text
    try:
        end = text.index("\n---", 4)
    except ValueError:
        return {}, text
    meta = yaml.safe_load(text[4:end])
    body = text[end + 4:].lstrip("\n")
    return meta or {}, body


class MarkdownDirectoryLoader(ABC):
    """Walks a Markdown directory tree and produces LlamaIndex Documents.

    Subclasses implement _try_parse to handle a specific documentation format.
    File discovery, hidden-directory skipping, and Document construction are
    handled here so subclasses never need to repeat them.
    """

    def __init__(
        self,
        root: str | Path,
        skip_names: set[str] | None = None,
        wiki_id: str = "",
    ) -> None:
        self.root = Path(root).resolve()
        if not self.root.is_dir():
            raise ValueError(f"root not found: {self.root}")
        self._skip_names = _resolve_skip_names(skip_names)
        self._wiki_id = wiki_id

    # ── Public API ───────────────────────────────────────────────────────────

    def load_pages(self) -> list[Page]:
        pages = []
        for path in self._iter_files():
            page = self._parse(path)
            if page is not None:
                pages.append(page)
        return pages

    def load(self) -> list[Document]:
        return [self._to_document(p) for p in self.load_pages()]

    # ── Extension points ─────────────────────────────────────────────────────

    @abstractmethod
    def _parse(self, path: Path) -> Page | None:
        """Parse one file into a Page. Return None to skip it."""
        ...

    def _extra_metadata(self, page: Page) -> dict:
        """Format-specific metadata merged into the Document. Override as needed."""
        return {}

    # ── Shared internals ─────────────────────────────────────────────────────

    def _iter_files(self) -> Iterator[Path]:
        for path in sorted(self.root.rglob("*.md")):
            if path.name in self._skip_names:
                continue
            relative_parts = path.relative_to(self.root).parts
            if any(part.startswith(".") for part in relative_parts):
                continue
            yield path

    def _to_document(self, page: Page) -> Document:
        return Document(
            text=page.text,
            doc_id=page.doc_id,
            metadata={
                "doc_id": page.doc_id,
                "source": page.doc_id,  # stable wiki-relative ID, not a filesystem path
                "title": page.title,
                "description": page.description,
                "tags": ", ".join(page.tags),
                "related_pages": page.related_pages,
                **self._extra_metadata(page),
            },
            excluded_embed_metadata_keys=["doc_id", "source"],
            excluded_llm_metadata_keys=["doc_id", "source"],
        )
