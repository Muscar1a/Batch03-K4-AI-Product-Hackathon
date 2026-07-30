"""Compatibility entrypoint for the graph store."""

from codebase.src.graph_db.graph_store import GraphStore, GraphStoreCorruptionError, ImportResult

__all__ = ["GraphStore", "GraphStoreCorruptionError", "ImportResult"]


