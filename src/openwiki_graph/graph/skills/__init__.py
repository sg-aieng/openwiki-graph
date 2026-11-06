from __future__ import annotations

from pathlib import Path

_SKILLS_DIR = Path(__file__).parent

# Built-in skills discovered from .md files in this directory.
SKILLS: dict[str, Path] = {
    p.stem: p for p in sorted(_SKILLS_DIR.glob("*.md"))
}

DEFAULT_SKILL = "multi-repo"


def resolve_skill(name: str) -> str:
    """Return the system prompt for a named built-in skill or a path to a local .md file.

    Resolution order:
    1. Built-in skill by name (e.g. "multi-repo", "general").
    2. Path to a local file (absolute or relative) whose contents become the system prompt.

    Raises ValueError for unknown names with no matching file.
    """
    if name in SKILLS:
        return SKILLS[name].read_text(encoding="utf-8")
    path = Path(name)
    if path.exists():
        return path.read_text(encoding="utf-8")
    raise ValueError(
        f"Unknown skill {name!r}. "
        f"Built-in skills: {list(SKILLS)}. "
        f"Or pass a path to a local .md file."
    )


def list_skills() -> list[str]:
    return list(SKILLS.keys())
