"""Script to import existing json files from data/discord-crawl into SQLite database."""

import asyncio
from pathlib import Path
from odysseybot.config import settings
from odysseybot.knowledge.db import init_db_sync
from odysseybot.ingestion.artifact_importer import ArtifactImporter

async def main():
    db_path = settings.DATABASE_PATH
    init_db_sync(db_path)
    
    crawl_dir = Path("data/discord-crawl")
    if not crawl_dir.exists():
        print(f"❌ Directory {crawl_dir} does not exist.")
        return

    importer = ArtifactImporter(db_path)
    json_files = list(crawl_dir.glob("*.json"))
    print(f"📦 Found {len(json_files)} JSON export files. Importing into SQLite...")

    total_inserted = 0
    total_skipped = 0

    for idx, fpath in enumerate(json_files, 1):
        inserted, skipped = await importer.import_json_file(fpath)
        total_inserted += inserted
        total_skipped += skipped
        if idx % 50 == 0 or idx == len(json_files):
            print(f"  Processed {idx}/{len(json_files)} files (Inserted: {total_inserted}, Skipped: {total_skipped})...")

    print(f"✅ Import complete! Total inserted messages: {total_inserted}")

if __name__ == "__main__":
    asyncio.run(main())
