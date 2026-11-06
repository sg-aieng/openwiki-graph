# Contributing to openwiki-graph

Thank you for taking the time to improve openwiki-graph. Contributions are
welcome, including bug fixes, documentation improvements, tests, new backends,
and improvements to the indexing and query pipelines.

## Before you start

- Read the [README](README.md) and [KNOWN_ISSUES.md](KNOWN_ISSUES.md).
- For substantial changes, open an issue first so the design and scope can be
  discussed before implementation.
- Never commit API keys, database credentials, local configuration files, or
  generated extraction checkpoints.

## Development setup

The project requires Python 3.10 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Provider and store integrations are optional. Install the extras needed for the
area you are working on, for example:

```bash
python -m pip install -e ".[openai,neo4j,pgvector]"
```

## Tests and checks

Run the test suite before submitting a change:

```bash
python -m pytest -q
```

Also make sure the command-line interface still starts:

```bash
openwiki-graph --help
```

Changes that affect packaging, configuration, loaders, graph writes, or CLI
behavior should include or update tests. Integration tests that require live
Neo4j, PostgreSQL, or LLM services should be clearly separated from the normal
unit-test suite and must not require credentials in CI.

## Making changes

1. Create a focused branch from the default branch.
2. Keep changes small and explain the user-visible behavior they affect.
3. Preserve backwards compatibility unless the change is explicitly a breaking
   change.
4. Update the README, configuration example, known issues, or changelog when
   behavior or setup requirements change.
5. Do not hand-edit generated OpenWiki pages when they can be regenerated from
   their source repository.
6. Review the final diff for credentials, local paths, generated files, and
   unrelated changes.

## Pull requests

A pull request should include:

- a concise description of the problem and solution;
- the tests and checks that were run;
- documentation updates when user-facing behavior changes; and
- any known limitations or follow-up work.

Please keep review discussions technical and constructive. Maintainers may ask
for additional tests, documentation, or a narrower scope before merging.

## Licensing

By submitting a contribution, you agree that it may be distributed under the
repository's [Apache License 2.0](LICENSE).
