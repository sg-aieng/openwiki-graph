from __future__ import annotations

import json
from pathlib import Path

from ..models import Claim, Evidence


def load_claims(claims_path: Path) -> list[Claim]:
    """Parse a .claims/<page>.json sidecar into a list of Claims.

    Returns an empty list when no sidecar exists for the page.
    """
    if not claims_path.exists():
        return []
    data = json.loads(claims_path.read_text(encoding="utf-8"))
    return [
        Claim(
            id=c["id"],
            statement=c["statement"],
            evidence=[
                Evidence(resource=e["resource"], version=e.get("version", ""))
                for e in c.get("evidence", [])
            ],
        )
        for c in data.get("claims", [])
    ]
