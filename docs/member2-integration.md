# Member 2 Integration Contract

Member 3 can use the storage modules without depending on their file formats:

```python
from src.graph_db import GraphStore, MemoryStore

graph = GraphStore("data/graph_store.json")
memory = MemoryStore("data/memory_store.json")

facts = memory.remember_from_text(user_id, latest_message)
profile = memory.get_facts(user_id)
context = graph.get_context("AI Log", max_hops=2, limit=20)
```

`context` contains ordered `entities`, `edges`, and `hops`. Each edge includes
`subject`, `relation`, `object`, `source`, and `confidence`, so the synthesizer
can cite the originating document. Empty or unknown queries return empty lists.

Member 1 input is imported separately:

```python
result = graph.import_file("data/extracted_triples.json")
graph.save()
print(result.to_dict())
```

The Member 1 payload contains `metadata`, `entities`, and `triples`. Triple
citations are preserved from `attributes.proof_document`, `discord_url`,
`file_name`, and `proof_snippet`. Runtime stores are generated under `data/`
and must not be committed with raw data.

To build the runtime graph directly:

```bash
python codebase/src/graph_db/build_graph.py
```
