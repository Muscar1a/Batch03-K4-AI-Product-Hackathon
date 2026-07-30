"""FTS5 SQLite and NetworkX projection retriever."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import aiosqlite


from odysseybot.config import settings
from odysseybot.domain.models import Citation


class KnowledgeRetriever:
    """Queries SQLite source messages (FTS5) and official documents for grounded context."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or settings.DATABASE_PATH

    async def search_staff_claims(self, query: str, limit: int = 3) -> List[Citation]:
        citations: List[Citation] = []
        if not self.db_path.exists():
            return citations

        async with aiosqlite.connect(self.db_path) as db:
            # Query FTS5 staff messages
            async with db.execute(
                """
                SELECT sm.id, sm.content, sm.author_name, sm.channel_name, sm.timestamp
                FROM fts_source_messages fts
                JOIN source_messages sm ON fts.id = sm.id
                WHERE fts.content MATCH ? AND sm.is_staff = 1
                ORDER BY sm.timestamp DESC
                LIMIT ?;
                """,
                (query, limit)
            ) as cursor:
                async for row in cursor:
                    msg_id, content, author_name, channel_name, timestamp = row
                    ts_dt = datetime.fromisoformat(timestamp) if timestamp else None
                    citations.append(
                        Citation(
                            source_type="STAFF_DISCORD",
                            title=f"Thông báo từ {author_name} (#{channel_name})",
                            url=f"https://discord.com/channels/{settings.DCE_SOURCE_GUILD_ID or '1526532830627102781'}/{msg_id}",
                            excerpt=content[:300],
                            authority=f"Staff/Admin ({author_name})",
                            source_timestamp=ts_dt,
                        )
                    )

        return citations
