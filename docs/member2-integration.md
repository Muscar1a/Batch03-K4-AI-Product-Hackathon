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
result = graph.import_file("data/processed/triples.json")
graph.save()
print(result.to_dict())
```

The importer accepts a top-level list or an object containing `triples`. Runtime
stores are generated under `data/` and must not be committed with raw data.
