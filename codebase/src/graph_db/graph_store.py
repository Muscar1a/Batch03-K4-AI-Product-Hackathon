"""Compatibility entrypoint for the production graph store."""

from src.graph_db.graph_store import GraphStore, GraphStoreCorruptionError, ImportResult

__all__ = ["GraphStore", "GraphStoreCorruptionError", "ImportResult"]
