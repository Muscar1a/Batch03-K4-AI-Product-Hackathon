import re
from typing import Dict, Any, List
from src.agent.state import ChatbotState, UserFact
from src.agent.tools import execute_tool_by_name

# Knowledge Base chính thức từ BTC (01-de-bai.md, 02-guide.md, 04-rubric.md)
KNOWLEDGE_BASE = {
    "cp1": {
        "title": "Checkpoint 1 (Canvas)",
        "content": "Khóa 3: 10:00 Ngày 1 | Khóa 4: 15:00 Ngày 1. Nội dung: Canvas 7 dòng (hướng, job executor, pain 1 câu, evidence, lát cắt, automation, willing users).",
        "citation": "04-rubric.md §Phần 3"
    },
    "cp2": {
        "title": "Checkpoint 2 (Show thứ bấm được)",
        "content": "Khóa 3: 12:00 Ngày 1 | Khóa 4: 17:00 Ngày 1. Nội dung: Flow chính bấm đi hết được (Sketch/Mock) + commit đầu trên Repo.",
        "citation": "04-rubric.md §Phần 3"
    },
    "cp3": {
        "title": "Checkpoint 3 (AI thật + Đo lượt 1)",
        "content": "Khóa 3: 16:00 Ngày 1 | Khóa 4: 10:30 Ngày 2. Nội dung: ≥1 lời gọi AI thật + Golden set ≥20 cases + bảng kết quả lượt 1.",
        "citation": "04-rubric.md §Phần 3"
    },
    "cp4": {
        "title": "Checkpoint 4 (Chốt tiến độ & Spec)",
        "content": "Khóa 3: 17:30 Ngày 1 | Khóa 4: 12:00 Ngày 2. ⏰ HẠN CỨNG SPEC: Commit spec.md trước 23:59 Ngày 1.",
        "citation": "01-de-bai.md & 04-rubric.md"
    },
    "cp5": {
        "title": "Checkpoint 5 (Validation & Dry run)",
        "content": "Khóa 3: 09:00 Ngày 2 | Khóa 4: 14:00 Ngày 2. Nội dung: Log user test ≥5 mẩu có tên + Changelog + Slide final + Dry run 5 phút.",
        "citation": "04-rubric.md §Phần 3"
    },
    "cp6": {
        "title": "Checkpoint 6 (Demo chính thức)",
        "content": "Khóa 3: 10:00 Ngày 2 | Khóa 4: 15:00 Ngày 2. Nội dung: 5 phút demo + 5 phút Q&A.",
        "citation": "04-rubric.md §Phần 3"
    },
    "vlearn": {
        "title": "Nền tảng VLearn & Codelabs",
        "content": "Trang học tập và nộp bài tại https://vlearn.dev và Codelabs tại https://codelabs.vlearn.dev.",
        "citation": "02-guide.md §Vlearn"
    },
    "ai-log": {
        "title": "Hướng dẫn Setup AI Log",
        "content": "Cài đặt git pre-push hook theo hướng dẫn trong kênh #chia-sẻ. Kiểm tra file overview.txt trong .system_generated/logs/. Với Windows/macOS: đảm bảo chạy agy cli trong git bash/pwsh.",
        "citation": "02-guide.md §AI-Log"
    },
    "form_nghi_hoc": {
        "title": "Form Xin Nghỉ Phép",
        "content": "Học viên xin nghỉ phép điền form chính thức tại link BTC và chờ Lab Coach duyệt.",
        "citation": "01-de-bai.md §Quy định chuyên cần"
    }
}

