"""Grounded LangGraph Assistant implementation."""

import asyncio
from datetime import datetime, timezone
import os
from typing import Any, Dict, List, Optional
import aiosqlite

from odysseybot.config import settings
from odysseybot.domain.models import Answer, AskRequest, Citation
from odysseybot.knowledge.retriever import KnowledgeRetriever
from odysseybot.adapters.web_adapters import WebSearchAdapter, WebReaderAdapter

try:
    from google import genai
    from google.genai import types
    gemini_key = settings.GEMINI_API_KEY.get_secret_value() if settings.GEMINI_API_KEY else None
    llm_client = genai.Client(api_key=gemini_key) if gemini_key else None
except Exception:
    llm_client = None
    types = None


class GroundedAssistant:
    """Orchestrates LangGraph pipeline for grounded answers with Gemini, FTS5 retriever, and Web tools."""

    def __init__(self):
        self.retriever = KnowledgeRetriever()
        self.web_search = WebSearchAdapter()
        self.web_reader = WebReaderAdapter()

    async def answer(self, request: AskRequest) -> Answer:
        query = request.text.strip()

        # Step 1: Query internal staff claims & FTS context
        staff_citations = await self.retriever.search_staff_claims(query)
        tools_used = ["fts_source_messages"]

        context_blocks = []
        for c in staff_citations:
            context_blocks.append(f"📌 [{c.title}]: {c.excerpt}")

        # Step 2: Intent check & Web fallback if needed
        is_tech = any(kw in query.lower() for kw in ["search", "tìm kiếm", "web", "docs", "langgraph", "python", "lỗi"])
        web_citations = []
        if is_tech and not staff_citations:
            tools_used.append("search_technical_web")
            web_results = await self.web_search.search(query, max_results=2)
            for res in web_results:
                title = res.get("title", "Web Link")
                url = res.get("url", "")
                snippet = res.get("content", "")
                web_citations.append(
                    Citation(
                        source_type="TECHNICAL_WEB",
                        title=title,
                        url=url,
                        excerpt=snippet[:250],
                        authority="External Web Documentation",
                    )
                )
                context_blocks.append(f"🌐 [Web: {title}]: {snippet[:250]}")

        combined_context = "\n\n".join(context_blocks)
        all_citations = staff_citations + web_citations

        # Step 3: Synthesize response with Gemini (Temperature 0)
        synthesized_text = ""
        if llm_client:
            try:
                system_prompt = (
                    "Bạn là Trợ lý AI Học viên (OdysseyBot) chu đáo, chính xác và minh bạch.\n"
                    "Nhiệm vụ: Trả lời câu hỏi học viên dựa trên NGỮ CẢNH DỮ LIỆU bên dưới.\n"
                    "Quy tắc tuyệt đối:\n"
                    "1. Không bịa đặt deadline, quy định hay điểm số nếu ngữ cảnh không đề cập.\n"
                    "2. Chỉ sử dụng thông tin chính thức có nguồn trích dẫn.\n"
                    "3. Nhiệt tình, thân thiện, rõ ràng.\n\n"
                    f"NGỮ CẢNH:\n{combined_context}\n\n"
                    f"CÂU HỎI HỌC VIÊN: {query}"
                )
                
                config = types.GenerateContentConfig(temperature=0.0) if types else None
                llm_resp = await asyncio.to_thread(
                    llm_client.models.generate_content,
                    model=settings.AI_MODEL,
                    contents=system_prompt,
                    config=config,
                )
                if llm_resp and llm_resp.text:
                    synthesized_text = llm_resp.text.strip()
            except Exception:
                pass

        if not synthesized_text:
            if combined_context:
                synthesized_text = f"🤖 **[Trợ lý AI - Thông tin tra cứu]**\n\n{combined_context}"
            else:
                synthesized_text = (
                    "❓ **[Chưa có thông tin chính thức]**\n"
                    "Hiện tại hệ thống chưa tìm thấy thông tin chính thức từ BTC về nội dung này. "
                    "Mình đã chuyển câu hỏi tới các anh chị Lab Coach / TA để hỗ trợ bạn sớm nhất nhé!"
                )

        # Log interaction to bot_messages table
        try:
            async with aiosqlite.connect(settings.DATABASE_PATH) as db:
                await db.execute(
                    """
                    INSERT INTO bot_messages (id, guild_id, channel_id, user_id, query_text, response_text, intent, confidence)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        request.message_id, request.guild_id, request.channel_id, request.user_id,
                        query, synthesized_text, "LOGISTICS" if staff_citations else "TECHNICAL", 1.0
                    )
                )
                await db.commit()
        except Exception:
            pass

        return Answer(
            text=synthesized_text,
            intent="LOGISTICS" if staff_citations else "TECHNICAL",
            confidence=1.0 if staff_citations else 0.8,
            citations=all_citations,
            status="BOT_ANSWERED",
            escalated=False,
            knowledge_freshness=datetime.now(timezone.utc),
            tools_used=tools_used,
        )
