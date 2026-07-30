"""Importer for DiscordChatExporter JSON artifacts into SQLite."""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple
import aiosqlite


class ArtifactImporter:
    """Validates and transactional imports JSON export files into SQLite database."""

    def __init__(self, db_path: Path):
        self.db_path = db_path

    @staticmethod
    def compute_content_hash(content: str, author_id: str, timestamp: str) -> str:
        raw = f"{author_id}:{timestamp}:{content}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    async def import_json_file(self, json_path: Path) -> Tuple[int, int]:
        """Reads a DCE JSON file and upserts messages into source_messages.
        
        Returns:
            Tuple[inserted_count, skipped_count]
        """
        if not json_path.exists():
            return (0, 0)

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return (0, 0)


        guild = data.get("guild", {})
        channel = data.get("channel", {})
        messages = data.get("messages", [])

        guild_id = guild.get("id", "")
        channel_id = channel.get("id", "")
        channel_name = channel.get("name", "")

        inserted = 0
        skipped = 0

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA foreign_keys = ON;")
            await db.execute("BEGIN TRANSACTION;")

            for msg in messages:
                msg_id = str(msg.get("id"))
                author = msg.get("author", {})
                author_id = str(author.get("id"))
                author_name = author.get("name", "")
                roles = author.get("roles", [])
                roles_json = json.dumps(roles, ensure_ascii=False)

                # Determine staff authority (e.g. Learner vs Lab Coach / TA / Admin)
                is_staff = 1 if any(r.get("name", "").lower() in ["lab coach", "ta", "admin", "organizer", "btc"] for r in roles) else 0

                content = msg.get("content", "")
                timestamp = msg.get("timestamp", "")
                ref_msg = msg.get("reference", {}).get("messageId")
                ref_msg_id = str(ref_msg) if ref_msg else None

                content_hash = self.compute_content_hash(content, author_id, timestamp)

                # Upsert into source_messages
                cursor = await db.execute(
                    """
                    INSERT INTO source_messages (
                        id, guild_id, channel_id, channel_name, author_id, author_name,
                        author_roles_json, is_staff, content, timestamp, reference_message_id, content_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        content = excluded.content,
                        author_roles_json = excluded.author_roles_json,
                        is_staff = excluded.is_staff,
                        content_hash = excluded.content_hash;
                    """,
                    (
                        msg_id, guild_id, channel_id, channel_name, author_id, author_name,
                        roles_json, is_staff, content, timestamp, ref_msg_id, content_hash
                    )
                )

                if cursor.rowcount > 0:
                    inserted += 1
                else:
                    skipped += 1


            await db.commit()

        return (inserted, skipped)
