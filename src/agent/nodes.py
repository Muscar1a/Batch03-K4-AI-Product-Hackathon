import re
import os
from typing import Dict, Any, List
from src.agent.state import ChatbotState, UserFact
from src.agent.tools import execute_tool_by_name

# Map các tên kênh và Thread Discord sang ID Tag (<#ID>) chuẩn xác
DISCORD_CHANNEL_MAP = {
    "#🏆-chia-sẻ": "<#1530270278301519974>",
    "#chia-sẻ": "<#1530270278301519974>",
    "#🙋-hỏi-đáp": "<#1530221989157929090>",
    "#hỏi-đáp": "<#1530221989157929090>",
    "#💬-chung": "<#1527920177390293164>",
    "#chung": "<#1527920177390293164>",
    "#📖-bài-học": "<#1531838822608797747>",
    "#bài-học": "<#1531838822608797747>",
    "#feedback-vlearn": "<#1530052915383894107>"
}

def format_discord_channel_links(text: str) -> str:
    """Tự động chuyển đổi tên kênh/thread dạng #tên-kênh sang định dạng link bấm được của Discord (<#ID>)."""
    for name, channel_tag in DISCORD_CHANNEL_MAP.items():
        text = text.replace(name, channel_tag)
    return text

# 1. Tích hợp Gemini LLM SDK (google-genai) & Cấu hình Temperature
try:
    from google import genai
    from google.genai import types
    
    gemini_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if gemini_api_key:
        llm_client = genai.Client(api_key=gemini_api_key)
    else:
        llm_client = None
except Exception:
    llm_client = None
    types = None

# Temperature 0.7 cho phản hồi tự nhiên, mềm mại
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))

# 2. Tích hợp Graph DB & Memory Store từ Thành viên 1 & 2
try:
    from src.graph_db.memory_store import MemoryStore
    from src.graph_db.graph_store import GraphStore
    
    DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
    memory_store_path = os.path.join(DATA_DIR, "memory_store.json")
    graph_store_path = os.path.join(DATA_DIR, "graph_store.json")
    
    memory_engine = MemoryStore(memory_store_path)
    graph_engine = GraphStore(graph_store_path) if os.path.exists(graph_store_path) else None
    
    triples_path = os.path.join(DATA_DIR, "extracted_triples.json")
    if graph_engine and os.path.exists(triples_path) and len(graph_engine.graph.nodes) == 0:
        graph_engine.import_file(triples_path)
        graph_engine.save()
except Exception:
    memory_engine = None
    graph_engine = None

