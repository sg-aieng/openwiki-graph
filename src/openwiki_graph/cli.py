from __future__ import annotations

import logging
import os
import shlex
import subprocess
import sys
import threading
from pathlib import Path

import click

from .config import DEFAULT_CONFIG_FILE, AppConfig, load_config
from .graph.indexer import OpenWikiGraphIndexer
from .graph.query import OpenWikiGraphQuerier
from .graph.skills import DEFAULT_SKILL, list_skills, resolve_skill
from .graph.edge_writer import RelatedPagesEdgeWriter
from .graph.evidence_writer import ClaimsEvidenceWriter
from .graph.delete_reconciler import DeleteReconciler
from .llm import build_llm, get_embed_dimensions
from .wiki.loader import OpenWikiLoader


class _Spinner:
    """ASCII spinner written directly to the terminal fd.

    Saves a duplicate of fd 2 before entering so it can write to the real
    terminal even while _FdStderrFilter has redirected fd 2 to a pipe.
    Only activates when fd 2 is a TTY (no-op in CI / redirected output).
    """

    _FRAMES = ("|", "/", "-", "\\")

    def __init__(self, message: str = "Thinking") -> None:
        self._message = message
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._tty_fd: int | None = None
        try:
            if os.isatty(2):
                self._tty_fd = os.dup(2)
        except OSError:
            pass

    def __enter__(self) -> "_Spinner":
        if self._tty_fd is not None:
            self._stop.clear()
            self._thread = threading.Thread(target=self._spin, daemon=True)
            self._thread.start()
        return self

    def _spin(self) -> None:
        fd = self._tty_fd
        frames = self._FRAMES
        i = 0
        while not self._stop.wait(0.1):
            line = f"\r{frames[i % len(frames)]}  {self._message}..."
            try:
                os.write(fd, line.encode())
            except OSError:
                break
            i += 1

    def __exit__(self, *_: object) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
        if self._tty_fd is not None:
            clear = "\r" + " " * (len(self._message) + 6) + "\r"
            try:
                os.write(self._tty_fd, clear.encode())
            except OSError:
                pass
            os.close(self._tty_fd)
            self._tty_fd = None


class _FdStderrFilter:
    """Suppress known noisy lines from stderr at the OS file-descriptor level.

    psycopg2 (libpq) calls write(2, ...) directly from C, bypassing Python's
    sys.stderr object entirely.  Replacing sys.stderr therefore has no effect.
    This context manager redirects fd 2 through an OS pipe, relays all lines
    that do NOT match the drop-list to the original stderr, then restores fd 2.
    """

    _DROP = (
        "collation version mismatch",
        "The database was created using collation version",
        "Rebuild all objects in this database that use the default collation",
        "ALTER DATABASE",
        "REFRESH COLLATION VERSION",
    )

    def __enter__(self) -> "_FdStderrFilter":
        self._saved_fd2 = os.dup(2)
        pipe_r, pipe_w = os.pipe()
        os.dup2(pipe_w, 2)
        os.close(pipe_w)

        saved = self._saved_fd2
        drop = self._DROP

        def _relay() -> None:
            with os.fdopen(pipe_r, "r", errors="replace") as reader:
                for line in reader:
                    if not any(p in line for p in drop):
                        os.write(saved, line.encode(errors="replace"))

        self._thread = threading.Thread(target=_relay, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *_: object) -> None:
        sys.stderr.flush()
        # Restore fd 2 → closes the pipe's write end → relay thread sees EOF.
        os.dup2(self._saved_fd2, 2)
        os.close(self._saved_fd2)
        self._thread.join(timeout=2)


def _first(*values):
    """Return the first value that is not None/empty-string."""
    for v in values:
        if v:
            return v
    return None


def _setup_llm(cfg: AppConfig):
    """Build LLM + embed model from config.

    Returns the llm object (or None for bedrock) and applies embed_model to
    LlamaIndex Settings so every component that reads Settings picks it up.

    Also sets GraphRAGConfig.embed_model and forces build_num_workers=1 when
    a non-default embed model is provided.  The toolkit's build pipeline spawns
    subprocess workers that lose non-picklable objects (embed models are excluded
    from the config snapshot).  With num_workers=1 the build runs in-process and
    the embed model set here is used directly.
    """
    llm, embed = build_llm(cfg.llm)
    if llm is not None or embed is not None:
        from llama_index.core import Settings
        from graphrag_toolkit.lexical_graph.config import GraphRAGConfig
        if llm is not None:
            Settings.llm = llm
            GraphRAGConfig.extraction_llm = llm
            GraphRAGConfig.response_llm = llm
        if embed is not None:
            Settings.embed_model = embed
            GraphRAGConfig.embed_model = embed
            GraphRAGConfig.build_num_workers = 1
            dims = get_embed_dimensions(embed)
            if dims is not None:
                GraphRAGConfig.embed_dimensions = dims
    return llm


