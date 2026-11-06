# Examples

This directory contains two minimal Spring Boot services designed to demonstrate
openwiki-graph's **multi-repo graph** capability: the ability to index two independent
repositories into one shared knowledge graph and then ask natural-language questions
that span both.

---

## What we're trying to show

Real codebases rarely live in isolation. A consumer service calls a producer service,
and the connection between them — which endpoints are used, what the contract looks
like, what the client wraps them in — is scattered across two separate repositories.

By indexing both repositories with openwiki-graph and assigning each one a `wiki_id`
namespace, you end up with a single graph where the two repos are connected via shared
topic nodes. A question like _"who consumes the user API?"_ can then be answered with
a citation pointing to the right repository and the right source file.

---

## The two services

### `producer-api`

A Spring Boot 3.2 REST API that exposes a full CRUD surface for user management at
`/api/users` on port `8080`. All state is held in-memory — no database required.
Three seed users (`admin`, `john_doe`, `jane_smith`) are created on every startup.

Key files:
- `src/main/java/com/example/userapi/controller/UserController.java` — 8 REST endpoints
- `src/main/java/com/example/userapi/service/UserService.java` — in-memory store + business logic
- `openwiki/` — pre-generated OpenWiki documentation for the service

### `consumer-api`

A Spring Boot 3.2 command-line application that connects to the producer and runs a
demo workflow on startup: it lists users, reads one by username, creates a new user,
updates it, deactivates it, activates it, then deletes it. It does not own any
user persistence and relies entirely on the producer for all user data.

Key files:
- `src/main/java/com/example/consumer/client/UserApiClient.java` — `RestTemplate`-based HTTP client
- `src/main/java/com/example/consumer/runner/DemoRunner.java` — startup demo workflow
- `openwiki/` — pre-generated OpenWiki documentation for the service

---

## Prerequisites

- **openwiki-graph** installed with store dependencies:
  ```bash
  pip install -e "path/to/openwiki-graph[openai,neo4j,pgvector]"
  ```
- A running **Neo4j** instance (graph store) and **PostgreSQL + pgvector** instance
  (vector store) — see the [openwiki-graph store setup guide](../README.md#store-setup)
- An **OpenAI API key** (or another supported provider) exported as `OPENAI_API_KEY`
- An `openwiki-graph.toml` config file pointing at your stores:
  ```toml
  [stores]
  graph  = "bolt://neo4j:yourpassword@localhost:7687"
  vector = "postgresql://postgres:yourpassword@localhost:5432/openwiki"

  [llm]
  provider    = "openai"
  model       = "gpt-4o-mini"
  embed_model = "text-embedding-3-small"
  ```

---

## Step 1 — Index both repos

The `openwiki/` folders in each service are pre-generated and ready to index.
Run the following from the openwiki-graph root (or anywhere your config file is):

```bash
# Index the producer — wiki_id scopes its doc_ids as "producer-api::..."
openwiki-graph pipeline \
  --wiki-root examples/producer-api/openwiki \
  --wiki-id producer-api

# Index the consumer — wiki_id scopes its doc_ids as "consumer-api::..."
openwiki-graph pipeline \
  --wiki-root examples/consumer-api/openwiki \
  --wiki-id consumer-api
```

Both repositories now share the same Neo4j + pgvector instance. Their documents are
namespaced by `wiki_id` to avoid collisions, and they are connected at the graph level
via shared `__Topic__` nodes (topics like "User API" and "REST" appear in both).

---

## Step 2 — Query the graph

```bash
openwiki-graph query "who consumes the user API?"
```

Expected answer (abbreviated):

> The User API is consumed by the `UserApiClient` in the `consumer-api` repository.
> This client issues HTTP requests to the producer using Spring Boot's `RestTemplate`.
> [source: consumer-api::integrations/user-api-contract.md]
> [source: consumer-api::architecture/application-overview.md]

More queries to try:

```bash
# Cross-repo endpoint coverage
openwiki-graph query "which endpoints does the consumer call on the producer?"

# Architecture question spanning both sides
openwiki-graph query "what happens when the producer is not reachable?"

# Single-repo question (producer side)
openwiki-graph query "what seed users does the producer create on startup?"

# Single-repo question (consumer side)
openwiki-graph query "what demo steps does the consumer run on startup?"

# Data model comparison
openwiki-graph query "how does the consumer's User model differ from the producer's?"
```

---

## What the graph looks like

After both indexes complete, the graph contains:

| Repository | Source nodes | Connected via |
|------------|-------------|---------------|
| `producer-api` | `api/endpoints`, `architecture/overview`, `data/user-model`, `quickstart` | Shared `__Topic__` nodes |
| `consumer-api` | `integrations/user-api-contract`, `architecture/application-overview`, `concepts/user-domain`, `operations/configuration-and-runtime`, `workflows/demo-execution`, `quickstart` | Shared `__Topic__` nodes |

Topics like **User API**, **RestTemplate**, **Spring Boot**, and **user management**
appear in both repositories and form the bridge that lets cross-repo queries work.