# Knowledge Base chính thức mở rộng từ BTC
KNOWLEDGE_BASE = {
    "feedback_vlearn": {
        "title": "Kênh Feedback & Báo Lỗi VLearn / Codelabs",
        "keywords": ["feedback", "góp ý", "báo lỗi vlearn", "báo lỗi codelabs", "qr feedback", "ý kiến vlearn"],
        "content": "Để gửi feedback góp ý hoặc báo lỗi UI/UX trên hệ thống VLearn/Codelabs:\n1. Quét mã QR Feedback tại Thread chính thức: <#1530052915383894107> (do Lab Coach Trần Hoàng Hà đăng tại kênh #🙋-hỏi-đáp).\n2. Hoặc gửi bài phản hồi trực tiếp tại thread 'Feedback, bug report vlearn.dev' <#1530226830920126505>.",
        "citation": "Thread QR Feedback Vlearn (#1530052915383894107) §Kênh #🙋-hỏi-đáp"
    },
    "gioi_thieu_khoa_hoc": {
        "title": "Tổng Quan Chương Trình AI Thực Chiến (AI20K Build Phase)",
        "keywords": ["ai thực chiến", "chương trình ai thực chiến", "khóa học ai thực chiến", "giới thiệu chương trình", "khoá học", "chương trình"],
        "content": "Chương trình AI Thực Chiến (Cohort 3 & 4) là khóa huấn luyện phát triển sản phẩm AI thực tế. Học viên được chia nhóm, thực hiện bài tập Lab và vượt qua 6 mốc Checkpoint (CP1 -> CP6) từ lập Canvas, Mockup UI, gọi AI API thật, hoàn thiện AI Spec đến Demo sản phẩm trước Giám khảo.",
        "citation": "01-de-bai.md & 02-guide.md §Tổng quan"
    },
    "cp1": {
        "title": "Checkpoint 1 (Canvas)",
        "keywords": ["cp1", "checkpoint 1", "canvas"],
        "content": "Khóa 3: 10:00 Ngày 1 | Khóa 4: 15:00 Ngày 1.\n- Nội dung: Canvas 7 dòng (hướng, job executor, pain 1 câu, evidence, lát cắt, automation, willing users).",
        "citation": "04-rubric.md §Phần 3"
    },
    "cp2": {
        "title": "Checkpoint 2 (Show thứ bấm được)",
        "keywords": ["cp2", "checkpoint 2", "bấm được", "mock", "sketch"],
        "content": "Khóa 3: 12:00 Ngày 1 | Khóa 4: 17:00 Ngày 1.\n- Nội dung: Flow chính bấm đi hết được (Sketch/Mock) + commit đầu tiên trên Repo.",
        "citation": "04-rubric.md §Phần 3"
    },
    "cp3": {
        "title": "Checkpoint 3 (AI thật + Đo lượt 1)",
        "keywords": ["cp3", "checkpoint 3", "ai thật", "golden set"],
        "content": "Khóa 3: 16:00 Ngày 1 | Khóa 4: 10:30 Ngày 2.\n- Nội dung: ≥1 lời gọi AI thật + Golden set ≥20 cases + bảng kết quả lượt 1.",
        "citation": "04-rubric.md §Phần 3"
    },
    "cp4": {
        "title": "Checkpoint 4 (Chốt tiến độ & Spec)",
        "keywords": ["cp4", "checkpoint 4", "spec", "hạn cứng"],
        "content": "Khóa 3: 17:30 Ngày 1 | Khóa 4: 12:00 Ngày 2.\n- ⏰ HẠN CỨNG SPEC: Commit spec.md trước 23:59 Ngày 1 (Quality bar chốt cố định từ mốc này).",
        "citation": "01-de-bai.md & 04-rubric.md"
    },
    "cp5": {
        "title": "Checkpoint 5 (Validation & Dry run)",
        "keywords": ["cp5", "checkpoint 5", "validation", "dry run", "slide"],
        "content": "Khóa 3: 09:00 Ngày 2 | Khóa 4: 14:00 Ngày 2.\n- Nội dung: Log user test ≥5 mẩu có tên + Changelog + Slide final + Dry run 5 phút.",
        "citation": "04-rubric.md §Phần 3"
    },
    "cp6": {
        "title": "Checkpoint 6 (Demo chính thức)",
        "keywords": ["cp6", "checkpoint 6", "demo", "thuyết trình"],
        "content": "Khóa 3: 10:00 Ngày 2 | Khóa 4: 15:00 Ngày 2.\n- Nội dung: 5 phút demo + 5 phút Q&A (Giám khảo chạy 1 case lạ tại chỗ).",
        "citation": "04-rubric.md §Phần 3"
    },
    "vlearn": {
        "title": "Nền tảng VLearn & Codelabs",
        "keywords": ["vlearn", "codelabs", "nộp bài", "link nộp", "bài tập", "trang web vlearn"],
        "content": "Trang học tập và nộp bài tại https://vlearn.dev và Codelabs tại https://codelabs.vlearn.dev.",
        "citation": "02-guide.md §Vlearn"
    },
    "slide_tai_lieu": {
        "title": "Slide Bài Giảng & Tài Nguyên Khóa Học",
        "keywords": ["slide", "bài giảng", "tài liệu", "slide bài giảng", "link slide"],
        "content": "Slide bài giảng và tài liệu học tập được cập nhật trực tiếp tại nền tảng VLearn (https://vlearn.dev) và các thông báo chính thức tại kênh Discord <#1531838822608797747>.",
        "citation": "02-guide.md §Tài liệu"
    },
    "ai-log": {
        "title": "Hướng dẫn Setup AI Log",
        "keywords": ["ai log", "git push", "pre-push", "lỗi git", "hook"],
        "content": "Cài đặt git pre-push hook theo hướng dẫn trong kênh <#1530270278301519974>. Kiểm tra file overview.txt trong `.system_generated/logs/`. Trên Windows/macOS: đảm bảo chạy lệnh agy cli trong Git Bash/PowerShell.",
        "citation": "02-guide.md §AI-Log"
    },
    "form_nghi_hoc": {
        "title": "Form Xin Nghỉ Phép & Chuyên Cần",
        "keywords": ["nghỉ", "xin nghỉ", "vắng mặt", "form nghỉ"],
        "content": "Học viên xin nghỉ phép điền form chính thức tại link BTC và gửi thông báo tới Lab Coach / TA (@LabCoach) để được duyệt.",
        "citation": "01-de-bai.md §Quy định chuyên cần"
    }
}