def _require(value: str | None, flag: str, env_var: str, toml_key: str) -> str:
    if value:
        return value
    raise click.UsageError(
        f"Missing {flag}. Supply it via the flag, "
        f"the {env_var} environment variable, "
        f"or [stores] {toml_key} in openwiki-graph.toml."
    )


@click.group()
@click.option("--config", "-c", default=DEFAULT_CONFIG_FILE, show_default=True,
              type=click.Path(), help="Path to openwiki-graph.toml config file.")
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging.")
@click.pass_context
def cli(ctx: click.Context, config: str, verbose: bool) -> None:
    """Convert an OpenWiki directory into a queryable knowledge graph."""
    # Third-party libraries (graphrag_toolkit, llama_index, …) are noisy at INFO.
    # Show WARNING+ from them by default; our own logger stays at INFO (or DEBUG).
    root_level = logging.DEBUG if verbose else logging.WARNING
    own_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=root_level, stream=sys.stderr,
                        format="%(levelname)s %(name)s: %(message)s")
    logging.getLogger("openwiki_graph").setLevel(own_level)
    if not verbose:
        # neo4j driver emits a WARNING per query about missing versioning properties
        # when the graph was built without versioning enabled.
        logging.getLogger("neo4j.notifications").setLevel(logging.ERROR)
        logging.getLogger("neo4j").setLevel(logging.ERROR)
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    try:
        ctx.obj["config"] = load_config(config)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


def _load_openwiki_env() -> dict:
    """Read ~/.openwiki/.env and return its key/value pairs.

    openwiki normally calls loadOpenWikiEnv() inside the Node.js process, but
    that happens after module initialisation.  deepagents (the tracing backend)
    reads LANGCHAIN_TRACING_V2 at import time, so the value must be present in
    the subprocess environment *before* Node.js starts loading modules.  Passing
    the parsed file contents as explicit env vars to subprocess.run() is the
    simplest reliable fix.
    """
    import os as _os
    import re as _re

    env_path = Path(_os.path.expanduser("~/.openwiki/.env"))
    result: dict = {}
    if not env_path.exists():
        return result
    try:
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[len("export "):]
            eq = line.find("=")
            if eq <= 0:
                continue
            key = line[:eq].strip()
            raw_val = line[eq + 1:].strip()
            if not _re.match(r"^[A-Z_][A-Z0-9_]*$", key):
                continue
            if raw_val.startswith('"') and raw_val.endswith('"'):
                raw_val = raw_val[1:-1].replace('\\"', '"').replace("\\n", "\n").replace("\\r", "\r").replace("\\\\", "\\")
            result[key] = raw_val
    except Exception:
        pass
    return result


def _run_openwiki(repo_root: str, wiki_root: str) -> None:
    """Run `openwiki code --init` or `--update` in repo_root (non-interactively).

    openwiki switches to its non-interactive path automatically when stdin is
    not a TTY, so passing stdin=DEVNULL is all that is needed.

    Uses --init for a first-time run (wiki directory absent or empty) and
    --update when the wiki already exists.
    """
    import os as _os
    import shutil
    if shutil.which("openwiki"):
        base = ["openwiki", "code"]
    elif shutil.which("npx"):
        base = ["npx", "openwiki", "code"]
    else:
        raise click.ClickException(
            "`openwiki` not found. Install it with: npm install -g openwiki"
        )

    wiki_path = Path(wiki_root)
    has_wiki = wiki_path.is_dir() and any(wiki_path.glob("*.md"))
    flag = "--update" if has_wiki else "--init"

    cmd = base + [flag]

    # Build subprocess env: start from current env, overlay ~/.openwiki/.env
    # values for keys not already set, then force LANGCHAIN_TRACING_V2=false so
    # deepagents (which reads it at import time) never attempts tracing.
    openwiki_file_env = _load_openwiki_env()
    proc_env = {**_os.environ}
    for k, v in openwiki_file_env.items():
        if k not in proc_env:
            proc_env[k] = v
    proc_env.setdefault("LANGCHAIN_TRACING_V2", "false")

    def _precreate_plan_dirs() -> bool:
        """Pre-create directories from .run.json plan. Returns True if any were created."""
        # openwiki bug workaround: isNotFoundBackendError checks for "not found"
        # but Node's ENOENT says "no such file or directory".  When restoring a
        # page that was never written (markdown == null), the backend tries to
        # delete the file; if the parent directory doesn't exist lstat raises
        # ENOENT and openwiki treats it as fatal.  Pre-creating the directories
        # lets the delete safely stat the (missing) file.
        import json as _json
        state_file = wiki_path / ".run.json"
        if not state_file.exists():
            return False
        try:
            state = _json.loads(state_file.read_text())
            created = False
            for page in state.get("plan", {}).get("pages", []):
                raw_path = page.get("path", "")
                rel = raw_path.lstrip("/")
                parent = (Path(repo_root) / rel).parent
                if not parent.exists():
                    parent.mkdir(parents=True, exist_ok=True)
                    created = True
            return created
        except Exception:
            return False

    _precreate_plan_dirs()

    click.echo(f"Running: {shlex.join(cmd)} (cwd={repo_root})")
    result = subprocess.run(cmd, cwd=repo_root, stdin=subprocess.DEVNULL, env=proc_env)

    if result.returncode != 0:
        # On first run openwiki may fail after writing its plan to .run.json but
        # before the page directories exist.  Pre-create them and retry once.
        if _precreate_plan_dirs():
            click.echo(f"Retrying after pre-creating wiki directories…")
            result = subprocess.run(cmd, cwd=repo_root, stdin=subprocess.DEVNULL, env=proc_env)

    if result.returncode != 0:
        raise click.ClickException(
            f"`openwiki code {flag}` exited with code {result.returncode}"
        )


