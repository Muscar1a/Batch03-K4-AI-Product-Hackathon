"""Personal Discord server bot runner and staff digest command interface."""

import asyncio
import os
import sys
from pathlib import Path
import discord
from discord.ext import commands

from odysseybot.config import settings
from odysseybot.domain.models import AskRequest
from odysseybot.agent.assistant import GroundedAssistant
from odysseybot.knowledge.db import init_db_sync


async def send_split_message(destination, text: str, citations_lines: list[str] = None):
    """Splits and sends long messages safely within Discord's 2000 character limit."""
    chunk_size = 1900
    
    # Send main response text in chunks if longer than 1900 chars
    if len(text) <= chunk_size:
        main_chunks = [text]
    else:
        main_chunks = []
        for i in range(0, len(text), chunk_size):
            main_chunks.append(text[i:i + chunk_size])

    for chunk in main_chunks:
        await destination.send(chunk)

    # Send citations header & lines in separate chunk
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
    # Initialize database tables
    init_db_sync(settings.DATABASE_PATH)

    token = settings.DISCORD_BOT_TOKEN.get_secret_value() if settings.DISCORD_BOT_TOKEN else os.getenv("DISCORD_TOKEN")
    if not token or token == "your_discord_bot_token_here":
        print("❌ ERROR: DISCORD_BOT_TOKEN environment variable is not configured.")
        sys.exit(1)

    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix="!", intents=intents)

    assistant = GroundedAssistant()

    @bot.event
    async def on_ready():
        print(f"✅ OdysseyBot Personal Server Bot ready: {bot.user} (ID: {bot.user.id})")

    @bot.command(name="hoi")
    async def hoi_command(ctx: commands.Context, *, query: str = ""):
        if not query:
            await ctx.send(
                "👋 **Xin chào! Mình là OdysseyBot Trợ lý Học viên AI.**\n"
                "Bạn có thể hỏi quy định, mốc deadline CP1-CP6 hoặc tra cứu bằng lệnh: `!hoi <câu hỏi>`\n"
                "📌 *Ví dụ*: `!hoi hạn nộp CP4 khóa 4 khi nào?`"
            )
            return

        async with ctx.typing():
            req = AskRequest(
                user_id=str(ctx.author.id),
                guild_id=str(ctx.guild.id) if ctx.guild else "dm",
                channel_id=str(ctx.channel.id),
                thread_id=str(ctx.thread.id) if hasattr(ctx, "thread") and ctx.thread else None,
                message_id=str(ctx.message.id),
                text=query,
            )
            answer = await assistant.answer(req)
            
        citation_lines = [f"- {c.url} - {c.title} ({c.authority})" if c.url.startswith("<#") else f"- [{c.title}]({c.url}) ({c.authority})" for c in answer.citations] if answer.citations else None
        await send_split_message(ctx, answer.text, citation_lines)

    @bot.event
    async def on_message(message: discord.Message):
        if message.author == bot.user:
            return

        # If message is a command like !hoi, let commands handler process it
        if message.content.startswith("!hoi"):
            await bot.process_commands(message)
            return

        # Otherwise, check for direct bot mentions
        if bot.user and bot.user in message.mentions:
            query = message.content.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "").strip()
            if query:
                async with message.channel.typing():
                    req = AskRequest(
                        user_id=str(message.author.id),
                        guild_id=str(message.guild.id) if message.guild else "dm",
                        channel_id=str(message.channel.id),
                        thread_id=str(message.thread.id) if hasattr(message, "thread") and message.thread else None,
                        message_id=str(message.id),
                        text=query,
                    )
                    answer = await assistant.answer(req)

                citation_lines = [f"- {c.url} - {c.title} ({c.authority})" if c.url.startswith("<#") else f"- [{c.title}]({c.url}) ({c.authority})" for c in answer.citations] if answer.citations else None
                await send_split_message(message.channel, answer.text, citation_lines)
                return


        await bot.process_commands(message)

    bot.run(token)


if __name__ == "__main__":
    main()
