"""Compatibility entrypoint for the production memory store."""

from src.graph_db.memory_store import MemoryStore, MemoryStoreCorruptionError

__all__ = ["MemoryStore", "MemoryStoreCorruptionError"]