def memory_extractor_and_router_node(state: ChatbotState) -> Dict[str, Any]:
    """
    Node 1: Extract dynamic facts from user message & route intent.
    """
    messages = state.get("messages", [])
    if not messages:
        return {"intent": "LOGISTICS"}
    
    last_user_msg = messages[-1].get("content", "").lower().strip()
    extracted_facts: List[UserFact] = list(state.get("extracted_user_facts", []))
    
    # 1. Memory Extraction (Hệ điều hành, Nhóm)
    if "windows" in last_user_msg:
        extracted_facts.append({"fact_type": "OS", "value": "Windows", "timestamp": "now"})
    elif "mac" in last_user_msg or "macos" in last_user_msg:
        extracted_facts.append({"fact_type": "OS", "value": "macOS", "timestamp": "now"})
        
    group_match = re.search(r"g\d+|nhóm\s*\d+|team\s*\d+", last_user_msg)
    if group_match:
        extracted_facts.append({"fact_type": "GROUP", "value": group_match.group(0).upper(), "timestamp": "now"})

    # 2. Intent Routing Logic
    # 2.1 Out of Scope check (Lớp ③ - HAX G8)
    out_keywords = ["đáp án", "giải hộ", "viết hộ", "cho xin code", "làm hộ", "bỏ qua quy định", "viết code", "code react"]
    if any(kw in last_user_msg for kw in out_keywords):
        return {
            "intent": "OUT_OF_SCOPE",
            "extracted_user_facts": extracted_facts
        }

    # 2.2 Ambiguous check (Lớp ② - HAX G10)
    ambiguous_keywords = ["hạn nộp", "deadline", "mấy giờ nộp", "khi nào nộp", "hết hạn"]
    has_any_cp_mention = bool(re.search(r"cp\s*\d+|checkpoint\s*\d+", last_user_msg))
    if any(kw in last_user_msg for kw in ambiguous_keywords) and not has_any_cp_mention:
        return {
            "intent": "AMBIGUOUS",
            "extracted_user_facts": extracted_facts
        }

    # 2.3 Tool execution check
    if "tìm kiếm trên web" in last_user_msg or "google" in last_user_msg or "web search" in last_user_msg:
        return {
            "intent": "EXECUTE_TOOL",
            "target_tool": "web_search_tool",
            "extracted_user_facts": extracted_facts
        }
    if "kiểm tra github" in last_user_msg or "kiểm tra repo" in last_user_msg:
        return {
            "intent": "EXECUTE_TOOL",
            "target_tool": "github_repo_checker_tool",
            "extracted_user_facts": extracted_facts
        }
    if "điểm danh qr" in last_user_msg or "kết quả điểm danh" in last_user_msg:
        return {
            "intent": "EXECUTE_TOOL",
            "target_tool": "vlearn_api_tool",
            "extracted_user_facts": extracted_facts
        }

    # 2.4 Tech Bug
    if "lỗi" in last_user_msg or "bug" in last_user_msg or "ai log" in last_user_msg or "git push" in last_user_msg:
        return {
            "intent": "TECH_BUG",
            "extracted_user_facts": extracted_facts
        }

    # Default: Logistics
    return {
        "intent": "LOGISTICS",
        "extracted_user_facts": extracted_facts
    }

def kg_retriever_node(state: ChatbotState) -> Dict[str, Any]:
    """
    Node 2: Search Knowledge Graph DB & official docs.
    Simulates 2-hop traversal using extracted user facts + question context.
    """
    messages = state.get("messages", [])
    last_user_msg = messages[-1].get("content", "").lower().strip() if messages else ""
    user_facts = state.get("extracted_user_facts", [])
    
    retrieved_parts = []
    citations = []
    
    # Context-aware augmentation from Memory (OS / Group)
    user_os = next((f["value"] for f in reversed(user_facts) if f["fact_type"] == "OS"), None)
    
    # Check tech bug for AI Log
    if "ai log" in last_user_msg or "git push" in last_user_msg or "lỗi" in last_user_msg:
        data = KNOWLEDGE_BASE["ai-log"]
        content = data["content"]
        if user_os:
            content += f"\n💡 [Ghi nhận hệ điều hành của bạn: {user_os}]: Áp dụng hướng dẫn cài đặt git pre-push hook dành cho {user_os}."
        retrieved_parts.append(f"📌 **{data['title']}**:\n{content}")
        citations.append(data["citation"])

    # 2-hop lookup matching for CPs and Vlearn
    for key, data in KNOWLEDGE_BASE.items():
        if key == "ai-log":
            continue
        normalized_key = key.replace("-", " ")
        if key in last_user_msg or normalized_key in last_user_msg or (key.startswith("cp") and key in last_user_msg.replace("checkpoint ", "cp")):
            retrieved_parts.append(f"📌 **{data['title']}**:\n{data['content']}")
            citations.append(data["citation"])
            
    if not retrieved_parts:
        if "nghỉ" in last_user_msg:
            data = KNOWLEDGE_BASE["form_nghi_hoc"]
            retrieved_parts.append(f"📌 **{data['title']}**:\n{data['content']}")
            citations.append(data["citation"])
        else:
            retrieved_parts.append("Chưa tìm thấy căn cứ chính thức từ văn bản BTC cho câu hỏi này.")
            citations.append("Không có nguồn")

    return {
        "retrieved_context": "\n\n".join(retrieved_parts),
        "citations": list(set(citations))
    }

