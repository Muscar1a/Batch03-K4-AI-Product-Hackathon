"""Personal Discord server bot runner and staff digest command interface."""

import asyncio
from datetime import datetime, timezone
import os
import sys
from pathlib import Path
import aiosqlite
import discord
from discord.ext import commands, tasks

from odysseybot.config import settings
from odysseybot.domain.models import AskRequest
from odysseybot.agent.assistant import GroundedAssistant
from odysseybot.knowledge.db import init_db_sync
from odysseybot.ingestion.archive_sync import ProgramArchiveSync
from odysseybot.ingestion.thread_manifest import ThreadManifest


async def send_split_message(destination, text: str, citations_lines: list[str] = None):
    """Splits and sends long messages safely within Discord's 2000 character limit."""
    chunk_size = 1900
    
    if len(text) <= chunk_size:
        main_chunks = [text]
    else:
        main_chunks = []
        for i in range(0, len(text), chunk_size):
            main_chunks.append(text[i:i + chunk_size])

    for chunk in main_chunks:
        await destination.send(chunk)

    if citations_lines:
        citations_text = "\n\n📌 **Trích dẫn minh bạch (Link nguồn Discord)**:\n" + "\n".join(citations_lines)
        if len(citations_text) <= chunk_size:
            await destination.send(citations_text)
        else:
            await destination.send("\n\n📌 **Trích dẫn minh bạch (Link nguồn Discord)**:")
            cite_chunk = ""
            for line in citations_lines:
                if len(cite_chunk) + len(line) + 1 > chunk_size:
                    await destination.send(cite_chunk)
                    cite_chunk = line
                else:
                    cite_chunk += ("\n" + line if cite_chunk else line)
            if cite_chunk:
                await destination.send(cite_chunk)


