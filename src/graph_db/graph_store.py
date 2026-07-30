"""NetworkX-backed knowledge graph with stable JSON persistence."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import tempfile
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Literal, Mapping

import networkx as nx


class GraphStoreCorruptionError(ValueError):
    """Raised when a persisted graph cannot be safely loaded."""


@dataclass
class ImportResult:
    inserted: int = 0
    duplicates: int = 0
    invalid: int = 0
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "inserted": self.inserted,
            "duplicates": self.duplicates,
            "invalid": self.invalid,
            "errors": list(self.errors),
        }


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    value = re.sub(r"[_-]+", " ", value)
    return re.sub(r"\s+", " ", value.strip()).casefold()


def normalize_relation(value: str) -> str:
    relation = re.sub(r"[^A-Za-z0-9]+", "_", value.strip().upper()).strip("_")
    if not relation:
        raise ValueError("relation must contain at least one alphanumeric character")
    return relation


def _edge_id(subject: str, relation: str, object_: str, source: str) -> str:
    raw = "\x1f".join((subject, relation, object_, source))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class GraphStore:
    """A directed multigraph whose records remain portable and inspectable."""

    SCHEMA_VERSION = "1.0"

    def __init__(self, path: str | Path, load_existing: bool = True) -> None:
        self.path = Path(path)
        self.graph = nx.MultiDiGraph()
        self.metadata: dict[str, object] = {}
        if load_existing and self.path.exists():
            self.load()

    @staticmethod
    def _canonicalize(triple: Mapping[str, object]) -> dict[str, object]:
        if not isinstance(triple, Mapping):
            raise ValueError("triple must be an object")
        subject = triple.get("subject")
        relation = triple.get("relation")
        object_ = triple.get("object")
        if not all(isinstance(value, str) and value.strip() for value in (subject, relation, object_)):
            raise ValueError("subject, relation, and object must be non-empty strings")
        source = triple.get("source", "unknown")
        attributes = triple.get("attributes", {})
        if not isinstance(attributes, Mapping):
            raise ValueError("attributes must be an object")
        if source == "unknown":
            source = attributes.get("proof_document") or attributes.get("discord_url") or attributes.get("file_name") or "unknown"
        if not isinstance(source, str):
            raise ValueError("source must be a string")
        confidence = triple.get("confidence", 1.0)
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            raise ValueError("confidence must be a number between 0 and 1")
        if not math.isfinite(float(confidence)) or not 0 <= float(confidence) <= 1:
            raise ValueError("confidence must be a number between 0 and 1")
        subject_id = normalize_text(subject)
        object_id = normalize_text(object_)
        relation_name = normalize_relation(relation)
        source_name = source.strip() or "unknown"
        return {
            "subject": subject_id,
            "subject_label": subject.strip(),
            "relation": relation_name,
            "object": object_id,
            "object_label": object_.strip(),
            "source": source_name,
            "confidence": float(confidence),
            "attributes": dict(attributes),
        }

    def load(self) -> None:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(payload, Mapping):
                raise ValueError("graph store root must be an object")
            if payload.get("schema_version") != self.SCHEMA_VERSION:
                raise ValueError("unsupported schema version")
            self.metadata = dict(payload.get("metadata", {}))
            nodes = payload["nodes"]
            edges = payload["edges"]
            if not isinstance(nodes, list) or not isinstance(edges, list):
                raise ValueError("nodes and edges must be arrays")
            graph = nx.MultiDiGraph()
            for node in nodes:
                if not isinstance(node, Mapping) or not isinstance(node.get("id"), str):
                    raise ValueError("invalid node record")
                graph.add_node(
                    node["id"],
                    label=node.get("label", node["id"]),
                    category=node.get("category"),
                    attributes=dict(node.get("attributes", {})),
                )
            for edge in edges:
                if not isinstance(edge, Mapping):
                    raise ValueError("invalid edge record")
                canonical = self._canonicalize(edge)
                if canonical["subject"] not in graph or canonical["object"] not in graph:
                    raise ValueError("edge references a missing node")
                key = edge.get("id") or _edge_id(
                    canonical["subject"], canonical["relation"], canonical["object"], canonical["source"]
                )
                graph.add_edge(
                    canonical["subject"],
                    canonical["object"],
                    key=key,
                    relation=canonical["relation"],
                    source=canonical["source"],
                    confidence=canonical["confidence"],
                    attributes=canonical["attributes"],
                )
            self.graph = graph
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise GraphStoreCorruptionError(f"cannot load graph store {self.path}: {exc}") from exc

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        nodes = [
            {
                "id": node,
                "label": data.get("label", node),
                "category": data.get("category"),
                "attributes": data.get("attributes", {}),
            }
            for node, data in sorted(self.graph.nodes(data=True))
        ]
        edges = []
        for subject, object_, key, data in sorted(
            self.graph.edges(keys=True, data=True), key=lambda item: (item[0], item[1], item[2])
        ):
            edges.append(
                {
                    "id": key,
                    "subject": subject,
                    "relation": data["relation"],
                    "object": object_,
                    "source": data.get("source", "unknown"),
                    "confidence": data.get("confidence", 1.0),
                    "attributes": data.get("attributes", {}),
                }
            )
        payload = {
            "schema_version": self.SCHEMA_VERSION,
            "metadata": self.metadata,
            "nodes": nodes,
            "edges": edges,
        }
        fd, temporary = tempfile.mkstemp(prefix=f".{self.path.name}.", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def add_triple(self, triple: Mapping[str, object]) -> bool:
        canonical = self._canonicalize(triple)
        subject = canonical["subject"]
        object_ = canonical["object"]
        self.graph.add_node(subject, label=canonical["subject_label"], attributes={})
        self.graph.add_node(object_, label=canonical["object_label"], attributes={})
        key = _edge_id(subject, canonical["relation"], object_, canonical["source"])
        if self.graph.has_edge(subject, object_, key):
            return False
        self.graph.add_edge(
            subject,
            object_,
            key=key,
            relation=canonical["relation"],
            source=canonical["source"],
            confidence=canonical["confidence"],
            attributes=canonical["attributes"],
        )
        return True

    def add_entities(self, entities: Iterable[Mapping[str, object]]) -> int:
        """Add entity labels/categories without requiring an edge for each entity."""
        inserted = 0
        for entity in entities:
            if not isinstance(entity, Mapping):
                continue
            name = entity.get("name")
            if not isinstance(name, str) or not name.strip():
                continue
            node_id = normalize_text(name)
            existing = self.graph.nodes.get(node_id, {})
            attributes = entity.get("attributes", existing.get("attributes", {}))
            if not isinstance(attributes, Mapping):
                continue
            self.graph.add_node(
                node_id,
                label=existing.get("label", name.strip()),
                category=entity.get("category", existing.get("category")),
                attributes=dict(attributes),
            )
            inserted += 1
        return inserted

    def add_triples(self, triples: Iterable[Mapping[str, object]]) -> ImportResult:
        result = ImportResult()
        for index, triple in enumerate(triples):
            try:
                if self.add_triple(triple):
                    result.inserted += 1
                else:
                    result.duplicates += 1
            except (TypeError, ValueError) as exc:
                result.invalid += 1
                if len(result.errors) < 20:
                    result.errors.append(f"item {index}: {exc}")
        return result

    def import_file(self, path: str | Path) -> ImportResult:
        source_path = Path(path)
        try:
            payload = json.loads(source_path.read_text(encoding="utf-8"))
            triples = payload.get("triples") if isinstance(payload, Mapping) else payload
            if not isinstance(triples, list):
                raise ValueError("expected a triple list or an object containing 'triples'")
            if isinstance(payload, Mapping):
                self.metadata = dict(payload.get("metadata", {}))
                self.add_entities(payload.get("entities", []))
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
            return ImportResult(invalid=1, errors=[str(exc)])
        return self.add_triples(triples)

    def find_entities(self, text: str, limit: int = 10) -> list[dict[str, str]]:
        query = normalize_text(text)
        if not query or limit <= 0:
            return []
        matches = []
        for node, data in self.graph.nodes(data=True):
            label = data.get("label", node)
            exact = node == query
            if exact or query in node:
                matches.append({"id": node, "label": label, "exact": exact})
        return sorted(matches, key=lambda item: (not item["exact"], normalize_text(item["label"])))[:limit]

    def traverse(
        self,
        entity: str,
        max_hops: int = 2,
        direction: Literal["out", "in", "both"] = "out",
    ) -> list[dict[str, object]]:
        if max_hops not in (1, 2):
            raise ValueError("max_hops must be 1 or 2")
        if direction not in ("out", "in", "both"):
            raise ValueError("direction must be 'out', 'in', or 'both'")
        entity_id = normalize_text(entity)
        if entity_id not in self.graph:
            return []
        queue: list[tuple[str, list[str], list[dict[str, object]], set[str]]] = [(entity_id, [entity_id], [], set())]
        results: list[dict[str, object]] = []
        while queue:
            current, path_nodes, path_edges, used_edges = queue.pop(0)
            if len(path_edges) >= max_hops:
                continue
            candidates: list[tuple[str, str, str, str, Mapping[str, object]]] = []
            if direction in ("out", "both"):
                candidates.extend(
                    (target, current, target, key, data)
                    for _, target, key, data in self.graph.out_edges(current, keys=True, data=True)
                )
            if direction in ("in", "both"):
                candidates.extend(
                    (source, source, current, key, data)
                    for source, _, key, data in self.graph.in_edges(current, keys=True, data=True)
                )
            for next_node, source, target, key, data in candidates:
                if key in used_edges:
                    continue
                edge = {
                    "subject": source,
                    "relation": data["relation"],
                    "object": target,
                    "source": data.get("source", "unknown"),
                    "confidence": data.get("confidence", 1.0),
                    "attributes": data.get("attributes", {}),
                }
                next_nodes = path_nodes + [next_node]
                next_edges = path_edges + [edge]
                results.append({"entities": next_nodes, "edges": next_edges, "hops": len(next_edges)})
                queue.append((next_node, next_nodes, next_edges, used_edges | {key}))
        return sorted(
            results,
            key=lambda item: (
                item["hops"],
                -min(edge["confidence"] for edge in item["edges"]),
                tuple(item["entities"]),
                tuple(edge["relation"] for edge in item["edges"]),
            ),
        )

    def get_context(self, entity: str, max_hops: int = 2, limit: int = 20) -> list[dict[str, object]]:
        return self.traverse(entity, max_hops=max_hops)[: max(0, limit)]
