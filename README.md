# openwiki-graph

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![OpenWiki](https://img.shields.io/badge/OpenWiki-langchain--ai-1A6FB5.svg)](https://github.com/langchain-ai/openwiki)
[![graphrag-toolkit](https://img.shields.io/badge/graphrag--toolkit-%E2%89%A53.19-orange.svg)](https://github.com/awslabs/graphrag-toolkit)

**openwiki-graph** converts an [OpenWiki](https://github.com/langchain-ai/openwiki) directory into a
queryable knowledge graph using the [graphrag-lexical-graph](https://github.com/awslabs/graphrag-toolkit) pipeline from AWS Labs.

---

## Table of Contents

- [What is openwiki-graph?](#what-is-openwiki-graph)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Quick Start](#quick-start)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Store Setup](#store-setup)
  - [Configuration](#configuration)
  - [Run your first pipeline](#run-your-first-pipeline)
- [Usage](#usage)
  - [pipeline](#pipeline--ingest-and-index)
  - [query](#query--ask-a-natural-language-question)
  - [skills](#skills--list-or-inspect-query-skills)
- [Multi-repo graphs](#multi-repo-graphs)
- [Configuration Reference](#configuration-reference)
- [What Gets Indexed](#what-gets-indexed)
- [Non-Bedrock Embeddings](#non-bedrock-embeddings)
- [Known Issues](#known-issues)

---

## What is openwiki-graph?

openwiki-graph bridges [OpenWiki](https://github.com/langchain-ai/openwiki) — LangChain's DeepAgents-powered wiki generator — with [graphrag-lexical-graph](https://github.com/awslabs/graphrag-toolkit), AWS Labs' production-grade knowledge graph toolkit. It ingests structured OpenWiki pages, respects pre-verified claim evidence, and builds a rich, traversable graph that lets you ask natural language questions over your entire codebase.

It runs as a CLI and supports multiple LLM and store backends without code changes.

---

## Key Features

### Claims-aware indexing
Pre-verified OpenWiki claims are injected as propositions before LLM extraction, bypassing redundant re-extraction. This makes indexing faster, cheaper, and more accurate than starting from raw text.

### Explicit relational edges
`relatedPages` frontmatter links are materialised as typed `RELATED_TO` edges in the graph, encoding navigational knowledge that vector similarity alone cannot reliably recover.

### Incremental updates
Re-index only changed pages on each run. A reconciler automatically detects and removes stale nodes for deleted wiki pages, keeping the graph consistent with the wiki on disk.

### Multi-repo graphs
Index multiple repositories into a single shared graph. Repositories are namespaced by a `wiki_id` prefix on all document IDs, and shared `__Topic__` nodes connect them so cross-repo questions surface inter-repository relationships.

### Pluggable backends
Any graph or vector store supported by [graphrag-toolkit](https://github.com/awslabs/graphrag-toolkit) works without code changes — select your backend via connection string.

### Multiple LLM providers
Supports OpenAI, Ollama (local), and Amazon Bedrock out of the box. Swap providers by changing two lines in your config.

### Named query skills
The query command ships with built-in skills (system prompts tuned for different question domains) and accepts a path to your own `.md` prompt file. No code changes needed to customise query behaviour.

---

## System Architecture

```
Repository source code
         │
         ▼  openwiki code --update
openwiki/ directory
  .md pages + .claims/ sidecars
         │
         ▼
  OpenWikiLoader          Stage 1 — Load
  Parses frontmatter, sections, claims → LlamaIndex Documents
         │
         ▼
  ClaimsEnricher          Stage 2 — Enrich
  Injects Claims as pre-seeded PROPOSITIONS_KEY metadata
         │
         ▼
  LexicalGraphIndex       Stage 3 — Index
  ├── ExtractionPipeline  TopicExtractor · LLMPropositionExtractor
  └── BuildPipeline       GraphConstruction · VectorIndexing
         │
   ┌─────┴──────┐
   ▼            ▼
Graph Store  Vector Store
(Neo4j, …)  (pgvector, …)
         │
         ▼
  Post-index writers      Stage 4 — Enrich graph
  ├── RelatedPagesEdgeWriter   RELATED_TO edges from relatedPages
  ├── ClaimsEvidenceWriter     evidence_uris on __Source__ nodes
  └── DeleteReconciler         remove orphaned nodes for deleted pages
```

The graph schema follows the toolkit's standard node hierarchy (`__Source__`, `__Chunk__`, `__Statement__`, `__Topic__`, `__Fact__`, `__Entity__`) with one wiki-specific addition: `RELATED_TO` edges between source nodes.

---

## Quick Start

### Prerequisites

- **Python 3.10+**
- A supported **graph store** and **vector store** — see [graphrag-toolkit](https://github.com/awslabs/graphrag-toolkit) for the full list
- An LLM API key (OpenAI, AWS Bedrock) or a running Ollama instance

### Installation

```bash
# Clone the repo
git clone https://github.com/your-org/openwiki-graph.git
cd openwiki-graph

# Install with your chosen LLM provider
pip install -e ".[openai]"        # OpenAI
pip install -e ".[ollama]"        # Ollama (local, free)

# Include store drivers alongside the LLM extra
pip install -e ".[openai,neo4j,pgvector]"
```

### Store Setup

The examples below use **Neo4j** (graph store) and **PostgreSQL + pgvector** (vector store). Any store supported by graphrag-toolkit works in the same way — just swap the connection string.

#### Neo4j

```bash
docker run -d --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/yourpassword \
  neo4j:5
```

Schema indexes are created automatically on first run.

#### PostgreSQL + pgvector

```bash
psql -U postgres -c "CREATE DATABASE openwiki;"
psql -U postgres -d openwiki -c "CREATE EXTENSION IF NOT EXISTS vector;"
psql -U postgres -d openwiki -c "CREATE SCHEMA IF NOT EXISTS graphrag;"
```

> **If you skip the schema step** you will get:
> `psycopg2.errors.InvalidSchemaName: schema "graphrag" does not exist`

### Configuration

Copy the example config and fill in your values:

```bash
cp openwiki-graph.toml.example openwiki-graph.toml
```

Minimal config:

```toml
[wiki]
root      = "openwiki"           # path to the OpenWiki directory
repo_root = "/path/to/my-repo"   # repository root (required for --update)

[stores]
graph  = "bolt://neo4j:yourpassword@localhost:7687"
vector = "postgresql://postgres:yourpassword@localhost:5432/openwiki"

[llm]
provider    = "openai"
model       = "gpt-4o-mini"
embed_model = "text-embedding-3-small"
```

Set credentials in your shell (not in the config file):

```bash
export OPENAI_API_KEY=sk-...          # OpenAI
export AWS_DEFAULT_REGION=us-east-1   # Bedrock
```

### Run your first pipeline

```bash
# Generate (or refresh) the wiki, then index into the graph
openwiki-graph --config openwiki-graph.toml pipeline --update \
  --repo-root /path/to/my-repo

# Query the result
openwiki-graph --config openwiki-graph.toml query "what port does the service run on?"
```

---

## Usage

### `pipeline` — ingest and index

```bash
openwiki-graph [--config FILE] pipeline [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--update` | Run `openwiki code --update` to regenerate wiki pages before indexing |
| `--full-rebuild` | Drop and rebuild the entire graph from the wiki on disk |
| `--repo-root PATH` | Repository root (required for `--update`). Overrides `[wiki] repo_root` |
| `--wiki-root PATH` | Path to the OpenWiki directory. Overrides `[wiki] root` |
| `--wiki-id TEXT` | Namespace prefix for multi-repo graphs (e.g. `producer-api`). Overrides `[wiki] id` |
| `--graph-store TEXT` | Graph store connection string. Overrides `[stores] graph` / `$GRAPH_STORE` |
| `--vector-store TEXT` | Vector store connection string. Overrides `[stores] vector` / `$VECTOR_STORE` |
| `--skip-reconcile-deletions` | Skip removal of graph nodes for deleted wiki pages |

**Common patterns:**

```bash
# First time: generate the wiki from scratch and build the graph
openwiki-graph pipeline --update --full-rebuild --repo-root /path/to/my-repo

# Day-to-day: regenerate wiki and sync the graph incrementally
openwiki-graph pipeline --update --repo-root /path/to/my-repo

# After large structural changes: full graph rebuild without regenerating the wiki
openwiki-graph pipeline --full-rebuild --wiki-root /path/to/my-repo/openwiki

# Graph-only sync: wiki already up to date on disk
openwiki-graph pipeline --wiki-root /path/to/my-repo/openwiki
```

### `query` — ask a natural language question

```bash
openwiki-graph [--config FILE] query QUESTION [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--skill TEXT` | `multi-repo` | Named built-in skill or path to a local `.md` prompt file |
| `--system-prompt TEXT` | — | Explicit system prompt, overrides `--skill` entirely |
| `--graph-store TEXT` | config | Graph store connection string |
| `--vector-store TEXT` | config | Vector store connection string |

```bash
# Default skill (multi-repo software graph)
openwiki-graph query "who are the consumers of the user API?"

# Use a different built-in skill
openwiki-graph query "what does the /users endpoint return?" --skill general

# Use a custom skill from a local file
openwiki-graph query "..." --skill ~/my-skills/security-review.md

# One-off system prompt override
openwiki-graph query "..." --system-prompt "You are a security auditor..."
```

### `skills` — list or inspect query skills

```bash
# List all built-in skills
openwiki-graph skills

# Show the full system prompt for a skill
openwiki-graph skills multi-repo
```

Built-in skills live in `src/openwiki_graph/graph/skills/` as `.md` files. Add a new built-in by dropping a `.md` file into that directory — no code changes needed.

---

## Multi-repo graphs

You can index multiple repositories into a single graph instance. Each repository gets a `wiki_id` namespace that prefixes all its document IDs (e.g. `producer-api::services/user-api.md`), preventing collisions between repos.

Repositories are still connected at the graph level via shared `__Topic__` nodes — graphrag-toolkit merges topic nodes by value, so a topic like "User API" that appears in both `producer-api` and `consumer-api` becomes a single node with edges to both.

**Example: indexing two repos into one graph**

```bash
# Index producer-api
openwiki-graph pipeline \
  --wiki-root /path/to/producer-api/openwiki \
  --wiki-id producer-api

# Index consumer-api
openwiki-graph pipeline \
  --wiki-root /path/to/consumer-api/openwiki \
  --wiki-id consumer-api

# Query across both
openwiki-graph query "which repository consumes the user API?"
```

The `multi-repo` skill (default) is tuned to synthesise cross-repo relationships in its answers and to cite the specific repository name from the source path prefix.

---

## Configuration Reference

Values in `openwiki-graph.toml` are the baseline. CLI flags always override the config file; for the two store fields, environment variables (`GRAPH_STORE`, `VECTOR_STORE`) sit between them. Full precedence order: **CLI flag > environment variable > config file**.

| Field | CLI override | Description |
|-------|-------------|-------------|
| `[wiki] root` | `--wiki-root` | Path to the OpenWiki directory |
| `[wiki] repo_root` | `--repo-root` | Repository root for `openwiki code --update` |
| `[wiki] id` | `--wiki-id` | Namespace prefix for multi-repo graphs (e.g. `"producer-api"`) |
| `[stores] graph` | `--graph-store` / `$GRAPH_STORE` | Graph store connection string |
| `[stores] vector` | `--vector-store` / `$VECTOR_STORE` | Vector store connection string |
| `[llm] provider` | — | `openai`, `ollama`, or `bedrock` (default: `bedrock`) |
| `[llm] model` | — | Model name for the chosen provider |
| `[llm] embed_model` | — | Embedding model name |
| `[llm] base_url` | — | Base URL override (Ollama only) |
| `[indexing] chunk_size` | — | Token size per chunk (default: 512) |
| `[indexing] chunk_overlap` | — | Overlap between chunks (default: 50) |
| `[indexing] extraction_dir` | — | Directory for LLM extraction checkpoint files |
| `[pipeline] full_rebuild` | `--full-rebuild` | Always do a full rebuild instead of incremental |
| `[pipeline] skip_reconcile_deletions` | `--skip-reconcile-deletions` | Skip deletion reconciliation on incremental updates |

---

## What Gets Indexed

Each OpenWiki page becomes a `__Source__` node. Pages with a `.claims/` sidecar have their verified claim statements pre-seeded as propositions, bypassing LLM extraction for those facts. Evidence URIs are written as a flat `evidence_uris` list onto the `__Source__` node after indexing.

**Pages that are skipped:**

- Auto-generated `index.md` files
- Files inside dotted directories (`.claims/`, `.run/`, etc.)
- Files that lack an OpenWiki `type:` frontmatter key

**Graph schema:**

```
:__Source__    sourceId, doc_id, url, title, wiki_type, tags[], evidence_uris[]
  └─__EXTRACTED_FROM__← :__Chunk__       chunkId, text
      └─__MENTIONED_IN__← :__Statement__ statementId, value
      └─__MENTIONED_IN__← :__Topic__     topicId, value
                                └─__SUPPORTS__← :__Fact__   factId
                                                 └─__SUBJECT__/:__OBJECT__← :__Entity__

:__Source__ ─RELATED_TO→ :__Source__   (from relatedPages frontmatter)
```

---

## Non-Bedrock Embeddings

The toolkit's build pipeline defaults to 2 parallel subprocess workers. Subprocess workers cannot receive non-picklable objects, so they fall back to Bedrock for embeddings when workers > 1.

When you configure `provider = "openai"` or `provider = "ollama"`, the CLI automatically sets `build_num_workers = 1`, which runs the build in-process and uses your configured embed model. For Bedrock users, the default of 2 workers is preserved.

If you need more throughput on a large wiki with a non-Bedrock provider, set `BUILD_NUM_WORKERS` to a higher value **only** after confirming that your embed model object is picklable in your environment.

---

## Known Issues

See [KNOWN_ISSUES.md](KNOWN_ISSUES.md).

---

## Additional Resources

- [Hierarchical Lexical Graph for Enhanced Multi-Hop Retrieval](https://arxiv.org/abs/2506.08074) [Article] — Describes the design of the hierarchical lexical graph model that underpins graphrag-lexical-graph.
