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
    """Queries FTS5 virtual tables, Knowledge Graph DB (graph_store.json), and official docs."""

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

        # 1. Search SQLite FTS5 Virtual Table (fts_source_messages)
        if self.db_path.exists() and clean_query:
            fts_term = " OR ".join(words) if words else clean_query
            async with aiosqlite.connect(self.db_path) as db:
                try:
                    async with db.execute(
                        """
                        SELECT sm.id, sm.guild_id, sm.channel_id, sm.content, sm.author_name, sm.channel_name, sm.timestamp, sm.is_staff
                        FROM fts_source_messages fts
                        JOIN source_messages sm ON fts.id = sm.id
                        WHERE fts_source_messages MATCH ? AND LENGTH(sm.content) > 30
                        ORDER BY bm25(fts_source_messages) ASC, sm.timestamp DESC
                        LIMIT ?;
                        """,
                        (fts_term, limit)
                    ) as cursor:
                        async for row in cursor:
                            msg_id, guild_id, channel_id, content, author_name, channel_name, timestamp, is_staff = row
                            if msg_id not in seen_ids:
                                seen_ids.add(msg_id)
                                ts_dt = datetime.fromisoformat(timestamp) if timestamp else None
                                target_guild = guild_id or settings.DCE_SOURCE_GUILD_ID or "1526532830627102781"
                                cname = channel_name.strip() if channel_name else "kênh"
                                if not cname.startswith("#"):
                                    cname = f"#{cname}"
                                citations.append(
                                    Citation(
                                        source_type="STAFF_DISCORD" if is_staff else "LEARNER_DISCORD",
                                        title=cname,
                                        url=f"<#{channel_id}>",
                                        excerpt=content[:600],
                                        authority=f"bởi {author_name} - https://discord.com/channels/{target_guild}/{channel_id}/{msg_id}",

                                        source_timestamp=ts_dt,
                                    )
                                )
                except Exception:
                    pass

        # 2. Search Knowledge Graph DB (GraphStore NetworkX projection)
        if len(citations) < limit and self.graph_store and clean_query:
            try:
                paths = self.graph_store.get_context(clean_query, max_hops=2, limit=3)
                for p in paths:
                    edges_desc = []
                    for e in p.get("edges", []):
                        edges_desc.append(f"({e.get('subject')}) -[{e.get('relation')}]-> ({e.get('object')})")
                    if edges_desc:
                        snippet = " ; ".join(edges_desc)
                        citations.append(
                            Citation(
                                source_type="LEARNER_DISCORD",
                                title=f"Knowledge Graph (Entity: {p.get('entities', [clean_query])[0]})",
                                url="file://data/graph_store.json",
                                excerpt=f"🌐 Context Graph: {snippet}",
                                authority="Knowledge Graph DB",
                            )
                        )

            except Exception:
                pass

        # 3. Search Official Course Documents (Strict Heading / Term Match)
        if len(citations) < limit and words:
            # Exclude meta spec/rubric files unless query explicitly asks about spec, de bai, or rubric
            is_asking_meta_spec = any(w in clean_query for w in ["spec", "đề bài", "rubric", "chấm điểm", "khung"])
            for fname, content in self.official_docs:
                if not is_asking_meta_spec and fname in ["01-de-bai.md", "02-guide.md", "03-template-ai-spec.md", "04-rubric.md", "spec.md"]:
                    continue

                matching_lines = []
                for line in content.splitlines():
                    line_lower = line.lower()
                    matched_count = sum(1 for w in words if w in line_lower)
                    if matched_count >= 2 and len(line.strip()) > 15:
                        matching_lines.append(line.strip())

                if matching_lines:
                    snippet = "\n".join(matching_lines[:3])
                    citations.append(
                        Citation(
                            source_type="OFFICIAL_DOCUMENT",
                            title=f"Tài liệu chính thức ({fname})",
                            url=f"file://{fname}",
                            excerpt=snippet[:350],
                            authority="BTC AI Thực Chiến",
                        )
                    )


        return citations

