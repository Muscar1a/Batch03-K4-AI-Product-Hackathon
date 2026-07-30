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
        clean_q = query.lower()

        # Check if query is overly broad/vague (e.g., short generic words without specific scope)
        broad_terms = {"hướng dẫn", "setup", "cài đặt", "lỗi", "giúp em", "bot", "ai log", "claude", "cp", "nộp bài", "cho em hỏi"}
        words = clean_q.split()
        
        # If query is extremely short (< 3 words) and contains only generic terms, classify as CLARIFICATION
        is_broad = (len(words) <= 2 and clean_q in broad_terms) or clean_q in ["làm thế nào", "hướng dẫn em", "setup sao", "lỗi rồi"]

        if is_broad:
            intent = "CLARIFICATION"
        else:
            is_tech = any(kw in clean_q for kw in ["search", "tìm kiếm", "web", "docs", "langgraph", "python", "lỗi", "code"])
            intent = "TECHNICAL" if is_tech else "LOGISTICS"

        return {"query": query, "intent": intent, "citations": [], "tools_used": []}

    async def _retrieve_claims_node(self, state: AgentState) -> Dict[str, Any]:
        if state.get("intent") == "CLARIFICATION":
            return {
                "citations": [],
                "combined_context": "",
                "tools_used": state.get("tools_used", []),
            }

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
            authority_label = "[Nguồn chính thức - Ban Tổ Chức/TA]" if c.source_type in ["STAFF_DISCORD", "OFFICIAL_DOCUMENT"] else f"[Ý kiến cộng đồng học viên - {c.authority}]"
            context_blocks.append(f"📌 {authority_label} ({c.title}): {c.excerpt}")

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
        intent = state.get("intent", "LOGISTICS")

        if intent == "CLARIFICATION":
            synthesized_text = (
                "👋 **Bạn có thể đặt câu hỏi cụ thể hơn một chút không?**\n\n"
                "Câu hỏi hiện tại hơi ngắn hoặc chung chung. Để OdysseyBot có thể tìm đúng thông tin và hỗ trợ bạn tốt nhất, bạn vui lòng cho mình biết rõ hơn nhé:\n"
                "- 📌 *Bạn đang cần hỗ trợ về công cụ/mục nào?* (VD: `AI LOG`, `Claude Code`, `Quy định nộp bài CP4`, `Điểm danh`...)\n"
                "- 📌 *Lỗi hoặc thắc mắc cụ thể của bạn là gì?*\n\n"
                "👉 *Ví dụ câu hỏi rõ ràng*: `!hoi hướng dẫn từng bước setup AI LOG trên VS Code`"
            )
            return {"response_text": synthesized_text}

        synthesized_text = ""
        if llm_client:
            try:
                system_prompt = (
                    "Bạn là OdysseyBot - Trợ lý AI Học viên chính thức của khóa học.\n"
                    "Nhiệm vụ: Cung cấp câu trả lời ĐẦY ĐỦ THÔNG TIN, RÕ RÀNG VÀ HỮU ÍCH dựa trên NGỮ CẢNH DỮ LIỆU.\n\n"
                    "Quy tắc tổng hợp và hành văn tuyệt đối:\n"
                    "1. Chi tiết và hữu ích: Đừng chỉ tóm tắt 1-2 câu qua loa. Hãy trích xuất rõ các bước hướng dẫn, tên biến/cấu hình, câu trả lời cụ thể từ Ban Tổ Chức/TA hoặc học viên nếu có trong ngữ cảnh.\n"
                    "2. Phân định rõ ràng nguồn tin:\n"
                    "   - Nếu có thông tin từ Ban Tổ Chức/TA: Trình bày chi tiết các lưu ý/chỉ đạo chính thức.\n"
                    "   - Nếu có hướng dẫn/chia sẻ mẹo từ học viên: Hãy trích dẫn chi tiết giải pháp đó (VD: 'Theo hướng dẫn chia sẻ từ học viên [Tên]...').\n"
                    "3. Loại bỏ tin rác: Bỏ qua hoàn toàn các tin nhắn tán xàm/chọc ghẹo không liên quan.\n"
                    "4. Không tự chèn các link thô dạng file:// hay URL dài vào văn bản.\n\n"
                    f"NGỮ CẢNH DỮ LIỆU:\n{combined_context}\n\n"
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

                    # Prune citations if the synthesized response states no information was found
                    if any(phrase in synthesized_text.lower() for phrase in ["không tìm thấy", "chưa có thông tin", "không thể xác định", "0 bài đăng"]):
                        # Filter to only keep citations whose author is explicitly mentioned in the response
                        relevant_citations = []
                        for c in all_citations:
                            author_clean = c.authority.split("bởi ")[-1].split(" - ")[0].strip().lower()
                            if author_clean and author_clean in synthesized_text.lower():
                                relevant_citations.append(c)
                        all_citations = relevant_citations
            except Exception:
                pass

        if not synthesized_text:
            if combined_context:
                synthesized_text = (
                    "ℹ️ **[Thông tin tổng hợp từ cộng đồng]**\n\n"
                    "Hiện chưa có quy định chính thức từ BTC về câu hỏi này, tuy nhiên dưới đây là các trao đổi liên quan trong cộng đồng học viên:\n\n"
                    f"{combined_context}"
                )
            else:
                synthesized_text = (
                    "❓ **[Chưa có thông tin chính thức]**\n"
                    "Hiện tại hệ thống chưa tìm thấy thông tin chính thức từ BTC về nội dung này. "
                    "Mình đã chuyển câu hỏi tới các anh chị Lab Coach / TA để hỗ trợ bạn sớm nhất nhé!"
                )
                all_citations = []

        return {"response_text": synthesized_text, "citations": all_citations}


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