def tool_execution_node(state: ChatbotState) -> Dict[str, Any]:
    """
    Node 3: Execute external sub-agent tool.
    """
    tool_name = state.get("target_tool", "web_search_tool")
    messages = state.get("messages", [])
    query = messages[-1].get("content", "") if messages else "Tra cứu"
    
    result = execute_tool_by_name(tool_name, query)
    return {
        "retrieved_context": result,
        "citations": [f"Tool Execution: {tool_name}"]
    }

def clarification_node(state: ChatbotState) -> Dict[str, Any]:
    """
    Node 4: Clarification & Guardrail when prompt is ambiguous (HAX G10).
    """
    response = (
        "❓ **[Cần làm rõ thông tin - HAX G10]**\n"
        "Bạn đang muốn tra cứu mốc deadline cho **Checkpoint mấy** (CP1 -> CP6) và thuộc **Khóa 3** hay **Khóa 4**?\n\n"
        "👉 *Gợi ý gõ*: `!hoi deadline CP4 khóa 4 khi nào?`"
    )
    return {
        "final_response": response,
        "citations": ["HAX G10 Guardrail"]
    }

def guardrail_refusal_node(state: ChatbotState) -> Dict[str, Any]:
    """
    Node 5: Refusal guardrail for out-of-scope requests (HAX G8).
    """
    response = (
        "⚠️ **[Từ chối - Ngoài thẩm quyền HAX G8]**\n"
        "Trợ lý chỉ hỗ trợ tra cứu logistics, deadline và quy định khóa học.\n"
        "Bot không hỗ trợ giải bài tập cá nhân hay tự động viết code.\n"
        "Bạn hãy tham khảo slide bài giảng hoặc thảo luận cùng nhóm tại kênh `#hỏi-đáp` nhé!"
    )
    return {
        "final_response": response,
        "citations": ["HAX G8 Scope Guardrail"]
    }

def answer_synthesizer_node(state: ChatbotState) -> Dict[str, Any]:
    """
    Node 6: Synthesize final answer with grounding citations (HAX G2).
    """
    context = state.get("retrieved_context", "")
    citations = state.get("citations", [])
    
    if "Chưa tìm thấy căn cứ chính thức" in context:
        response = (
            "🔍 **[Chưa có căn cứ chính thức - HAX G10]**\n"
            "Hiện tại chưa tìm thấy thông tin chính thức của BTC về câu hỏi này.\n"
            "📩 Đã ghi nhận và chuyển thông báo tới các **Lab Coach / TA** (@LabCoach) để hỗ trợ bạn sớm nhất!"
        )
    else:
        citation_str = "\n".join([f"- *Nguồn: {c}*" for c in citations])
        response = (
            f"🤖 **[Trợ lý Học viên AI - Thông tin chính thức HAX G2]**\n\n"
            f"{context}\n\n"
            f"📌 **Trích dẫn minh bạch**:\n{citation_str}"
        )
        
    return {
        "final_response": response,
        "citations": citations
    }
