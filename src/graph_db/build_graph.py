"""Build the runtime graph from Member 1's extracted triple payload."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.graph_db import GraphStore


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", type=Path, default=Path("data/extracted_triples.json"))
    parser.add_argument("output", nargs="?", type=Path, default=Path("data/kg_database.json"))
    args = parser.parse_args()

    store = GraphStore(args.output)
    result = store.import_file(args.input)
    if result.invalid or not result.inserted:
        print(result.to_dict())
        return 1
    store.save()
    print(
        {
            **result.to_dict(),
            "nodes": store.graph.number_of_nodes(),
            "edges": store.graph.number_of_edges(),
            "metadata": store.metadata,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
