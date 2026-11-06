# Security Policy

## Supported versions

Security fixes are prioritized for the latest released version and the current
default branch. Users should upgrade to the latest available release before
reporting an issue against an older version.

## Reporting a vulnerability

Please do not report security vulnerabilities in a public GitHub issue, pull
request, or discussion.

Use GitHub's private vulnerability reporting or security advisory feature for
this repository when it is available. If private reporting is not enabled,
contact the repository maintainers through the GitHub account or organization
that owns the repository and request a private channel.

Include as much of the following as possible:

- the affected version or commit;
- a concise description of the vulnerability and its impact;
- reproducible steps or a minimal proof of concept;
- affected configuration, provider, store, or CLI paths; and
- any suggested mitigation.

Please redact API keys, database passwords, access tokens, personal data, and
private source code from the report.

## Configuration and credential safety

Never commit `openwiki-graph.toml`, provider credentials, store passwords, or
local `.env` files. Use `openwiki-graph.toml.example` as the starting point and
provide credentials through the environment or the provider's normal credential
chain.

The project can connect to LLM, graph-store, and vector-store services. Treat
connection strings, logs, extraction checkpoints, and generated graph data as
potentially sensitive because they may contain source content or infrastructure
details.

The tenant-aware indexing limitation documented in [KNOWN_ISSUES.md](KNOWN_ISSUES.md)
is not a safe basis for multi-tenant isolation until it has been fixed and
verified with integration tests.

## Scope

Reports may cover the openwiki-graph source code, packaging, CLI, configuration
handling, dependency use, documentation examples, and supported integrations.
Issues caused solely by OpenWiki, graphrag-toolkit, LlamaIndex, a database, or
an LLM provider should also be reported to the relevant upstream project when
appropriate, with sensitive details removed.
