from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from openwiki_graph.models import Claim, Evidence, OpenWikiPage
from openwiki_graph.graph.evidence_writer import ClaimsEvidenceWriter, _SET_SOURCE_EVIDENCE_QUERY


def _make_page(
    doc_id: str = "api/endpoints",
    claims: list[Claim] | None = None,
) -> OpenWikiPage:
    return OpenWikiPage(
        path=Path(f"/wiki/{doc_id}.md"),
        doc_id=doc_id,
        title="Test Page",
        description="A test page.",
        text="Some content.",
        tags=[],
        related_pages=[],
        wiki_type="api-reference",
        claims=claims or [],
    )


@pytest.fixture
def mock_graph_store():
    store = MagicMock()
    store.execute_query = MagicMock()
    return store


def _make_writer(pages, store):
    writer = ClaimsEvidenceWriter(graph_store="bolt://localhost:7687", pages=pages)
    with patch(
        "openwiki_graph.graph.evidence_writer.GraphStoreFactory.for_graph_store",
        return_value=store,
    ):
        count = writer.write()
    return count, store


def test_write_returns_zero_for_no_claim_pages(mock_graph_store):
    pages = [_make_page(doc_id="plain")]
    writer = ClaimsEvidenceWriter(graph_store="bolt://localhost:7687", pages=pages)
    with patch(
        "openwiki_graph.graph.evidence_writer.GraphStoreFactory.for_graph_store",
        return_value=mock_graph_store,
    ):
        count = writer.write()
    assert count == 0
    mock_graph_store.execute_query.assert_not_called()


def test_write_returns_zero_for_empty_pages(mock_graph_store):
    writer = ClaimsEvidenceWriter(graph_store="bolt://localhost:7687", pages=[])
    with patch(
        "openwiki_graph.graph.evidence_writer.GraphStoreFactory.for_graph_store",
        return_value=mock_graph_store,
    ):
        count = writer.write()
    assert count == 0
    mock_graph_store.execute_query.assert_not_called()


def test_write_single_claim_with_evidence():
    store = MagicMock()
    claim = Claim(
        id="c1",
        statement="Service listens on port 8080.",
        evidence=[
            Evidence(resource="repo://src/main/Config.java#L10-L12", version="v1"),
            Evidence(resource="repo://src/main/Config.java#L20", version=""),
        ],
    )
    page = _make_page(doc_id="services/config", claims=[claim])

    count, store = _make_writer([page], store)

    # One call per page (not per claim)
    assert count == 1
    store.execute_query.assert_called_once_with(
        _SET_SOURCE_EVIDENCE_QUERY,
        parameters={
            "page_doc_id": "services/config",
            "evidence_uris": [
                "repo://src/main/Config.java#L10-L12",
                "repo://src/main/Config.java#L20",
            ],
        },
    )


def test_write_multiple_claims_on_one_page():
    store = MagicMock()
    claims = [
        Claim(id="c1", statement="Claim one.", evidence=[Evidence(resource="repo://A.java#L1")]),
        Claim(id="c2", statement="Claim two.", evidence=[Evidence(resource="repo://B.java#L5")]),
    ]
    page = _make_page(claims=claims)

    count, store = _make_writer([page], store)

    # All evidence URIs from all claims merged into one call
    assert count == 1
    store.execute_query.assert_called_once_with(
        _SET_SOURCE_EVIDENCE_QUERY,
        parameters={
            "page_doc_id": "api/endpoints",
            "evidence_uris": ["repo://A.java#L1", "repo://B.java#L5"],
        },
    )


def test_write_claim_with_no_evidence_sends_empty_list():
    store = MagicMock()
    claim = Claim(id="c1", statement="Unverified claim.", evidence=[])
    page = _make_page(claims=[claim])

    count, store = _make_writer([page], store)

    assert count == 1
    store.execute_query.assert_called_once_with(
        _SET_SOURCE_EVIDENCE_QUERY,
        parameters={
            "page_doc_id": "api/endpoints",
            "evidence_uris": [],
        },
    )


def test_write_skips_non_claim_pages():
    store = MagicMock()
    plain = _make_page(doc_id="overview")
    claim_page = _make_page(
        doc_id="api/auth",
        claims=[Claim(id="c1", statement="Auth uses JWT.", evidence=[Evidence(resource="repo://Auth.java#L1")])],
    )

    count, store = _make_writer([plain, claim_page], store)

    assert count == 1
    assert store.execute_query.call_count == 1
    _, kwargs = store.execute_query.call_args
    assert kwargs["parameters"]["page_doc_id"] == "api/auth"


def test_write_multiple_pages_with_claims():
    store = MagicMock()
    pages = [
        _make_page(
            doc_id="svc/a",
            claims=[Claim(id="c1", statement="A fact.", evidence=[Evidence(resource="repo://A.java#L1")])],
        ),
        _make_page(doc_id="svc/plain"),
        _make_page(
            doc_id="svc/b",
            claims=[
                Claim(id="c2", statement="B fact.", evidence=[Evidence(resource="repo://B.java#L2")]),
                Claim(id="c3", statement="C fact.", evidence=[Evidence(resource="repo://C.java#L3")]),
            ],
        ),
    ]

    count, store = _make_writer(pages, store)

    # One call per claim page (2), not per claim (3)
    assert count == 2
    assert store.execute_query.call_count == 2
    calls = store.execute_query.call_args_list
    first_params = calls[0][1]["parameters"]
    second_params = calls[1][1]["parameters"]
    assert first_params["page_doc_id"] == "svc/a"
    assert first_params["evidence_uris"] == ["repo://A.java#L1"]
    assert second_params["page_doc_id"] == "svc/b"
    assert second_params["evidence_uris"] == ["repo://B.java#L2", "repo://C.java#L3"]
