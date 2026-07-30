"""Program archive sync coordinator managing exporter jobs and atomic database ingestion."""

import asyncio
from datetime import datetime, timezone
import uuid
from pathlib import Path
from typing import List, Optional
import aiosqlite

from odysseybot.config import settings
from odysseybot.domain.models import SyncResult, SyncStatus
from odysseybot.ingestion.dce_adapter import DCEAdapter, DCEAdapterError, DCEAuthError
from odysseybot.ingestion.artifact_importer import ArtifactImporter
from odysseybot.ingestion.thread_manifest import ThreadManifest


class ProgramArchiveSync:
    """Coordinates DCE subprocess execution, manifest iteration, atomic artifact ingestion, and cursors."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or settings.DATABASE_PATH
        self.adapter = DCEAdapter()
        self.importer = ArtifactImporter(self.db_path)
        self.manifest = ThreadManifest()

    async def get_last_successful_timestamp(self) -> Optional[str]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT last_timestamp FROM sync_cursors WHERE key = 'dce_incremental';") as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None

    async def update_cursor(self, timestamp: str) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO sync_cursors (key, last_timestamp, updated_at) VALUES ('dce_incremental', ?, CURRENT_TIMESTAMP) ON CONFLICT(key) DO UPDATE SET last_timestamp = excluded.last_timestamp, updated_at = CURRENT_TIMESTAMP;",
                (timestamp,)
            )
            await db.commit()

    async def run_incremental(self) -> SyncResult:

        if not settings.DCE_SYNC_ENABLED:
            return SyncResult(
                run_id=str(uuid.uuid4()),
                status="disabled",
                file_count=0,
                message_count=0,
                error_message="DCE_SYNC_ENABLED is false",
            )

        run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        staging_dir = Path("data/runtime/source-sync/staging") / f"{run_id}.partial"
        ready_dir = Path("data/runtime/source-sync/ready") / run_id
        imported_dir = Path("data/runtime/source-sync/imported") / run_id
        staging_dir.mkdir(parents=True, exist_ok=True)

        after_timestamp = await self.get_last_successful_timestamp()

        # Gather target channels/threads
        channels_to_export = list(settings.DCE_FORUM_CHANNEL_IDS)
        channels_to_export.extend(self.manifest.get_all_thread_ids())

        total_files = 0
        total_messages = 0

        try:
            for channel_id in set(channels_to_export):
                try:
                    exported_file = await self.adapter.export_channel(
                        channel_id=channel_id,
                        output_dir=staging_dir,
                        after_timestamp=after_timestamp,
                        include_threads=True,
                    )
                    total_files += 1

                    inserted, _ = await self.importer.import_json_file(exported_file)
                    total_messages += inserted
                except DCEAuthError as auth_err:
                    raise auth_err
                except DCEAdapterError:
                    continue

            # Atomically move partial -> ready
            ready_dir.parent.mkdir(parents=True, exist_ok=True)
            staging_dir.rename(ready_dir)

            # Move ready -> imported
            imported_dir.parent.mkdir(parents=True, exist_ok=True)
            ready_dir.rename(imported_dir)

            now_iso = datetime.now(timezone.utc).isoformat()
            await self.update_cursor(now_iso)

            return SyncResult(
                run_id=run_id,
                status="success",
                file_count=total_files,
                message_count=total_messages,
            )

        except DCEAuthError as auth_err:
            return SyncResult(
                run_id=run_id,
                status="failed",
                file_count=total_files,
                message_count=total_messages,
                error_message=f"AUTH ERROR: {auth_err}",
            )
        except Exception as e:
            return SyncResult(
                run_id=run_id,
                status="failed",
                file_count=total_files,
                message_count=total_messages,
                error_message=str(e),
            )
