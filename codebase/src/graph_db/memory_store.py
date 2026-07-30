"""
Memory Store Module
Quản lý bộ nhớ hội thoại dài hạn (Dynamic Long-Term Memory Engine)
Lưu các Facts về người dùng (OS, Nhóm, Lỗi gặp phải...).
"""

import json
import os
from typing import List, Dict, Any, Optional

class MemoryStore:
    def __init__(self, storage_path: str = "data/memory_store.json"):
        self.storage_path = storage_path
        self.user_memories: Dict[str, List[Dict[str, Any]]] = self._load()

    def _load(self) -> Dict[str, List[Dict[str, Any]]]:
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save(self):
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(self.user_memories, f, ensure_ascii=False, indent=2)

    def add_user_fact(self, user_id: str, fact_type: str, value: str, timestamp: Optional[str] = None):
        """Thêm một Fact quan trọng về người dùng vào bộ nhớ dài hạn."""
        if user_id not in self.user_memories:
            self.user_memories[user_id] = []
            
        fact = {
            "fact_type": fact_type,
            "value": value,
            "timestamp": timestamp or ""
        }
        # Tránh trùng lặp fact
        if fact not in self.user_memories[user_id]:
            self.user_memories[user_id].append(fact)
            self.save()

    def get_user_facts(self, user_id: str) -> List[Dict[str, Any]]:
        """Lấy tất cả các Facts đã lưu của người dùng."""
        return self.user_memories.get(user_id, [])
