from pathlib import Path

import pytest

from openwiki_graph.models import Claim, Evidence, OpenWikiPage
from openwiki_graph.graph.enricher import ClaimsEnricher, EVIDENCE_KEY, PROPOSITIONS_KEY


def _make_page(claims: list[Claim] | None = None, doc_id: str = "api/endpoints") -> OpenWikiPage:
    return OpenWikiPage(
        path=Path(f"/wiki/{doc_id}.md"),
        doc_id=doc_id,
        title="Test Page",
        description="A test page.",
        text="Some content.",
        tags=["test"],
        related_pages=[],
        wiki_type="api-reference",
        claims=claims or [],
    )


def test_enrich_page_without_claims_produces_one_document():
    from llama_index.core import Document

    page = _make_page()
    docs = ClaimsEnricher().enrich([page])

    assert len(docs) == 1
    doc = docs[0]
    assert isinstance(doc, Document)
    assert doc.doc_id == "api/endpoints"


def test_enrich_page_without_claims_has_no_propositions_key():
    page = _make_page()
    docs = ClaimsEnricher().enrich([page])
    assert PROPOSITIONS_KEY not in docs[0].metadata


def test_enrich_page_with_claims_produces_one_document():
    """Claim-bearing pages produce exactly one document (no ::claims duplicate)."""
    from llama_index.core import Document

    claims = [Claim(id="c1", statement="Endpoint A returns 200.",
                    evidence=[Evidence(resource="repo://a.java#L1")])]
    page = _make_page(claims=claims)
    docs = ClaimsEnricher().enrich([page])

    assert len(docs) == 1
    assert docs[0].doc_id == "api/endpoints"
    assert isinstance(docs[0], Document)


def test_enrich_page_with_claims_retains_full_text():
    """The page document keeps its original markdown text."""
    claims = [Claim(id="c1", statement="A fact.", evidence=[])]
    page = _make_page(claims=claims)
    docs = ClaimsEnricher().enrich([page])

    assert docs[0].text == "Some content."


def test_enrich_page_with_claims_seeds_propositions_key():
    claims = [
        Claim(id="c1", statement="Endpoint A returns 200.",
              evidence=[Evidence(resource="repo://a.java#L1")]),
        Claim(id="c2", statement="Endpoint B requires auth.",
              evidence=[Evidence(resource="repo://b.java#L5")]),
    ]
    page = _make_page(claims=claims)
    docs = ClaimsEnricher().enrich([page])

    assert PROPOSITIONS_KEY in docs[0].metadata
    assert docs[0].metadata[PROPOSITIONS_KEY] == [
        "Endpoint A returns 200.",
        "Endpoint B requires auth.",
    ]


def test_enrich_page_with_claims_evidence_is_json_string():
    """EVIDENCE_KEY is a JSON string (not a list) so the toolkit passes it through."""
    import json

    claims = [
        Claim(id="c1", statement="Fact one.",
              evidence=[Evidence(resource="repo://Foo.java#L1-L5",
                                 version="repo-lines-v1:sha256:aaa")]),
        Claim(id="c2", statement="Fact two.",
              evidence=[Evidence(resource="repo://Bar.java#L10", version="")]),
    ]
    page = _make_page(claims=claims)
    docs = ClaimsEnricher().enrich([page])

    raw = docs[0].metadata[EVIDENCE_KEY]
    assert isinstance(raw, str), "EVIDENCE_KEY must be a string, not a list"

    parsed = json.loads(raw)
    assert len(parsed) == 2
    assert parsed[0]["id"] == "c1"
    assert parsed[0]["statement"] == "Fact one."
    assert parsed[0]["evidence"][0]["resource"] == "repo://Foo.java#L1-L5"
    assert parsed[0]["evidence"][0]["version"] == "repo-lines-v1:sha256:aaa"
    assert parsed[1]["id"] == "c2"
    assert parsed[1]["evidence"][0]["resource"] == "repo://Bar.java#L10"


