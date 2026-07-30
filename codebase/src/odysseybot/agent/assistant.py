"""Grounded LangGraph Assistant StateGraph implementation."""

import asyncio
from datetime import datetime, timezone
import json
import os
from typing import Any, Dict, List, Optional, TypedDict
import aiosqlite

from langgraph.graph import StateGraph, END
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


class AgentState(TypedDict):
    request: AskRequest
    query: str
    intent: str
    citations: List[Citation]
    combined_context: str
    response_text: str
    status: str
    escalated: bool
    tools_used: List[str]


class GroundedAssistant:
    """Orchestrates LangGraph StateGraph pipeline for grounded answers with Gemini, FTS5 retriever, and Web tools."""

    def __init__(self):
        self.retriever = KnowledgeRetriever()
        self.web_search = WebSearchAdapter()
        self.web_reader = WebReaderAdapter()
        self.workflow = self._build_graph()

    def _build_graph(self) -> Any:
        builder = StateGraph(AgentState)

        builder.add_node("classify_intent", self._classify_intent_node)
        builder.add_node("retrieve_claims", self._retrieve_claims_node)
        builder.add_node("verify_evidence", self._verify_evidence_node)
        builder.add_node("synthesize_answer", self._synthesize_answer_node)
        builder.add_node("log_interaction", self._log_interaction_node)

        builder.set_entry_point("classify_intent")
        builder.add_edge("classify_intent", "retrieve_claims")
        builder.add_edge("retrieve_claims", "verify_evidence")
        builder.add_edge("verify_evidence", "synthesize_answer")
        builder.add_edge("synthesize_answer", "log_interaction")
        builder.add_edge("log_interaction", END)

        return builder.compile()

    async def _classify_intent_node(self, state: AgentState) -> Dict[str, Any]:
        query = state["request"].text.strip()
        is_tech = any(kw in query.lower() for kw in ["search", "tìm kiếm", "web", "docs", "langgraph", "python", "lỗi", "code"])
        intent = "TECHNICAL" if is_tech else "LOGISTICS"
        return {"query": query, "intent": intent, "citations": [], "tools_used": []}

    async def _retrieve_claims_node(self, state: AgentState) -> Dict[str, Any]:
        query = state["query"]
        citations = await self.retriever.search_staff_claims(query)
        tools_used = list(state.get("tools_used", [])) + ["fts_source_messages"]

        web_citations = []
        if state["intent"] == "TECHNICAL" and not citations:
            tools_used.append("search_technical_web")
            web_results = await self.web_search.search(query, max_results=2)
            for res in web_results:
                title = res.get("title", "Web Link")
                url = res.get("url", "")
                snippet = res.get("content", "")
                if snippet:
                    web_citations.append(
                        Citation(
                            source_type="TECHNICAL_WEB",
                            title=title,
                            url=url,
                            excerpt=snippet[:250],
                            authority="External Web Documentation",
                        )
                    )

        all_citations = citations + web_citations
        context_blocks = []
        for c in all_citations:
            context_blocks.append(f"📌 [{c.title}]: {c.excerpt}")

        combined_context = "\n\n".join(context_blocks)
        return {
            "citations": all_citations,
            "combined_context": combined_context,
            "tools_used": tools_used,
        }

    async def _verify_evidence_node(self, state: AgentState) -> Dict[str, Any]:
        citations = state.get("citations", [])
        has_staff_evidence = any(c.source_type in ["STAFF_DISCORD", "OFFICIAL_DOCUMENT"] for c in citations)
        if not citations or not has_staff_evidence:
            status = "ESCALATED"
            escalated = True
        else:
            status = "BOT_ANSWERED"
            escalated = False
        return {"status": status, "escalated": escalated}


    async def _synthesize_answer_node(self, state: AgentState) -> Dict[str, Any]:
        query = state["query"]
        combined_context = state.get("combined_context", "")
        status = state.get("status", "BOT_ANSWERED")

        synthesized_text = ""
        if llm_client:
            try:
                system_prompt = (
                    "Bạn là Trợ lý AI Học viên (OdysseyBot) chu đáo, chính xác và minh bạch.\n"
                    "Nhiệm vụ: Trả lời câu hỏi học viên dựa trên NGỮ CẢNH DỮ LIỆU bên dưới.\n"
                    "Quy tắc tuyệt đối:\n"
                    "1. Nếu NGỮ CẢNH không chứa thông tin trực tiếp trả lời câu hỏi, hãy lịch sự thông báo chưa có dữ liệu chính thức và khuyên liên hệ BTC/TA. KHÔNG trích dẫn hoặc viện dẫn các kênh/thread trong ngữ cảnh nếu nội dung của chúng không liên quan đến câu hỏi.\n"
                    "2. Không tự ý chèn các đoạn trích dẫn nguồn hoặc link dạng [Thread ...] hay (bởi ...) trong phần thân văn bản. Phần trích dẫn đính kèm sẽ được hệ thống tự động thêm ở cuối.\n"
                    "3. Không bịa đặt thông tin, deadline hay quy định.\n\n"
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

        return {"response_text": synthesized_text}

    async def _log_interaction_node(self, state: AgentState) -> Dict[str, Any]:
        req = state["request"]
        try:
            async with aiosqlite.connect(settings.DATABASE_PATH) as db:
                await db.execute(
                    """
                    INSERT INTO bot_messages (id, guild_id, channel_id, user_id, query_text, response_text, intent, confidence)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        req.message_id, req.guild_id, req.channel_id, req.user_id,
                        state["query"], state["response_text"], state["intent"], 1.0
                    )
                )
                await db.execute(
                    """
                    INSERT INTO interactions (id, user_id, channel_id, message_id, action_type, payload_json)
                    VALUES (?, ?, ?, ?, ?, ?);
                    """,
                    (
                        f"act_{req.message_id}", req.user_id, req.channel_id, req.message_id,
                        "ANSWER", json.dumps({"intent": state["intent"], "status": state["status"]})
                    )
                )
                await db.commit()
        except Exception:
            pass
        return {}

    async def answer(self, request: AskRequest) -> Answer:
        initial_state: AgentState = {
            "request": request,
            "query": "",
            "intent": "LOGISTICS",
            "citations": [],
            "combined_context": "",
            "response_text": "",
            "status": "OPEN",
            "escalated": False,
            "tools_used": [],
        }

        final_state = await self.workflow.ainvoke(initial_state)

        return Answer(
            text=final_state["response_text"],
            intent=final_state["intent"],
            confidence=1.0 if final_state["citations"] else 0.5,
            citations=final_state["citations"],
            status=final_state["status"],
            escalated=final_state["escalated"],
            knowledge_freshness=datetime.now(timezone.utc) if final_state["citations"] else None,
            tools_used=final_state["tools_used"],
        )
