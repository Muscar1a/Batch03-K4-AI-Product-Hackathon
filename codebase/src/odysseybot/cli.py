"""CLI entrypoint for OdysseyBot operations, sync, and status."""

import asyncio
import sys
from pathlib import Path
import click

from odysseybot.config import settings
from odysseybot.knowledge.db import init_db_sync
from odysseybot.ingestion.archive_sync import ProgramArchiveSync
from odysseybot.ingestion.thread_manifest import ThreadManifest


@click.group()
def main():
    """OdysseyBot operational management CLI."""
    pass


@main.command()
def init_db():
    """Initialize SQLite schema and FTS tables."""
    init_db_sync(settings.DATABASE_PATH)
    click.echo(f"✅ Database initialized at {settings.DATABASE_PATH}")


@main.command()
def sync():
    """Run incremental DiscordChatExporter sync."""
    init_db_sync(settings.DATABASE_PATH)
    click.echo("🔄 Running incremental source sync...")
    sync_job = ProgramArchiveSync()
    result = asyncio.run(sync_job.run_incremental())
    click.echo(f"Sync complete. Status: {result.status}, Files: {result.file_count}, Messages: {result.message_count}")
    if result.error_message:
        click.echo(f"Error: {result.error_message}")


@main.command()
@click.argument("thread_id")
@click.argument("forum_id")
def add_thread(thread_id, forum_id):
    """Add a thread ID manually to the manifest."""
    manifest = ThreadManifest()
    manifest.add_thread(thread_id=thread_id, parent_forum_id=forum_id, method="manual")
    click.echo(f"✅ Thread {thread_id} added under parent forum {forum_id}")


if __name__ == "__main__":
    main()