def test_enrich_preserves_standard_metadata():
    page = _make_page()
    doc = ClaimsEnricher().enrich([page])[0]

    assert doc.metadata["wiki_type"] == "api-reference"
    assert doc.metadata["title"] == "Test Page"
    assert doc.metadata["tags"] == "test"
    assert doc.metadata["description"] == "A test page."
    assert doc.metadata["related_pages"] == []


def test_enrich_tags_are_comma_string():
    """Tags must be a scalar string so the toolkit persists them on __Source__."""
    from openwiki_graph.models import OpenWikiPage
    page = OpenWikiPage(
        path=__import__("pathlib").Path("/wiki/p.md"),
        doc_id="p",
        title="P",
        description="",
        text="Content.",
        tags=["alpha", "beta", "gamma"],
        related_pages=[],
        wiki_type="api-reference",
        claims=[],
    )
    doc = ClaimsEnricher().enrich([page])[0]
    assert doc.metadata["tags"] == "alpha, beta, gamma"
    assert isinstance(doc.metadata["tags"], str)


def test_enrich_raw_claims_present_on_claim_page():
    """raw_claims mirrors the loader path so both paths expose a consistent key."""
    claims = [
        Claim(id="c1", statement="Statement A.", evidence=[]),
        Claim(id="c2", statement="Statement B.", evidence=[]),
    ]
    page = _make_page(claims=claims)
    doc = ClaimsEnricher().enrich([page])[0]
    assert isinstance(doc.metadata["raw_claims"], str)
    assert "Statement A." in doc.metadata["raw_claims"]
    assert "Statement B." in doc.metadata["raw_claims"]


def test_enrich_raw_claims_empty_on_non_claim_page():
    page = _make_page()
    doc = ClaimsEnricher().enrich([page])[0]
    assert doc.metadata["raw_claims"] == ""


def test_enrich_claim_page_with_empty_text_gets_placeholder():
    """Empty-body claim pages must produce a non-empty document so the pipeline
    emits at least one chunk and the pre-seeded propositions are not lost."""
    from openwiki_graph.models import OpenWikiPage
    page = OpenWikiPage(
        path=__import__("pathlib").Path("/wiki/empty.md"),
        doc_id="empty",
        title="Empty",
        description="",
        text="",
        tags=[],
        related_pages=[],
        wiki_type="api-reference",
        claims=[Claim(id="c1", statement="A claim.", evidence=[])],
    )
    doc = ClaimsEnricher().enrich([page])[0]
    assert doc.text.strip(), "placeholder text must be non-empty"


def test_enrich_non_claim_page_with_empty_text_keeps_empty():
    """Non-claim pages with empty text are left as-is; the guard is claims-only."""
    from openwiki_graph.models import OpenWikiPage
    page = OpenWikiPage(
        path=__import__("pathlib").Path("/wiki/blank.md"),
        doc_id="blank",
        title="Blank",
        description="",
        text="",
        tags=[],
        related_pages=[],
        wiki_type="api-reference",
        claims=[],
    )
    doc = ClaimsEnricher().enrich([page])[0]
    assert doc.text == ""


def test_enrich_multiple_pages_mixed():
    page_with = _make_page(
        doc_id="api/endpoints",
        claims=[Claim(id="c1", statement="Claim.", evidence=[])],
    )
    page_without = _make_page(doc_id="quickstart")

    docs = ClaimsEnricher().enrich([page_with, page_without])

    assert len(docs) == 2
    ids = {d.doc_id for d in docs}
    assert ids == {"api/endpoints", "quickstart"}

    claim_doc = next(d for d in docs if d.doc_id == "api/endpoints")
    plain_doc = next(d for d in docs if d.doc_id == "quickstart")
    assert PROPOSITIONS_KEY in claim_doc.metadata
    assert PROPOSITIONS_KEY not in plain_doc.metadata


def test_enrich_empty_list_returns_empty():
    assert ClaimsEnricher().enrich([]) == []


def test_propositions_key_is_list_of_strings():
    claims = [Claim(id="c1", statement="A fact.", evidence=[])]
    docs = ClaimsEnricher().enrich([_make_page(claims=claims)])
    seeded = docs[0].metadata[PROPOSITIONS_KEY]
    assert isinstance(seeded, list)
    assert all(isinstance(s, str) for s in seeded)
