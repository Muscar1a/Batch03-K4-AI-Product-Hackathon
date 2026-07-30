import json
import tempfile
import unittest
from pathlib import Path

from src.graph_db import (
    GraphStore,
    GraphStoreCorruptionError,
    MemoryStore,
    MemoryStoreCorruptionError,
)


class GraphStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self.temp_dir.name) / "graph.json"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_import_deduplicates_and_preserves_sources(self):
        store = GraphStore(self.path)
        triples = [
            {"subject": "AI Log", "relation": "has solution", "object": "Windows Guide", "source": "a.md"},
            {"subject": " ai   log ", "relation": "HAS_SOLUTION", "object": "Windows Guide", "source": "a.md"},
            {"subject": "AI Log", "relation": "HAS_SOLUTION", "object": "Windows Guide", "source": "b.md"},
        ]
        result = store.add_triples(triples)

        self.assertEqual(result.inserted, 2)
        self.assertEqual(result.duplicates, 1)
        self.assertEqual(store.graph.number_of_edges(), 2)

    def test_two_hop_query_survives_json_round_trip(self):
        store = GraphStore(self.path)
        store.add_triples(
            [
                {"subject": "AI Log", "relation": "HAS_SOLUTION", "object": "Windows Guide", "source": "a.md"},
                {"subject": "Windows Guide", "relation": "REFERENCES", "object": "overview.txt", "source": "b.md"},
            ]
        )
        store.save()

        loaded = GraphStore(self.path)
        paths = loaded.get_context("ai log", max_hops=2)

        self.assertEqual([path["hops"] for path in paths], [1, 2])
        self.assertEqual(paths[1]["entities"][-1], "overview.txt")
        self.assertEqual(paths[1]["edges"][0]["source"], "a.md")

    def test_import_file_and_incoming_traversal(self):
        input_path = Path(self.temp_dir.name) / "triples.json"
        input_path.write_text(
            json.dumps({"triples": [{"subject": "Topic", "relation": "HAS_SOLUTION", "object": "Guide"}]}),
            encoding="utf-8",
        )
        store = GraphStore(self.path)
        result = store.import_file(input_path)

        self.assertEqual(result.inserted, 1)
        paths = store.traverse("Guide", direction="in")
        self.assertEqual(paths[0]["entities"], ["guide", "topic"])

    def test_member1_payload_preserves_entities_metadata_and_citations(self):
        input_path = Path(self.temp_dir.name) / "extracted_triples.json"
        input_path.write_text(
            json.dumps(
                {
                    "metadata": {"extracted_triples_count": 1},
                    "entities": [{"name": "AI_Log", "category": "TECH_ISSUE", "attributes": {"kind": "bug"}}],
                    "triples": [
                        {
                            "subject": "AI_Log",
                            "relation": "REQUIRES_HOOK",
                            "object": "git pre-push hook",
                            "attributes": {
                                "citation_level": "Grounding",
                                "proof_document": "README.md",
                                "proof_snippet": "Install the hook.",
                            },
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        store = GraphStore(self.path)
        result = store.import_file(input_path)
        store.save()
        loaded = GraphStore(self.path)

        self.assertEqual(result.inserted, 1)
        self.assertEqual(loaded.metadata["extracted_triples_count"], 1)
        self.assertEqual(loaded.graph.nodes["ai log"]["category"], "TECH_ISSUE")
        context = loaded.get_context("AI Log")
        self.assertEqual(context[0]["edges"][0]["source"], "README.md")
        self.assertEqual(context[0]["edges"][0]["attributes"]["citation_level"], "Grounding")

    def test_cycles_terminate_and_unknown_entities_are_empty(self):
        store = GraphStore(self.path)
        store.add_triples(
            [
                {"subject": "A", "relation": "NEXT", "object": "B"},
                {"subject": "B", "relation": "NEXT", "object": "A"},
            ]
        )

        self.assertTrue(store.traverse("missing") == [])
        self.assertLessEqual(len(store.traverse("A", max_hops=2)), 2)

    def test_invalid_triples_are_reported(self):
        store = GraphStore(self.path)
        result = store.add_triples([{"subject": "A"}, {"subject": "A", "relation": "R", "object": "B", "confidence": 2}])

        self.assertEqual(result.invalid, 2)
        self.assertEqual(len(result.errors), 2)

    def test_corrupt_graph_is_not_silently_replaced(self):
        self.path.write_text("not json", encoding="utf-8")
        with self.assertRaises(GraphStoreCorruptionError):
            GraphStore(self.path)

    def test_non_object_graph_is_corrupt(self):
        self.path.write_text("[]", encoding="utf-8")
        with self.assertRaises(GraphStoreCorruptionError):
            GraphStore(self.path)


class MemoryStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self.temp_dir.name) / "memory.json"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_extracts_os_group_and_issue(self):
        store = MemoryStore(self.path)

        facts = store.remember_from_text("u1", "Mình ở nhóm G14, dùng Windows và đang bị lỗi AI Log")

        self.assertEqual({fact["fact_type"] for fact in facts}, {"OS", "GROUP", "STUCK_ISSUE"})
        self.assertEqual(store.get_facts("u1", "GROUP")[0]["value"], "G14")
        self.assertEqual(store.get_facts("u1", "OS")[0]["value"], "Windows")

    def test_memory_is_deduplicated_and_survives_reload(self):
        store = MemoryStore(self.path)
        store.remember_from_text("u1", "Mình dùng Windows")
        store.remember_from_text("u1", "Mình dùng Windows")
        store.remember_from_text("u2", "Mình dùng macOS")

        loaded = MemoryStore(self.path)
        self.assertEqual(len(loaded.get_facts("u1")), 1)
        self.assertEqual(loaded.get_facts("u1")[0]["value"], "Windows")
        self.assertEqual(loaded.get_facts("u2")[0]["value"], "macOS")

    def test_empty_questions_do_not_become_issues(self):
        store = MemoryStore(self.path)

        self.assertEqual(store.extract_facts("Xin chào, deadline CP4 khi nào?"), [])

    def test_remove_and_clear_are_user_scoped(self):
        store = MemoryStore(self.path)
        store.remember_from_text("u1", "Mình ở nhóm G14")
        store.remember_from_text("u2", "Mình ở nhóm G15")

        self.assertTrue(store.remove_fact("u1", "GROUP", "G14"))
        self.assertEqual(store.get_facts("u1"), [])
        self.assertEqual(store.get_facts("u2")[0]["value"], "G15")
        self.assertTrue(store.clear_user("u2"))
        self.assertEqual(store.get_facts("u2"), [])

    def test_corrupt_memory_is_not_silently_replaced(self):
        self.path.write_text(json.dumps({"schema_version": "bad"}), encoding="utf-8")
        with self.assertRaises(MemoryStoreCorruptionError):
            MemoryStore(self.path)

    def test_invalid_memory_confidence_is_rejected(self):
        store = MemoryStore(self.path)
        with self.assertRaises(ValueError):
            store.add_fact("u1", {"fact_type": "OS", "value": "Windows", "confidence": 2})


if __name__ == "__main__":
    unittest.main()
