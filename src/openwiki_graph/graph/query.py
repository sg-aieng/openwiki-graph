from __future__ import annotations

from typing import Any

from graphrag_toolkit.lexical_graph import LexicalGraphQueryEngine

from .skills import DEFAULT_SKILL, resolve_skill


class OpenWikiGraphQuerier:
    """Query a LexicalGraph knowledge graph using a named skill or custom system prompt.

    Usage::

        querier = OpenWikiGraphQuerier(
            graph_store="bolt://...",
            vector_store="postgresql://...",
            extraction_llm=llm,
        )
        response = querier.query("Who are the consumers of the user API?")
        response = querier.query("...", skill="api-design")
        response = querier.query("...", system_prompt="Custom prompt text {search_results}")
    """

    def __init__(
        self,
        graph_store: str,
        vector_store: str,
        extraction_llm: Any = None,
        tenant_id: Any = None,
    ) -> None:
        self._graph_conn = graph_store
        self._vector_conn = vector_store
        self._extraction_llm = extraction_llm
        self._tenant_id = tenant_id

    def query(
        self,
        question: str,
        skill: str = DEFAULT_SKILL,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Run a traversal-based query and return the LlamaIndex Response.

        Args:
            question: Natural language question.
            skill: Named built-in skill or path to a prompt file. Ignored when
                ``system_prompt`` is provided. Defaults to ``"multi-repo"``.
            system_prompt: Explicit system prompt override. When set, ``skill``
                is not used.
            **kwargs: Forwarded to ``LexicalGraphQueryEngine.for_traversal_based_search``.
        """
        effective_prompt = system_prompt if system_prompt is not None else resolve_skill(skill)
        if self._extraction_llm is not None:
            kwargs.setdefault("llm", self._extraction_llm)
        engine = LexicalGraphQueryEngine.for_traversal_based_search(
            graph_store=self._graph_conn,
            vector_store=self._vector_conn,
            tenant_id=self._tenant_id,
            system_prompt=effective_prompt,
            **kwargs,
        )
        return engine.query(question)
