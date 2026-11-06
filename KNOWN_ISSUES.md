# Known Issues

## openwiki non-interactive mode: `LANGCHAIN_TRACING_V2` set too late

**Severity**: Medium
**Affects**: `pipeline --update`

When `openwiki` is run as a subprocess (non-interactive), the `deepagents` library
reads `LANGCHAIN_TRACING_V2` at Node.js module import time — before openwiki's own
`loadOpenWikiEnv()` call has had a chance to load `~/.openwiki/.env`. If the env
file sets `LANGCHAIN_TRACING_V2=false` but the variable is absent from the shell
environment, deepagents attempts to connect to a Langfuse backend and the run fails.

**Workaround (implemented)**: `_load_openwiki_env()` in `cli.py` reads
`~/.openwiki/.env` in Python before spawning the subprocess, and passes all its
values explicitly as `env=proc_env` to `subprocess.run()`. It also forces
`proc_env.setdefault("LANGCHAIN_TRACING_V2", "false")` as a safety net.

**Upstream fix needed**: openwiki should load its env file earlier, before deepagents
is imported. Filed against `langchain-ai/openwiki`.

---

## openwiki ENOENT on page restore when parent directory is missing

**Severity**: Medium
**Affects**: `pipeline --update` (first run, or after directory structure changes)

When openwiki tries to restore a page that was never written (markdown == null in
`.run.json`), it attempts to delete the file. If the page's parent directory does
not yet exist, Node.js `lstat` raises `ENOENT`. openwiki's `isNotFoundBackendError`
check tests for the string `"not found"` but the Node.js error message says
`"no such file or directory"`, so the error is not caught and the run fails.

**Workaround (implemented)**: `_precreate_plan_dirs()` in `cli.py` reads the
`.run.json` plan before each openwiki invocation and pre-creates all parent
directories. If openwiki fails on the first attempt, the directories are created
and the command is retried once automatically.

**Upstream fix needed**: openwiki's `isNotFoundBackendError` should match the
Node.js ENOENT message, or the restore path should handle a missing parent directory
gracefully. Filed against `langchain-ai/openwiki`.

---

## Cross-repo `RELATED_TO` edges are not created between repositories

**Severity**: Low
**Affects**: multi-repo graphs

`RelatedPagesEdgeWriter` creates `RELATED_TO` edges between `__Source__` nodes
based on `relatedPages` frontmatter in wiki pages. In practice, OpenWiki-generated
pages do not include `relatedPages` frontmatter, so no edges are written and
cross-repo connections rely entirely on shared `__Topic__` nodes (which graphrag-toolkit
MERGEs by value).

Shared topic nodes connect repositories at the topic level, but there are no direct
source-to-source edges encoding "this page in repo A references this page in repo B".

**What needs to happen**: either OpenWiki should emit `relatedPages` frontmatter
when it detects cross-repo references, or openwiki-graph needs an alternative
writer that infers cross-repo edges from the graph topology (e.g. pages in different
repos that share many topic nodes).

---

## Tenant-aware indexing is incomplete

**Severity**: High
**Affects**: `OpenWikiGraphIndexer`, `RelatedPagesEdgeWriter`, `ClaimsEvidenceWriter`

`OpenWikiGraphIndexer` accepts a `tenant_id` at `_indexer.py` and passes it to
`LexicalGraphIndex`, which scopes graph labels and queries accordingly.
However, the two post-index writers — `RelatedPagesEdgeWriter` and
`ClaimsEvidenceWriter` — call `GraphStoreFactory.for_graph_store` directly with
only the connection string. They receive an unscoped graph store, so their Cypher
writes (`RELATED_TO` edges and `evidence_uris` properties) bypass the tenant
namespace. In a multi-tenant deployment this will either miss the tenant's nodes
or silently write to the wrong graph region.

**What needs to happen**: pass `tenant_id` through to both writers and use it when
constructing the graph store, or pass a pre-built scoped store from the indexer.
The toolkit API for scoped stores needs verification before settling on an approach.

**Workaround**: `tenant_id` is not exposed in the CLI and defaults to `None`
(no tenancy). Do not set it programmatically unless you can verify both writers
against a live multi-tenant instance.

---

## Graph integration tests are missing

**Severity**: Low
**Affects**: `ClaimsEvidenceWriter`, `RelatedPagesEdgeWriter`, `OpenWikiGraphIndexer`

Current tests mock `GraphStoreFactory` and assert Cypher call arguments. There are
no end-to-end tests that run against a real (or embedded) Neo4j instance to verify:

- `RELATED_TO` edges appear with the correct `doc_id` anchors.
- `evidence_uris` lands on the correct `__Source__` node.
- Pre-seeded claims produce the right number of statement nodes.
- Deleted-page reconciliation removes the correct subgraph.
- Multi-tenant label scoping works for edges and evidence writes.

**What needs to happen**: add a pytest fixture that starts an embedded Neo4j instance
(e.g. via `testcontainers-python`) and run the full pipeline against it in a
`tests/integration/` directory, gated behind a `--run-integration` marker.