@cli.command()
@click.option("--update", "run_update", is_flag=True, default=False,
              help="Regenerate the wiki (`openwiki code --update`) before indexing. "
                   "Requires --repo-root or [wiki] repo_root in config. "
                   "Can be combined with --full-rebuild.")
@click.option("--full-rebuild", is_flag=True, default=False,
              help="Drop and rebuild the entire graph instead of doing an incremental update. "
                   "Can be combined with --update.")
@click.option("--repo-root", default=None, type=click.Path(),
              help="Root of the repository to document (required for --update). "
                   "Overrides config [wiki] repo_root.")
@click.option("--wiki-root", default=None, type=click.Path(),
              help="Path to the OpenWiki directory. Overrides config [wiki] root.")
@click.option("--graph-store", default=None, envvar="GRAPH_STORE",
              help="Graph store connection string. Overrides config [stores] graph.")
@click.option("--vector-store", default=None, envvar="VECTOR_STORE",
              help="Vector store connection string. Overrides config [stores] vector.")
@click.option("--wiki-id", default=None,
              help="Namespace prefix for multi-repo graphs (e.g. 'producer-api'). "
                   "Scopes all doc_ids so multiple repos can share one graph without collision. "
                   "Overrides config [wiki] id.")
@click.option("--skip-reconcile-deletions", is_flag=True, default=False,
              help="Skip deleting graph nodes for wiki pages removed from disk. "
                   "Deletion reconciliation runs by default on incremental updates. "
                   "No effect with --full-rebuild (which rebuilds from scratch). "
                   "Overrides config [pipeline] skip_reconcile_deletions.")
