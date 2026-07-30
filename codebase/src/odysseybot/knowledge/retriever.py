"""FTS5 SQLite, GraphStore (Knowledge Graph DB), and official course docs retriever."""

import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import aiosqlite

from odysseybot.config import settings
from odysseybot.domain.models import Citation
from graph_db.graph_store import GraphStore


class KnowledgeRetriever:
    """Queries SQLite source messages, Knowledge Graph DB (graph_store.json), and official docs."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or settings.DATABASE_PATH
        self.official_docs: List[Tuple[str, str]] = []
        self._load_official_docs()

        # Initialize Knowledge Graph DB (GraphStore)
        graph_json_path = Path("data/graph_store.json")
        self.graph_store = GraphStore(graph_json_path) if graph_json_path.exists() else None

    def _load_official_docs(self):
        root_dir = Path(".")
        doc_files = ["01-de-bai.md", "02-guide.md", "03-template-ai-spec.md", "04-rubric.md", "spec.md"]
        for df in doc_files:
            fpath = root_dir / df
            if fpath.exists():
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        self.official_docs.append((df, f.read()))
                except Exception:
                    pass

    async def search_staff_claims(self, query: str, limit: int = 5) -> List[Citation]:
        citations: List[Citation] = []
        clean_query = query.lower().strip()
        
        stopwords = {"hướng", "dẫn", "tôi", "cho", "em", "hỏi", "với", "setup", "cài", "đặt", "là", "gì", "khi", "nào", "ở", "trên"}
        words = [w for w in re.sub(r"[^\w\s]", " ", clean_query).split() if len(w) >= 2 and w not in stopwords]

        seen_ids = set()

        if self.db_path.exists() and clean_query:
            async with aiosqlite.connect(self.db_path) as db:
                # Priority 1: Match sub-keywords in content or channel_name, prioritizing longer/richer content
                search_terms = [" ".join(words)] + sorted(words, key=len, reverse=True)
                for term in search_terms:
                    if not term or len(term) < 2:
                        continue
                    pattern = f"%{term}%"
                    async with db.execute(
                        """
                        SELECT sm.id, sm.guild_id, sm.channel_id, sm.content, sm.author_name, sm.channel_name, sm.timestamp
                        FROM source_messages sm
                        WHERE (sm.content LIKE ? OR sm.channel_name LIKE ?) AND LENGTH(sm.content) > 30
                        ORDER BY LENGTH(sm.content) DESC, sm.timestamp DESC
                        LIMIT ?;
                        """,
                        (pattern, pattern, limit - len(citations))
                    ) as cursor:
                        async for row in cursor:
                            msg_id, guild_id, channel_id, content, author_name, channel_name, timestamp = row
                            if msg_id not in seen_ids:
                                seen_ids.add(msg_id)
                                ts_dt = datetime.fromisoformat(timestamp) if timestamp else None
                                target_guild = guild_id or settings.DCE_SOURCE_GUILD_ID or "1526532830627102781"
                                cname = channel_name.strip() if channel_name else "kênh"
                                if not cname.startswith("#"):
                                    cname = f"#{cname}"
                                citations.append(
                                    Citation(
                                        source_type="STAFF_DISCORD",
                                        title=cname,
                                        url=f"<#{channel_id}>",
                                        excerpt=content[:600],
                                        authority=f"bởi {author_name} (https://discord.com/channels/{target_guild}/{channel_id}/{msg_id})",
                                        source_timestamp=ts_dt,
                                    )
                                )

                    if len(citations) >= limit:
                        break

        return citations