def memory_extractor_and_router_node(state: ChatbotState) -> Dict[str, Any]:
    messages = state.get("messages", [])
    if not messages:
        return {"intent": "LOGISTICS"}
    
    last_user_msg = messages[-1].get("content", "").lower().strip()
    user_id = state.get("user_id", "default_user")
    extracted_facts: List[UserFact] = list(state.get("extracted_user_facts", []))
    
    if memory_engine:
        stored_facts = memory_engine.remember_from_text(user_id, last_user_msg)
        for f in stored_facts:
            extracted_facts.append({
                "fact_type": str(f.get("fact_type")),
                "value": str(f.get("value")),
                "timestamp": str(f.get("created_at", "now"))
            })
    else:
        if "windows" in last_user_msg:
            extracted_facts.append({"fact_type": "OS", "value": "Windows", "timestamp": "now"})
        elif "mac" in last_user_msg or "macos" in last_user_msg:
            extracted_facts.append({"fact_type": "OS", "value": "macOS", "timestamp": "now"})
            
        group_match = re.search(r"g\d+|nhóm\s*\d+|team\s*\d+", last_user_msg)
        if group_match:
            extracted_facts.append({"fact_type": "GROUP", "value": group_match.group(0).upper(), "timestamp": "now"})

    out_keywords = ["đáp án", "giải hộ", "viết hộ", "cho xin code", "làm hộ", "bỏ qua quy định", "viết code", "code react"]
    if any(kw in last_user_msg for kw in out_keywords):
        return {
            "intent": "OUT_OF_SCOPE",
            "extracted_user_facts": extracted_facts
        }

    ambiguous_keywords = ["hạn nộp", "deadline", "mấy giờ nộp", "khi nào nộp", "hết hạn"]
    has_any_cp_mention = bool(re.search(r"cp\s*\d+|checkpoint\s*\d+", last_user_msg))
    if any(kw in last_user_msg for kw in ambiguous_keywords) and not has_any_cp_mention:
        return {
            "intent": "AMBIGUOUS",
            "extracted_user_facts": extracted_facts
        }

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

    if "lỗi" in last_user_msg or "bug" in last_user_msg or "ai log" in last_user_msg or "git push" in last_user_msg:
        return {
            "intent": "TECH_BUG",
            "extracted_user_facts": extracted_facts
        }

    return {
        "intent": "LOGISTICS",
        "extracted_user_facts": extracted_facts
    }

def kg_retriever_node(state: ChatbotState) -> Dict[str, Any]:
    messages = state.get("messages", [])
    last_user_msg = messages[-1].get("content", "").lower().strip() if messages else ""
    user_facts = state.get("extracted_user_facts", [])
    user_id = state.get("user_id", "default_user")
    
    if memory_engine:
        stored_user_facts = memory_engine.get_facts(user_id)
        for f in stored_user_facts:
            user_facts.append({
                "fact_type": str(f.get("fact_type")),
                "value": str(f.get("value")),
                "timestamp": str(f.get("created_at", "now"))
            })

    retrieved_parts = []
    citations = []
    
    user_os = next((f["value"] for f in reversed(user_facts) if f.get("fact_type") == "OS"), None)
    
    # 1. Tra cứu Graph Engine (nếu có)
    if graph_engine:
        entities = graph_engine.find_entities(last_user_msg, limit=5)
        for entity in entities:
            traversal = graph_engine.get_context(entity["id"], max_hops=2, limit=5)
            for path in traversal:
                for edge in path.get("edges", []):
                    subj = edge.get("subject")
                    rel = edge.get("relation")
                    obj = edge.get("object")
                    src = edge.get("source", "KGDB")
                    retrieved_parts.append(f"🌐 [Graph Triple]: ({subj}) -[:{rel}]-> ({obj})")
                    citations.append(f"KGDB ({src})")

    # 2. Match linh hoạt & Tổng hợp đa nguồn từ KNOWLEDGE_BASE
    for key, data in KNOWLEDGE_BASE.items():
        matched = False
        if key in last_user_msg or key.replace("-", " ") in last_user_msg:
            matched = True
        else:
            for kw in data.get("keywords", []):
                if kw in last_user_msg:
                    matched = True
                    break
                    
        if matched:
            content = data["content"]
            if key == "ai-log" and user_os:
                content += f"\n💡 [Ghi nhận hệ điều hành của bạn từ bộ nhớ: {user_os}]: Áp dụng hướng dẫn cài đặt git pre-push hook dành cho {user_os}."
            retrieved_parts.append(f"📌 **{data['title']}**:\n{content}")
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
    tool_name = state.get("target_tool", "web_search_tool")
    messages = state.get("messages", [])
    query = messages[-1].get("content", "") if messages else "Tra cứu"
    
    result = execute_tool_by_name(tool_name, query)
    return {
        "retrieved_context": result,
        "citations": [f"Tool Execution: {tool_name}"]
    }

