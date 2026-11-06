from __future__ import annotations

import logging
from typing import Any, Dict

from graphrag_toolkit.lexical_graph.indexing.extract import LLMPropositionExtractor
from llama_index.core.schema import BaseNode

from ..enricher import PROPOSITIONS_KEY

logger = logging.getLogger(__name__)


class SkippingLLMPropositionExtractor(LLMPropositionExtractor):
    """LLMPropositionExtractor that honours pre-seeded PROPOSITIONS_KEY.

    When ClaimsEnricher has already set PROPOSITIONS_KEY on a node (verified
    OpenWiki Claims), this extractor returns those values unchanged instead of
    calling the LLM.  Nodes without pre-seeded propositions go through the
    normal LLM extraction path.
    """

    async def _extract_propositions_for_node(self, node: BaseNode) -> Dict[str, Any]:
        existing = node.metadata.get(PROPOSITIONS_KEY)
        if existing:
            logger.debug(
                "Skipping LLM extraction for node %s — %d pre-seeded proposition(s)",
                node.node_id,
                len(existing),
            )
            return {PROPOSITIONS_KEY: existing}
        return await super()._extract_propositions_for_node(node)
