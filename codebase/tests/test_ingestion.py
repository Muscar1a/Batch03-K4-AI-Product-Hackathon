import pytest
from pathlib import Path
from odysseybot.knowledge.db import init_db_async
from odysseybot.ingestion.artifact_importer import ArtifactImporter
from odysseybot.ingestion.thread_manifest import ThreadManifest

@pytest.mark.asyncio
async def test_sqlite_db_init_and_importer(tmp_path: Path):
    db_file = tmp_path / "test_odyssey.sqlite3"
    await init_db_async(db_file)
    assert db_file.exists()

    importer = ArtifactImporter(db_file)
    with pytest.raises(FileNotFoundError):
        await importer.import_json_file(Path("non_existent.json"))


def test_thread_manifest(tmp_path: Path):
    manifest_file = tmp_path / "program_threads.json"
    manifest = ThreadManifest(manifest_file)
    
    entry = manifest.add_thread("123456789", "forum_1", "Test Thread")
    assert entry.thread_id == "123456789"
    assert entry.name == "Test Thread"
    assert "123456789" in manifest.get_all_thread_ids()