def clarification_node(state: ChatbotState) -> Dict[str, Any]:
    response = (
        "❓ **[Cần làm rõ thông tin - HAX G10]**\n"
        "Bạn đang muốn tra cứu mốc deadline cho **Checkpoint mấy** (CP1 -> CP6) và thuộc **Khóa 3** hay **Khóa 4**?\n\n"
        "👉 *Gợi ý gõ*: `!hoi deadline CP4 khóa 4 khi nào?`"
    )
    return {
        "final_response": format_discord_channel_links(response),
        "citations": ["HAX G10 Guardrail"]
    }

def guardrail_refusal_node(state: ChatbotState) -> Dict[str, Any]:
    response = (
        "⚠️ **[Từ chối - Ngoài thẩm quyền HAX G8]**\n"
        "Trợ lý chỉ hỗ trợ tra cứu logistics, deadline và quy định khóa học.\n"
        "Bot không hỗ trợ giải bài tập cá nhân hay tự động viết code.\n"
        "Bạn hãy tham khảo slide bài giảng hoặc thảo luận cùng nhóm tại kênh <#1530221989157929090> nhé!"
    )
    return {
        "final_response": format_discord_channel_links(response),
        "citations": ["HAX G8 Scope Guardrail"]
    }

def answer_synthesizer_node(state: ChatbotState) -> Dict[str, Any]:
    """
    Node 6: AI Tutor Synthesizer mềm mại, linh hoạt và tổng hợp thông minh bằng Gemini LLM.
    """
    context = state.get("retrieved_context", "")
    citations = state.get("citations", [])
    messages = state.get("messages", [])
    user_query = messages[-1].get("content", "") if messages else ""
    
    # 1. Sử dụng Gemini LLM với System Prompt chuyên dụng làm Trợ lý AI học tập mềm mại
    if llm_client:
        try:
            system_prompt = (
                "Bạn là một Trợ lý AI Học tập (AI Tutor) vô cùng tinh tế, chu đáo và mềm mại cho khóa học AI Thực Chiến.\n"
                "Nhiệm vụ của bạn:\n"
                "1. Trả lời đúng trọng tâm câu hỏi của học viên bằng văn phong tự nhiên, lịch sự, ân cần như một người đồng hành thực thụ.\n"
                "2. Đừng dán khuôn mẫu thô cứng. Hãy tự tổng hợp lại các ý trong NGỮ CẢNH TRA CỨU bên dưới thành một câu trả lời mượt mà, dễ hiểu.\n"
                "3. Nếu học viên hỏi về Feedback / Góp ý VLearn: hãy chỉ rõ đường link/thread gửi QR feedback (<#1530052915383894107>) và giải thích lịch sự.\n"
                "4. Giữ nguyên định dạng link kênh Discord dạng <#ID> nếu có trong ngữ cảnh.\n\n"
                f"NGỮ CẢNH DỮ LIỆU TRA CỨU:\n{context}\n\n"
                f"CÂU HỎI CỦA HỌC VIÊN: {user_query}"
            )
            
            config = types.GenerateContentConfig(
                temperature=LLM_TEMPERATURE,
                top_p=0.95
            ) if types else None
            
            llm_response = llm_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=system_prompt,
                config=config
            )
            if llm_response and llm_response.text:
                citation_str = "\n".join([f"- *Nguồn: {c}*" for c in citations if c != "Không có nguồn"])
                if citation_str:
                    raw_resp = f"{llm_response.text.strip()}\n\n📌 **Trích dẫn minh bạch**:\n{citation_str}"
                else:
                    raw_resp = llm_response.text.strip()
                return {
                    "final_response": format_discord_channel_links(raw_resp),
                    "citations": citations
                }
        except Exception:
            pass

    # 2. Fallback Synthesizer
    if "Chưa tìm thấy căn cứ chính thức" in context:
        response = (
            "🔍 **[Chưa có căn cứ chính thức - HAX G10]**\n"
            "Hiện tại mình chưa tìm thấy thông tin chính thức của BTC về câu hỏi này.\n"
            "📩 Mình đã ghi nhận và chuyển câu hỏi tới các anh chị **Lab Coach / TA** (@LabCoach) để hỗ trợ bạn sớm nhất nhé!"
        )
    else:
        citation_str = "\n".join([f"- *Nguồn: {c}*" for c in citations])
        response = (
            f"🤖 **[Trợ lý Học viên AI]**\n\n"
            f"{context}\n\n"
            f"📌 **Trích dẫn minh bạch**:\n{citation_str}"
        )
        
    return {
        "final_response": format_discord_channel_links(response),
        "citations": citations
    }
