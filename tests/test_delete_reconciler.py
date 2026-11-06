from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from openwiki_graph.models import OpenWikiPage
from openwiki_graph.graph.delete_reconciler import DeleteReconciler, _LIST_SOURCES_QUERY


def _make_page(doc_id: str) -> OpenWikiPage:
    return OpenWikiPage(
        path=Path(f"/wiki/{doc_id}.md"),
        doc_id=doc_id,
        title="Test Page",
        description="",
        text="Content.",
        tags=[],
        related_pages=[],
        wiki_type="overview",
        claims=[],
    )


@pytest.fixture
def mock_graph_store():
    store = MagicMock()
    store.execute_query = MagicMock()
    return store


@pytest.fixture
def mock_vector_store():
    return MagicMock()


def _run_reconciler(wiki_pages, graph_rows, mock_graph_store, mock_vector_store):
    """Helper: runs reconcile() with mocked graph/vector stores and loader."""
    mock_graph_store.execute_query.return_value = graph_rows
    mock_loader = MagicMock()
    mock_loader.load_pages.return_value = wiki_pages
    r = DeleteReconciler(
        graph_store="bolt://localhost:7687",
        vector_store="postgresql://localhost:5432/db",
        wiki_root="/fake/wiki",
    )
    with (
        patch(
            "openwiki_graph.graph.delete_reconciler.GraphStoreFactory.for_graph_store",
            return_value=mock_graph_store,
        ),
        patch(
            "openwiki_graph.graph.delete_reconciler.VectorStoreFactory.for_vector_store",
            return_value=mock_vector_store,
        ),
        patch(
            "openwiki_graph.graph.delete_reconciler.OpenWikiLoader",
            return_value=mock_loader,
        ),
        patch(
            "openwiki_graph.graph.delete_reconciler.DeleteSources",
        ) as mock_deleter_cls,
    ):
        count = r.reconcile()
    mock_delete = mock_deleter_cls.return_value.delete_source_documents
    return count, mock_delete


def test_reconcile_empty_graph_returns_zero(mock_graph_store, mock_vector_store):
    count, mock_delete = _run_reconciler(
        wiki_pages=[_make_page("api/users")],
        graph_rows=[],
        mock_graph_store=mock_graph_store,
        mock_vector_store=mock_vector_store,
    )
    assert count == 0
    mock_delete.assert_not_called()


def test_reconcile_all_pages_present_returns_zero(mock_graph_store, mock_vector_store):
    rows = [
        {"doc_id": "api/users", "source_id": "uuid-1"},
        {"doc_id": "api/orders", "source_id": "uuid-2"},
    ]
    wiki_pages = [_make_page("api/users"), _make_page("api/orders")]
    count, mock_delete = _run_reconciler(
        wiki_pages=wiki_pages,
        graph_rows=rows,
        mock_graph_store=mock_graph_store,
        mock_vector_store=mock_vector_store,
    )
    assert count == 0
    mock_delete.assert_not_called()


def test_reconcile_deleted_page_calls_delete(mock_graph_store, mock_vector_store):
    rows = [
        {"doc_id": "api/users", "source_id": "uuid-1"},
        {"doc_id": "api/deleted", "source_id": "uuid-2"},  # gone from disk
    ]
    wiki_pages = [_make_page("api/users")]  # only users remains
    count, mock_delete = _run_reconciler(
        wiki_pages=wiki_pages,
        graph_rows=rows,
        mock_graph_store=mock_graph_store,
        mock_vector_store=mock_vector_store,
    )
    assert count == 1
    mock_delete.assert_called_once_with(source_ids=["uuid-2"])


def test_reconcile_multiple_deleted_pages(mock_graph_store, mock_vector_store):
    rows = [
        {"doc_id": "a", "source_id": "uuid-a"},
        {"doc_id": "b", "source_id": "uuid-b"},
        {"doc_id": "c", "source_id": "uuid-c"},
    ]
    wiki_pages = [_make_page("a")]  # b and c deleted
    count, mock_delete = _run_reconciler(
        wiki_pages=wiki_pages,
        graph_rows=rows,
        mock_graph_store=mock_graph_store,
        mock_vector_store=mock_vector_store,
    )
    assert count == 2
    # source_ids are sorted by doc_id in the reconciler
    mock_delete.assert_called_once_with(source_ids=["uuid-b", "uuid-c"])


def test_reconcile_rows_missing_doc_id_are_skipped(mock_graph_store, mock_vector_store):
    rows = [
        {"doc_id": None, "source_id": "uuid-x"},   # no doc_id → skip
        {"doc_id": "", "source_id": "uuid-y"},      # empty → skip
        {"doc_id": "api/users", "source_id": "uuid-1"},
    ]
    wiki_pages = [_make_page("api/users")]
    count, mock_delete = _run_reconciler(
        wiki_pages=wiki_pages,
        graph_rows=rows,
        mock_graph_store=mock_graph_store,
        mock_vector_store=mock_vector_store,
    )
    assert count == 0
    mock_delete.assert_not_called()


def test_reconcile_uses_list_sources_query(mock_graph_store, mock_vector_store):
    mock_graph_store.execute_query.return_value = []
    r = DeleteReconciler(
        graph_store="bolt://localhost:7687",
        vector_store="postgresql://localhost:5432/db",
        wiki_root="/fake/wiki",
    )
    mock_loader = MagicMock()
    mock_loader.load_pages.return_value = []
    with (
        patch(
            "openwiki_graph.graph.delete_reconciler.GraphStoreFactory.for_graph_store",
            return_value=mock_graph_store,
        ),
        patch(
            "openwiki_graph.graph.delete_reconciler.OpenWikiLoader",
            return_value=mock_loader,
        ),
    ):
        r.reconcile()
    mock_graph_store.execute_query.assert_called_once_with(_LIST_SOURCES_QUERY)
