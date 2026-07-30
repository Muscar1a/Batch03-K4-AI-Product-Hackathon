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

        response_msg = answer.text
        if answer.citations:
            citation_lines = [f"- [{c.title}]({c.url}) *(Nguồn: {c.authority})*" for c in answer.citations]
            response_msg += "\n\n📌 **Trích dẫn minh bạch**:\n" + "\n".join(citation_lines)

        await ctx.send(response_msg)

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

                response_msg = answer.text
                if answer.citations:
                    citation_lines = [f"- [{c.title}]({c.url}) *(Nguồn: {c.authority})*" for c in answer.citations]
                    response_msg += "\n\n📌 **Trích dẫn minh bạch (Link nguồn Discord)**:\n" + "\n".join(citation_lines)

                await message.channel.send(response_msg)
                return

        await bot.process_commands(message)



    bot.run(token)


if __name__ == "__main__":
    main()