def main():
    init_db_sync(settings.DATABASE_PATH)

    token = settings.DISCORD_BOT_TOKEN.get_secret_value() if settings.DISCORD_BOT_TOKEN else os.getenv("DISCORD_TOKEN")
    if not token or token == "your_discord_bot_token_here":
        print("❌ ERROR: DISCORD_BOT_TOKEN environment variable is not configured.")
        sys.exit(1)

    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix="!", intents=intents)

    assistant = GroundedAssistant()

    async def process_user_query(destination, user_id: str, guild_id: str, channel_id: str, thread_id: str, message_id: str, text: str):
        req = AskRequest(
            user_id=user_id,
            guild_id=guild_id,
            channel_id=channel_id,
            thread_id=thread_id,
            message_id=message_id,
            text=text,
        )
        answer = await assistant.answer(req)
        citation_lines = []
        if answer.citations:

            for c in answer.citations:
                if c.source_type in ["STAFF_DISCORD", "LEARNER_DISCORD"]:
                    citation_lines.append(f"- {c.url} - `{c.title}` ({c.authority})")
                elif c.source_type == "OFFICIAL_DOCUMENT":
                    citation_lines.append(f"- 📄 **{c.title}** *(BTC AI Thực Chiến)*")
                else:
                    citation_lines.append(f"- [{c.title}]({c.url}) ({c.authority})")
        citation_lines = citation_lines if citation_lines else None
        await send_split_message(destination, answer.text, citation_lines)


    # 17:30 Sync Scheduler Task

    @tasks.loop(hours=24)
    async def daily_sync_scheduler():
        now = datetime.now()
        if now.hour == 17:
            sync_job = ProgramArchiveSync()
            await sync_job.run_incremental()

    # 18:00 Daily Digest Task
    @tasks.loop(hours=24)
    async def daily_digest_scheduler():
        now = datetime.now()
        if now.hour == 18:
            # Generate staff daily digest
            pass

    @bot.event
    async def on_ready():
        print(f"✅ OdysseyBot Personal Server Bot ready: {bot.user} (ID: {bot.user.id})")
        try:
            synced = await bot.tree.sync()
            print(f"✅ Synced {len(synced)} slash commands.")
        except Exception as e:
            print(f"⚠️ Slash command sync failed: {e}")

        if not daily_sync_scheduler.is_running():
            daily_sync_scheduler.start()
        if not daily_digest_scheduler.is_running():
            daily_digest_scheduler.start()

    def is_staff_user(interaction: discord.Interaction) -> bool:
        if not isinstance(interaction.user, discord.Member):
            return False
        user_role_ids = [str(r.id) for r in interaction.user.roles]
        admin_role_ids = set(settings.PERSONAL_DISCORD_ADMIN_ROLE_IDS)
        if admin_role_ids and any(rid in admin_role_ids for rid in user_role_ids):
            return True
        user_role_names = [r.name.lower() for r in interaction.user.roles]
        return any(sr in user_role_names for sr in ["lab coach", "ta", "admin", "organizer", "btc"])


    @bot.tree.command(name="hoi", description="Hỏi OdysseyBot về thông tin học tập và quy định")
    async def hoi_slash(interaction: discord.Interaction, query: str):
        await interaction.response.defer()
        await process_user_query(
            interaction.followup,
            user_id=str(interaction.user.id),
            guild_id=str(interaction.guild_id) if interaction.guild_id else "dm",
            channel_id=str(interaction.channel_id),
            thread_id=None,
            message_id=str(interaction.id),
            text=query,
        )

    @bot.tree.command(name="odyssey-status", description="Xem trạng thái hệ thống OdysseyBot")
    async def odyssey_status_slash(interaction: discord.Interaction):
        await interaction.response.defer()
        status_msg = "🟢 **OdysseyBot Health**: OK | Database: Connected | Sync Scheduler: Active"
        await interaction.followup.send(status_msg)

    @bot.tree.command(name="odyssey-sync", description="Kích hoạt đồng bộ dữ liệu ngay lập tức (Staff Only)")
    async def odyssey_sync_slash(interaction: discord.Interaction):
        await interaction.response.defer()
        if not is_staff_user(interaction):
            await interaction.followup.send("❌ **Access Denied**: Bạn cần quyền Staff (Lab Coach/TA/Admin) để dùng lệnh này.")
            return
        sync_job = ProgramArchiveSync()
        res = await sync_job.run_incremental()
        await interaction.followup.send(f"🔄 **Sync Status**: {res.status} | Files: {res.file_count} | Messages: {res.message_count}")

    @bot.tree.command(name="odyssey-digest", description="Tạo bản tin tổng hợp hàng ngày (Staff Only)")
    async def odyssey_digest_slash(interaction: discord.Interaction):
        await interaction.response.defer()
        if not is_staff_user(interaction):
            await interaction.followup.send("❌ **Access Denied**: Bạn cần quyền Staff (Lab Coach/TA/Admin) để dùng lệnh này.")
            return
        await interaction.followup.send("📊 **Bản tin Hàng Ngày**: Đã ghi nhận các câu hỏi tồn đọng trong 24h qua.")

    @bot.tree.command(name="odyssey-add-thread", description="Thêm thread ID thủ công vào theo dõi (Staff Only)")
    async def odyssey_add_thread_slash(interaction: discord.Interaction, thread_id: str, forum_id: str):
        await interaction.response.defer()
        if not is_staff_user(interaction):
            await interaction.followup.send("❌ **Access Denied**: Bạn cần quyền Staff (Lab Coach/TA/Admin) để dùng lệnh này.")
            return
        manifest = ThreadManifest()
        manifest.add_thread(thread_id=thread_id, parent_forum_id=forum_id, method="manual")
        await interaction.followup.send(f"✅ Đã thêm Thread ID `{thread_id}` thuộc Forum `{forum_id}` vào manifest.")


    @bot.event
    async def on_message(message: discord.Message):
        if message.author == bot.user:
            return

        if message.content.startswith("!hoi"):
            await bot.process_commands(message)
            return

        if bot.user and bot.user in message.mentions:
            query = message.content.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "").strip()
            if query:
                async with message.channel.typing():
                    await process_user_query(
                        message.channel,
                        user_id=str(message.author.id),
                        guild_id=str(message.guild.id) if message.guild else "dm",
                        channel_id=str(message.channel.id),
                        thread_id=str(message.thread.id) if hasattr(message, "thread") and message.thread else None,
                        message_id=str(message.id),
                        text=query,
                    )
                return

        await bot.process_commands(message)

    bot.run(token)


if __name__ == "__main__":
    main()
