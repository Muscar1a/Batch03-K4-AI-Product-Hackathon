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
        
        # Stopwords to filter out generic query words
        stopwords = {"hướng", "dẫn", "tôi", "cho", "em", "hỏi", "với", "setup", "cài", "đặt", "là", "gì", "khi", "nào"}
        words = [w for w in re.sub(r"[^\w\s]", " ", clean_query).split() if len(w) >= 2 and w not in stopwords]

        seen_ids = set()

        # 1. Search Database Source Messages (Highest precision for specific technical & Discord topics like "AI LOG")
        if self.db_path.exists() and clean_query:
            clean_text = re.sub(r"[^\w\s]", " ", clean_query).strip()
            # Try full phrase search first
            phrase_keywords = [clean_text] if clean_text else []
            if words:
                phrase_keywords.append(" ".join(words))

            async with aiosqlite.connect(self.db_path) as db:
                for p_kw in phrase_keywords:
                    phrase = f"%{p_kw}%"
                    async with db.execute(
                        """
                        SELECT sm.id, sm.content, sm.author_name, sm.channel_name, sm.timestamp
                        FROM source_messages sm
                        WHERE sm.content LIKE ? OR sm.channel_name LIKE ?
                        ORDER BY sm.timestamp DESC
                        LIMIT ?;
                        """,
                        (phrase, phrase, limit)
                    ) as cursor:
                        async for row in cursor:
                            msg_id, content, author_name, channel_name, timestamp = row
                            if msg_id not in seen_ids:
                                seen_ids.add(msg_id)
                                ts_dt = datetime.fromisoformat(timestamp) if timestamp else None
                                citations.append(
                                    Citation(
                                        source_type="STAFF_DISCORD",
                                        title=f"Kênh #{channel_name}",
                                        url=f"https://discord.com/channels/{settings.DCE_SOURCE_GUILD_ID or '1526532830627102781'}/{msg_id}",
                                        excerpt=content[:450],
                                        authority=f"Tác giả: {author_name}",
                                        source_timestamp=ts_dt,
                                    )
                                )

                # Fallback to key specific terms (e.g. "log", "antigravity", "claude")
                if len(citations) < limit and words:
                    for kw in sorted(words, key=len, reverse=True):
                        like_pattern = f"%{kw}%"
                        async with db.execute(
                            """
                            SELECT sm.id, sm.content, sm.author_name, sm.channel_name, sm.timestamp
                            FROM source_messages sm
                            WHERE sm.content LIKE ? OR sm.channel_name LIKE ?
                            ORDER BY sm.timestamp DESC
                            LIMIT ?;
                            """,
                            (like_pattern, like_pattern, limit - len(citations))
                        ) as cursor:
                            async for row in cursor:
                                msg_id, content, author_name, channel_name, timestamp = row
                                if msg_id not in seen_ids:
                                    seen_ids.add(msg_id)
                                    ts_dt = datetime.fromisoformat(timestamp) if timestamp else None
                                    citations.append(
                                        Citation(
                                            source_type="STAFF_DISCORD",
                                            title=f"Kênh #{channel_name}",
                                            url=f"https://discord.com/channels/{settings.DCE_SOURCE_GUILD_ID or '1526532830627102781'}/{msg_id}",
                                            excerpt=content[:450],
                                            authority=f"Tác giả: {author_name}",
                                            source_timestamp=ts_dt,
                                        )
                                    )
                        if len(citations) >= limit:
                            break

        # 2. Search Knowledge Graph DB (GraphStore traversal)
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
                                source_type="STAFF_DISCORD",
                                title=f"Knowledge Graph (Triples: {p.get('entities', [clean_query])[0]})",
                                url="file://data/graph_store.json",
                                excerpt=f"🌐 Context Graph: {snippet}",
                                authority="Knowledge Graph DB",
                            )
                        )
            except Exception:
                pass

        # 3. Search Official Course Documents (as secondary or general context)
        if len(citations) < limit and words:
            for fname, content in self.official_docs:
                matching_lines = [line for line in content.splitlines() if any(w in line.lower() for w in words)]
                if matching_lines:
                    snippet = "\n".join(matching_lines[:6])
                    citations.append(
                        Citation(
                            source_type="OFFICIAL_DOCUMENT",
                            title=f"Tài liệu chính thức ({fname})",
                            url=f"file://{fname}",
                            excerpt=snippet[:450],
                            authority="BTC AI Thực Chiến",
                        )
                    )

        return citations
