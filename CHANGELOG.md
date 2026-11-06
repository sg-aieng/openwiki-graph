# Changelog

All notable changes to this project are documented here.

This project follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Project contribution, security, and community guidelines.

## [0.1.0] - 2026-11-06

Initial release of openwiki-graph.

### Added

- CLI commands for indexing, querying, and listing query skills.
- OpenWiki Markdown and claims loading.
- Claims-aware graph indexing with incremental updates.
- Explicit `RELATED_TO` edges from page relationships.
- Evidence URI enrichment on source nodes.
- Deleted-page reconciliation for incremental indexing.
- Multi-repository graph namespaces through `wiki_id`.
- OpenAI, Ollama, and Amazon Bedrock provider configuration.
- Neo4j, PostgreSQL/pgvector, and other graphrag-toolkit store support.
- Multi-repository example applications and pre-generated OpenWiki content.

### Known limitations

- Tenant-aware indexing is incomplete; see [KNOWN_ISSUES.md](KNOWN_ISSUES.md).
- End-to-end graph integration tests are not yet included in the default test
  suite.
- Cross-repository `RELATED_TO` edges depend on relationship metadata that
  OpenWiki may not currently emit.

[Unreleased]: https://github.com/your-org/openwiki-graph/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/your-org/openwiki-graph/releases/tag/v0.1.0
