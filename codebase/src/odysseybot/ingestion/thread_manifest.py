"""Thread manifest storage and fallback probe manager."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ThreadEntry(BaseModel):
    thread_id: str
    parent_forum_id: str
    name: Optional[str] = None
    first_seen: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_exported: Optional[str] = None
    is_active: bool = True
    discovery_method: str = "manifest"


class ThreadManifest:
    """Manages thread manifests at data/runtime/manifests/program_threads.json."""

    def __init__(self, manifest_path: Optional[Path] = None):
        self.manifest_path = manifest_path or Path("data/runtime/manifests/program_threads.json")
        self.threads: Dict[str, ThreadEntry] = {}
        self.load()

    def load(self) -> None:
        if self.manifest_path.exists():
            try:
                with open(self.manifest_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data.get("threads", []):
                        entry = ThreadEntry(**item)
                        self.threads[entry.thread_id] = entry
            except Exception:
                pass

    def save(self) -> None:
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "threads": [entry.model_dump() for entry in self.threads.values()],
        }
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def add_thread(self, thread_id: str, parent_forum_id: str, name: Optional[str] = None, method: str = "manual") -> ThreadEntry:
        if thread_id in self.threads:
            entry = self.threads[thread_id]
            if name:
                entry.name = name
            entry.is_active = True
        else:
            entry = ThreadEntry(
                thread_id=thread_id,
                parent_forum_id=parent_forum_id,
                name=name,
                discovery_method=method,
            )
            self.threads[thread_id] = entry
        self.save()
        return entry

    def get_all_thread_ids(self) -> List[str]:
        return list(self.threads.keys())

