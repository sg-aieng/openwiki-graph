from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Evidence:
    resource: str
    version: str = ""


@dataclass
class Claim:
    id: str
    statement: str
    evidence: list[Evidence] = field(default_factory=list)