@click.pass_context
def pipeline(
    ctx: click.Context,
    run_update: bool,
    full_rebuild: bool,
    repo_root: str | None,
    wiki_root: str | None,
    graph_store: str | None,
    vector_store: str | None,
    wiki_id: str | None,
    skip_reconcile_deletions: bool,
) -> None:
    """Index an OpenWiki directory into the knowledge graph.

    Without flags: incrementally re-indexes existing wiki files on disk.

    With --update: runs `openwiki code --update` to regenerate the wiki first,
    then does an incremental graph update.

    With --full-rebuild: drops and rebuilds the entire graph from the wiki on
    disk (no wiki regeneration unless --update is also passed).

    --update and --full-rebuild can be combined: regenerate the wiki then do a
    full graph rebuild.
    """
    cfg: AppConfig = ctx.obj["config"]

    effective_repo_root = _first(repo_root, cfg.wiki.repo_root)
    effective_wiki_root = _first(
        wiki_root,
        cfg.wiki.root,
        (str(Path(effective_repo_root) / "openwiki") if effective_repo_root else None),
    )
    if not effective_wiki_root:
        raise click.UsageError(
            "Provide --wiki-root, set [wiki] root in openwiki-graph.toml, "
            "or provide --repo-root (wiki defaults to <repo_root>/openwiki)."
        )

    if run_update:
        if not effective_repo_root:
            raise click.UsageError(
                "--update requires --repo-root or [wiki] repo_root in openwiki-graph.toml."
            )
        _run_openwiki(effective_repo_root, effective_wiki_root)
    resolved_graph = _require(
        _first(graph_store, cfg.stores.graph),
        "--graph-store", "GRAPH_STORE", "graph",
    )
    resolved_vector = _require(
        _first(vector_store, cfg.stores.vector),
        "--vector-store", "VECTOR_STORE", "vector",
    )

    effective_wiki_id = _first(wiki_id, cfg.wiki.id) or ""
    extraction_llm = _setup_llm(cfg)
    indexer = OpenWikiGraphIndexer(
        wiki_root=effective_wiki_root,
        graph_store=resolved_graph,
        vector_store=resolved_vector,
        extraction_llm=extraction_llm,
        extraction_dir=cfg.indexing.extraction_dir,
        chunk_size=cfg.indexing.chunk_size,
        chunk_overlap=cfg.indexing.chunk_overlap,
        wiki_id=effective_wiki_id,
    )
    effective_full_rebuild = full_rebuild or cfg.pipeline.full_rebuild
    if effective_full_rebuild:
        indexer.index(show_progress=True)
    else:
        indexer.update(show_progress=True)

    pages = OpenWikiLoader(effective_wiki_root, wiki_id=effective_wiki_id).load_pages()
    RelatedPagesEdgeWriter(graph_store=resolved_graph, pages=pages).write()
    ClaimsEvidenceWriter(graph_store=resolved_graph, pages=pages).write()

    if not effective_full_rebuild and not (skip_reconcile_deletions or cfg.pipeline.skip_reconcile_deletions):
        DeleteReconciler(
            graph_store=resolved_graph,
            vector_store=resolved_vector,
            wiki_root=effective_wiki_root,
            wiki_id=effective_wiki_id,
        ).reconcile()

    click.echo("Pipeline complete.")


@cli.command()
@click.argument("question")
@click.option("--graph-store", default=None, envvar="GRAPH_STORE",
              help="Graph store connection string. Overrides config [stores] graph.")
@click.option("--vector-store", default=None, envvar="VECTOR_STORE",
              help="Vector store connection string. Overrides config [stores] vector.")
@click.option("--skill", default=DEFAULT_SKILL, show_default=True,
              help="Named skill that sets the LLM system prompt. "
                   f"Built-in: {', '.join(list_skills())}. "
                   "Or pass a path to a .txt file containing a custom prompt.")
@click.option("--system-prompt", default=None,
              help="Explicit system prompt text, overrides --skill entirely.")
@click.pass_context
def query(
    ctx: click.Context,
    question: str,
    graph_store: str | None,
    vector_store: str | None,
    skill: str,
    system_prompt: str | None,
) -> None:
    """Query the knowledge graph with a natural-language question."""
    cfg: AppConfig = ctx.obj["config"]

    resolved_graph = _require(
        _first(graph_store, cfg.stores.graph),
        "--graph-store", "GRAPH_STORE", "graph",
    )
    resolved_vector = _require(
        _first(vector_store, cfg.stores.vector),
        "--vector-store", "VECTOR_STORE", "vector",
    )

    if system_prompt is None:
        try:
            system_prompt = resolve_skill(skill)
        except ValueError as exc:
            raise click.UsageError(str(exc)) from exc

    extraction_llm = _setup_llm(cfg)
    querier = OpenWikiGraphQuerier(
        graph_store=resolved_graph,
        vector_store=resolved_vector,
        extraction_llm=extraction_llm,
    )
    if ctx.obj.get("verbose"):
        response = querier.query(question, system_prompt=system_prompt)
    else:
        # _Spinner saves the real terminal fd BEFORE _FdStderrFilter redirects fd 2,
        # so the spinner writes directly to the terminal throughout.
        with _Spinner("Thinking"):
            with _FdStderrFilter():
                response = querier.query(question, system_prompt=system_prompt)
    click.echo(str(response))


@cli.command()
@click.argument("skill_name", default=None, required=False, metavar="[SKILL]")
def skills(skill_name: str | None) -> None:
    """List available skills or show a skill's system prompt.

    Without arguments, lists all built-in skill names.
    With a SKILL name, prints the full system prompt for that skill.
    """
    if skill_name is None:
        click.echo("Built-in skills:")
        for name in list_skills():
            marker = " (default)" if name == DEFAULT_SKILL else ""
            click.echo(f"  {name}{marker}")
        click.echo("\nPass a file path to --skill to use a custom prompt.")
    else:
        try:
            prompt = resolve_skill(skill_name)
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc
        click.echo(prompt)
