# Implementation Notes — Member 2

## Decisions

- Knowledge graph backend: NetworkX `MultiDiGraph` with explicit JSON persistence.
- Edge identity includes normalized subject, relation, object, and source so duplicate imports are idempotent while source provenance is preserved.
- Entity matching normalizes Unicode, whitespace, and case while retaining the first display label.
- Dynamic memory is user-scoped and persisted in `data/memory_store.json`.
- Prototype fact extraction is deterministic and injectable; it detects OS, group, and issue facts without requiring an LLM.
- Runtime data files are ignored by the repository's existing `/data/*` rule.

## Member 1 Handoff

Expected input: `data/processed/triples.json`, either as a top-level triple list or as `{ "triples": [...] }`. The importer reports inserted, duplicate, invalid, and representative error counts.

## Verification

Run the targeted graph and memory tests with:

```bash
python -m unittest discover -s tests/graph_db -p 'test_*.py'
```

Current verification: 13 tests pass under `uv run --with networkx`; source compilation, `git diff --check`, and graphify refresh also pass. `uvx ruff` could not run because the sandbox could not resolve PyPI; no lint result is claimed.

User-test results and final Member 1 import statistics must be added here after those activities occur; they are not fabricated in this file.
