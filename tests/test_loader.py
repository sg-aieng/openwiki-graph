from pathlib import Path

import pytest

from openwiki_graph.wiki.loader import MarkdownDirectoryLoader, OpenWikiLoader
from openwiki_graph.models import Claim, OpenWikiPage, Page

FIXTURE = Path(__file__).parent / "fixtures" / "sample_wiki"


def test_load_pages_returns_openwiki_pages():
    loader = OpenWikiLoader(FIXTURE)
    pages = loader.load_pages()
    assert len(pages) == 1
    page = pages[0]
    assert isinstance(page, OpenWikiPage)
    assert isinstance(page, Page)  # OpenWikiPage is a Page
    assert page.doc_id == "quickstart"
    assert page.wiki_type == "quickstart"
    assert page.title == "Quickstart"


def test_load_pages_attaches_claims():
    loader = OpenWikiLoader(FIXTURE)
    pages = loader.load_pages()
    page = pages[0]
    assert len(page.claims) == 1
    claim = page.claims[0]
    assert isinstance(claim, Claim)
    assert "port 8080" in claim.statement
    assert len(claim.evidence) == 1
    assert claim.evidence[0].resource == "repo://src/main/resources/application.properties#L1-L1"
    assert claim.evidence[0].version == "repo-lines-v1:sha256:abc"


def test_load_returns_documents():
    from llama_index.core import Document

    loader = OpenWikiLoader(FIXTURE)
    docs = loader.load()
    assert len(docs) == 1
    doc = docs[0]
    assert isinstance(doc, Document)
    assert doc.doc_id == "quickstart"
    assert doc.metadata["wiki_type"] == "quickstart"
    assert doc.metadata["tags"] == "quickstart, navigation"
    assert "port 8080" in doc.metadata["raw_claims"]


def test_missing_root_raises():
    with pytest.raises(ValueError, match="root not found"):
        OpenWikiLoader("/nonexistent/path")


def test_skips_files_without_openwiki_frontmatter(tmp_path):
    (tmp_path / "plain.md").write_text("# No frontmatter here\n")
    loader = OpenWikiLoader(tmp_path)
    assert loader.load_pages() == []


def test_skips_files_in_hidden_dirs(tmp_path):
    hidden = tmp_path / ".claims"
    hidden.mkdir()
    (hidden / "page.md").write_text("---\ntype: x\ntitle: x\n---\nbody\n")
    loader = OpenWikiLoader(tmp_path)
    assert loader.load_pages() == []


def test_page_without_claims_sidecar(tmp_path):
    (tmp_path / "no-claims.md").write_text(
        "---\ntype: architecture\ntitle: Overview\n---\nContent.\n"
    )
    loader = OpenWikiLoader(tmp_path)
    pages = loader.load_pages()
    assert len(pages) == 1
    assert pages[0].claims == []


def test_openwiki_loader_is_a_markdown_directory_loader():
    loader = OpenWikiLoader(FIXTURE)
    assert isinstance(loader, MarkdownDirectoryLoader)


def test_extra_metadata_included_in_document(tmp_path):
    (tmp_path / "typed.md").write_text(
        "---\ntype: api-reference\ntitle: API\n---\nBody.\n"
    )
    loader = OpenWikiLoader(tmp_path)
    docs = loader.load()
    assert docs[0].metadata["wiki_type"] == "api-reference"
    assert docs[0].metadata["raw_claims"] == ""
