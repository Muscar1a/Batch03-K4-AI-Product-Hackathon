"""
Graph Store Module
Lưu trữ và truy vấn Đồ thị Tri thức (Knowledge Graph Database).
Hỗ trợ thuật toán truy vấn đa chặng (2-hop graph traversal).
"""

from typing import List, Dict, Any, Optional

class KnowledgeGraphStore:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path
        self.nodes = {}
        self.edges = []

    def add_triple(self, subject: str, relation: str, obj: str, attributes: Optional[Dict[str, Any]] = None):
        """Thêm một quan hệ Triple (Subject -> Relation -> Object) vào đồ thị."""
        edge = {
            "subject": subject,
            "relation": relation,
            "object": obj,
            "attributes": attributes or {}
        }
        self.edges.append(edge)

    def query_multi_hop(self, entity: str, hops: int = 2) -> List[Dict[str, Any]]:
        """Truy vấn đa chặng từ một thực thể gốc."""
        results = []
        visited = set()
        queue = [(entity, 0)]
        
        while queue:
            curr_entity, depth = queue.pop(0)
            if depth >= hops or curr_entity in visited:
                continue
            visited.add(curr_entity)
            
            for edge in self.edges:
                if edge["subject"] == curr_entity:
                    results.append(edge)
                    queue.append((edge["object"], depth + 1))
        return results
