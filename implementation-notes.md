# Implementation Notes — Member 2

## Decisions

- Knowledge graph backend: NetworkX `MultiDiGraph` with explicit JSON persistence.
- Edge identity includes normalized subject, relation, object, and source so duplicate imports are idempotent while source provenance is preserved.
- Entity matching normalizes Unicode, whitespace, and case while retaining the first display label.
- Dynamic memory is user-scoped and persisted in `data/memory_store.json`.
- Prototype fact extraction is deterministic and injectable; it detects OS, group, and issue facts without requiring an LLM.
- Runtime data files are ignored by the repository's existing `/data/*` rule.

## Member 1 Handoff

Expected input: `data/extracted_triples.json`, containing `metadata`, `entities`, and `{ "triples": [...] }`. The importer preserves entity categories and citation attributes, and reports inserted, duplicate, invalid, and representative error counts.

Local handoff observed: 148 triples, 98 entities, 0 malformed records, 132 Level-2 Discord citations, 15 grounding citations, and 1 community citation. The old importer reduced this to 87 edges because it discarded nested citation attributes; the adapted importer now preserves all 148 source-distinct edges.

## Verification

Run the targeted graph and memory tests with:

```bash
python -m unittest discover -s tests/graph_db -p 'test_*.py'
```

Current verification: 14 tests pass under `uv run --with networkx`; source compilation, `git diff --check`, and graphify refresh also pass. Real-data build produces 98 nodes, 148 edges, 0 invalid records, 0 unknown sources, and 2-hop queries for CP1/AI Log succeed. `uvx ruff` could not run because the sandbox could not resolve PyPI; no lint result is claimed.

User-test results and final Member 1 import statistics must be added here after those activities occur; they are not fabricated in this file.
