"""Compatibility entrypoint for the memory store."""

from codebase.src.graph_db.memory_store import MemoryStore, MemoryStoreCorruptionError

__all__ = ["MemoryStore", "MemoryStoreCorruptionError"]

