import re
import os
import json
from typing import Dict, Any, List
from src.agent.state import ChatbotState, UserFact
from src.agent.tools import execute_tool_by_name

# Map các tên kênh Discord sang Category ID Tag (<#ID>) chuẩn xác
DISCORD_CHANNEL_MAP = {
    "#🏆-chia-sẻ": "<#1527920185649008660>",
    "#chia-sẻ": "<#1527920185649008660>",
    "#🙋-hỏi-đáp": "<#1530221989157929090>",
    "#hỏi-đáp": "<#1530221989157929090>",
    "#💬-chung": "<#1527920177390293164>",
    "#chung": "<#1527920177390293164>",
    "#📖-bài-học": "<#1531838822608797747>",
    "#bài-học": "<#1531838822608797747>",
    "#feedback-vlearn": "<#1530052915383894107>"
}

def format_discord_channel_links(text: str) -> str:
    """Tự động chuyển đổi tên kênh dạng #tên-kênh sang định dạng link bấm được của Discord (<#ID>)."""
    for name, channel_tag in DISCORD_CHANNEL_MAP.items():
        text = text.replace(name, channel_tag)
    return text

# 1. Tích hợp Gemini LLM SDK (google-genai) & Cấu hình Model
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

LLM_MODEL = os.getenv("LLM_MODEL", "gemma-4-26b-a4b-it")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))

# 2. Tích hợp Graph DB, Extracted Triples & Memory Store
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
CRAWL_DIR = os.path.join(DATA_DIR, "data", "discord-crawl")
TRIPLES_PATH = os.path.join(DATA_DIR, "extracted_triples.json")

try:
    from src.graph_db.memory_store import MemoryStore
    from src.graph_db.graph_store import GraphStore
    
    memory_store_path = os.path.join(DATA_DIR, "memory_store.json")
    graph_store_path = os.path.join(DATA_DIR, "graph_store.json")
    
    memory_engine = MemoryStore(memory_store_path)
    graph_engine = GraphStore(graph_store_path) if os.path.exists(graph_store_path) else None
    
    if graph_engine and os.path.exists(TRIPLES_PATH) and len(graph_engine.graph.nodes) == 0:
        graph_engine.import_file(TRIPLES_PATH)
        graph_engine.save()
except Exception:
    memory_engine = None
    graph_engine = None

STOP_WORDS = {
    "trong", "có", "mát", "không", "là", "thế", "nào", "mình", "bạn", "với", "cho",
    "được", "này", "đó", "gì", "ở", "về", "vẫn", "phải", "như", "mấy", "bao",
    "nhiêu", "tại", "sao", "thì", "cái", "ai", "bên", "rồi", "lại", "đang", "cũng", "đều"
}

def query_extracted_triples(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Tra cứu trực tiếp dữ liệu từ file data/extracted_triples.json bằng thuật toán matching từ khóa."""
    if not os.path.exists(TRIPLES_PATH):
        return []
    
    query_lower = query.lower().replace("anti gravity", "antigravity")
    keywords = [w for w in re.findall(r"\w+", query_lower) if len(w) > 1 and w not in STOP_WORDS]
    if not keywords:
        return []
        
    matched_triples = []
    try:
        with open(TRIPLES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        triples = data.get("triples", [])
        for t in triples:
            subj = str(t.get("subject", "")).lower()
            rel = str(t.get("relation", "")).lower()
            obj = str(t.get("object", "")).lower()
            
            score = 0
            for kw in keywords:
                if kw in subj:
                    score += 4
                if kw in rel:
                    score += 2
                if kw in obj:
                    score += 3
                    
            if score >= 5:
                attrs = t.get("attributes", {})
                proof = attrs.get("proof_document") or attrs.get("thread_id") or "Knowledge Graph"
                matched_triples.append((score, {
                    "subject": t.get("subject"),
                    "relation": t.get("relation"),
                    "object": t.get("object"),
                    "proof": proof
                }))
                
        matched_triples.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in matched_triples[:limit]]
    except Exception:
        return []

def search_discord_crawl_data(query: str, limit: int = 1) -> List[Dict[str, str]]:
    """Tra cứu thông minh bằng Relevance Scoring trên 285 file crawl thô để tìm ĐÚNG 1 Thread chuẩn xác nhất."""
    if not CRAWL_DIR or not os.path.exists(CRAWL_DIR):
        return []
    
    query_lower = query.lower().replace("anti gravity", "antigravity")
    keywords = [w for w in re.findall(r"\w+", query_lower) if len(w) > 1 and w not in STOP_WORDS]
    if not keywords:
        return []
        
    scored_files = []
    try:
        files = os.listdir(CRAWL_DIR)
        for fname in files:
            if not fname.endswith(".json"):
                continue
            
            fname_clean = fname.lower().replace("anti gravity", "antigravity")
            score = 0
            
            for kw in keywords:
                if kw in fname_clean:
                    score += 5
                    
            if "miễn phí" in query_lower or "free" in query_lower or "công cụ" in query_lower:
                if "free" in fname_clean or "miễn phí" in fname_clean or "công cụ" in fname_clean:
                    score += 15
            if "rag" in query_lower and "rag" in fname_clean:
                score += 15
            if "cấu trúc" in query_lower or "thư mục" in query_lower:
                if "cấu trúc" in fname_clean or "thư mục" in fname_clean:
                    score += 15
            if "macos" in query_lower and "macos" in fname_clean:
                score += 15
            if "windows" in query_lower and "windows" in fname_clean:
                score += 15
            if "antigravity" in query_lower and "antigravity" in fname_clean:
                score += 15
            if "git push" in query_lower and "git push" in fname_clean:
                score += 10
                
            fpath = os.path.join(CRAWL_DIR, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                channel_info = data.get("channel", {})
                thread_id = channel_info.get("id")
                thread_name = channel_info.get("name", fname.replace(".json", ""))
                messages = data.get("messages", [])
                first_msg = messages[0].get("content", "") if messages else ""
                author_info = messages[0].get("author", {}) if messages else {}
                author_name = author_info.get("nickname") or author_info.get("name", "Học viên")
                
                msg_lower = first_msg.lower()
                for kw in keywords:
                    if kw in msg_lower:
                        score += 2
                        
                if score >= 12:
                    snippet = first_msg[:400].strip() if first_msg else ""
                    scored_files.append((score, {
                        "title": thread_name,
                        "thread_id": thread_id,
                        "author": author_name,
                        "content": snippet,
                        "citation": f"Thread <#{thread_id}> (bởi {author_name})"
                    }))
            except Exception:
                continue
                    
        scored_files.sort(key=lambda x: x[0], reverse=True)
        results = [item[1] for item in scored_files[:limit]]
    except Exception:
        results = []
        
    return results

# Knowledge Base chính thức mở rộng từ BTC với Citation dạng Link Discord Tag chính xác
KNOWLEDGE_BASE = {
    "free_coding_agents": {
        "title": "Các Công Cụ Code Tích Hợp AI Miễn Phí (Free Coding Agents)",
        "keywords": ["công cụ code ai miễn phí", "ai coding miễn phí", "free coding agents", "công cụ ai miễn phí", "code ai miễn phí", "công cụ code tích hợp ai"],
        "content": "Danh sách các công cụ AI coding miễn phí nổi bật được chia sẻ bởi học viên !G18-T058-Nguyễn Duy Bách-01844:\n1. Cursor: Miễn phí thử nghiệm với GPT-4o-mini & Claude-3.5-haiku.\n2. Windsurf (Codeium): Miễn phí AI Flow & Tab Autocomplete.\n3. GitHub Copilot: Miễn phí cho Học sinh/Sinh viên qua GitHub Student Pack.\n4. Antigravity IDE (Gemini Code Assist): Miễn phí kết nối API token cá nhân.\n5. OpenCode AI & Kiro AI: Tích hợp mã nguồn mở cho VS Code.",
        "citation": "Thread <#1531559503785496676> (bởi !G18-T058-Nguyễn Duy Bách-01844)"
    },
    "cau_truc_rag": {
        "title": "Cấu trúc Thư mục Dự án RAG Chuẩn Production",
        "keywords": ["cấu trúc rag", "thư mục rag", "rag production", "cấu trúc dự án rag", "cấu trúc thư mục"],
        "content": "Cấu trúc thư mục RAG chuẩn Production được chia sẻ bởi học viên T054-Lê Nguyễn Minh Quang-01248:\n- Root: requirements.txt, .env, config.yaml, README.md\n- Xử lý dữ liệu: src/ingestion/, src/chunking/, src/embeddings/\n- Lưu trữ & Truy xuất: src/vectordb/, src/retrieval/\n- LLM Core: src/prompts/, src/llm/\n- API & Utils: src/api/, src/utils/\n- Log & Test: tests/, logs/\nXem chi tiết tại Thread: <#1531322415395901522>.",
        "citation": "Thread <#1531322415395901522> (bởi T054-Lê Nguyễn Minh Quang-01248)"
    },
    "antigravity_fix": {
        "title": "Fix Lỗi AI Log Antigravity IDE (No new prompts / overview.txt)",
        "keywords": ["antigravity", "anti gravity", "agy", "log_antigravity", "fix antigravity", "lỗi antigravity", "brain dir", "transcript.jsonl"],
        "content": "Cách sửa lỗi Antigravity IDE báo 'No new prompts' / không tìm thấy transcript.jsonl:\n1. Antigravity IDE lưu log tại thư mục `.system_generated\\logs\\overview.txt` thay vì `transcript.jsonl`.\n2. Cập nhật script `log_antigravity.py` chỉ hướng đọc file `overview.txt` hoặc dùng `agy` CLI lệnh fix.\n3. Xem hướng dẫn chi tiết tại Thread: <#1531490593543553247> (Kênh <#1527920185649008660>).",
        "citation": "Thread <#1531490593543553247>"
    },
    "feedback_vlearn": {
        "title": "Kênh Feedback & Báo Lỗi VLearn / Codelabs",
        "keywords": ["feedback", "góp ý", "báo lỗi vlearn", "báo lỗi codelabs", "qr feedback", "ý kiến vlearn"],
        "content": "Để gửi feedback góp ý hoặc báo lỗi UI/UX trên hệ thống VLearn/Codelabs:\n1. Quét mã QR Feedback tại Thread chính thức: <#1530052915383894107> (do Lab Coach Trần Hoàng Hà đăng tại kênh #🙋-hỏi-đáp).\n2. Hoặc gửi bài phản hồi trực tiếp tại thread 'Feedback, bug report vlearn.dev' <#1530226830920126505>.",
        "citation": "Thread <#1530052915383894107>"
    },
    "gioi_thieu_khoa_hoc": {
        "title": "Tổng Quan Chương Trình AI Thực Chiến (AI20K Build Phase)",
        "keywords": ["ai thực chiến", "chương trình ai thực chiến", "khóa học ai thực chiến", "giới thiệu chương trình", "khoá học", "chương trình"],
        "content": "Chương trình AI Thực Chiến (Cohort 3 & 4) là khóa huấn luyện phát triển sản phẩm AI thực tế. Học viên được chia nhóm, thực hiện bài tập Lab và vượt qua 6 mốc Checkpoint (CP1 -> CP6) từ lập Canvas, Mockup UI, gọi AI API thật, hoàn thiện AI Spec đến Demo sản phẩm trước Giám khảo.",
        "citation": "Tài liệu 01-de-bai.md & 02-guide.md"
    },
    "cp1": {
        "title": "Checkpoint 1 (Canvas)",
        "keywords": ["cp1", "checkpoint 1", "canvas"],
        "content": "Khóa 3: 10:00 Ngày 1 | Khóa 4: 15:00 Ngày 1.\n- Nội dung: Canvas 7 dòng (hướng, job executor, pain 1 câu, evidence, lát cắt, automation, willing users).",
        "citation": "Quy định Rubric 04-rubric.md"
    },
    "cp2": {
        "title": "Checkpoint 2 (Show thứ bấm được)",
        "keywords": ["cp2", "checkpoint 2", "bấm được", "mock", "sketch"],
        "content": "Khóa 3: 12:00 Ngày 1 | Khóa 4: 17:00 Ngày 1.\n- Nội dung: Flow chính bấm đi hết được (Sketch/Mock) + commit đầu tiên trên Repo.",
        "citation": "Quy định Rubric 04-rubric.md"
    },
    "cp3": {
        "title": "Checkpoint 3 (AI thật + Đo lượt 1)",
        "keywords": ["cp3", "checkpoint 3", "ai thật", "golden set"],
        "content": "Khóa 3: 16:00 Ngày 1 | Khóa 4: 10:30 Ngày 2.\n- Nội dung: ≥1 lời gọi AI thật + Golden set ≥20 cases + bảng kết quả lượt 1.",
        "citation": "Quy định Rubric 04-rubric.md"
    },
    "cp4": {
        "title": "Checkpoint 4 (Chốt tiến độ & Spec)",
        "keywords": ["cp4", "checkpoint 4", "spec", "hạn cứng"],
        "content": "Khóa 3: 17:30 Ngày 1 | Khóa 4: 12:00 Ngày 2.\n- ⏰ HẠN CỨNG SPEC: Commit spec.md trước 23:59 Ngày 1 (Quality bar chốt cố định từ mốc này).",
        "citation": "Quy định Rubric 04-rubric.md"
    },
    "cp5": {
        "title": "Checkpoint 5 (Validation & Dry run)",
        "keywords": ["cp5", "checkpoint 5", "validation", "dry run", "slide"],
        "content": "Khóa 3: 09:00 Ngày 2 | Khóa 4: 14:00 Ngày 2.\n- Nội dung: Log user test ≥5 mẩu có tên + Changelog + Slide final + Dry run 5 phút.",
        "citation": "Quy định Rubric 04-rubric.md"
    },
    "cp6": {
        "title": "Checkpoint 6 (Demo chính thức)",
        "keywords": ["cp6", "checkpoint 6", "demo", "thuyết trình"],
        "content": "Khóa 3: 10:00 Ngày 2 | Khóa 4: 15:00 Ngày 2.\n- Nội dung: 5 phút demo + 5 phút Q&A (Giám khảo chạy 1 case lạ tại chỗ).",
        "citation": "Quy định Rubric 04-rubric.md"
    },
    "vlearn": {
        "title": "Nền tảng VLearn & Codelabs",
        "keywords": ["vlearn", "codelabs", "nộp bài", "link nộp", "bài tập", "trang web vlearn"],
        "content": "Trang học tập và nộp bài tại https://vlearn.dev và Codelabs tại https://codelabs.vlearn.dev.",
        "citation": "Hệ thống VLearn"
    },
    "slide_tai_lieu": {
        "title": "Slide Bài Giảng & Tài Nguyên Khóa Học",
        "keywords": ["slide", "bài giảng", "tài liệu", "slide bài giảng", "link slide"],
        "content": "Slide bài giảng và tài liệu học tập được cập nhật trực tiếp tại nền tảng VLearn (https://vlearn.dev) và các thông báo chính thức tại kênh Discord <#1531838822608797747>.",
        "citation": "Kênh <#1531838822608797747>"
    },
    "ai-log": {
        "title": "Hướng dẫn Setup AI Log",
        "keywords": ["cách setup ai log", "hướng dẫn ai log", "pre-push hook setup"],
        "content": "Cài đặt git pre-push hook theo hướng dẫn chi tiết tại kênh <#1527920185649008660>. Kiểm tra file overview.txt trong `.system_generated/logs/`. Trên Windows/macOS: đảm bảo chạy lệnh agy cli trong Git Bash/PowerShell.",
        "citation": "Kênh <#1527920185649008660>"
    },
    "form_nghi_hoc": {
        "title": "Form Xin Nghỉ Phép & Chuyên Cần",
        "keywords": ["nghỉ", "xin nghỉ", "vắng mặt", "form nghỉ"],
        "content": "Học viên xin nghỉ phép điền form chính thức tại link BTC và gửi thông báo tới Lab Coach / TA (@LabCoach) để được duyệt.",
        "citation": "Quy định Chuyên cần"
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

    out_keywords = [
        "đáp án", "giải hộ", "viết hộ", "cho xin code", "làm hộ", "bỏ qua quy định", "viết code", "code react",
        "mặt trời", "mát không", "thời tiết", "ăn gì", "chữa thất tình", "yêu đương", "bóng đá", "thể thao",
        "tin tức", "xổ số", "giá vàng", "chứng khoán", "game", "chơi game", "hát", "thơ"
    ]
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
    if "checklist" in last_user_msg or "cần làm gì" in last_user_msg or "cần chuẩn bị gì" in last_user_msg:
        return {
            "intent": "EXECUTE_TOOL",
            "target_tool": "cp_checklist_tool",
            "extracted_user_facts": extracted_facts
        }
    if "báo ta" in last_user_msg or "chuyển ta" in last_user_msg or "gọi ta" in last_user_msg or "gọi coach" in last_user_msg or "cần ta hỗ trợ" in last_user_msg:
        return {
            "intent": "EXECUTE_TOOL",
            "target_tool": "ta_escalation_tool",
            "extracted_user_facts": extracted_facts
        }
    if "bản tin" in last_user_msg or "top faq" in last_user_msg or "thống kê hôm nay" in last_user_msg:
        return {
            "intent": "EXECUTE_TOOL",
            "target_tool": "daily_digest_tool",
            "extracted_user_facts": extracted_facts
        }

    if "lỗi" in last_user_msg or "bug" in last_user_msg or "ai log" in last_user_msg or "git push" in last_user_msg or "antigravity" in last_user_msg or "anti gravity" in last_user_msg or "fix" in last_user_msg:
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
    
    # 1. Tra cứu trực tiếp từ data/extracted_triples.json
    extracted_triples = query_extracted_triples(last_user_msg, limit=3)
    for t in extracted_triples:
        retrieved_parts.append(f"🌐 [Knowledge Graph Triple]: ({t['subject']}) -[:{t['relation']}]-> ({t['object']})")
        citations.append(f"KG ({t['proof']})")

    # 2. Tra cứu Knowledge Base chính thức
    normalized_query = last_user_msg.replace("anti gravity", "antigravity")
    for key, data in KNOWLEDGE_BASE.items():
        matched = False
        if key in normalized_query or key.replace("-", " ") in normalized_query:
            matched = True
        else:
            for kw in data.get("keywords", []):
                if kw in normalized_query or kw in last_user_msg:
                    matched = True
                    break
                    
        if matched:
            content = data["content"]
            if ("ai-log" in key or "antigravity" in key) and user_os:
                content += f"\n💡 [Ghi nhận hệ điều hành của bạn từ bộ nhớ: {user_os}]: Áp dụng hướng dẫn cài đặt git pre-push hook dành cho {user_os}."
            retrieved_parts.append(f"📌 **{data['title']}**:\n{content}")
            citations.append(data["citation"])

    # 3. Tra cứu trực tiếp 285 file Crawl thô khi chưa có fake CP
    has_fake_cp = any(f"cp{i}" in normalized_query or f"checkpoint {i}" in normalized_query for i in range(7, 20))
    if not has_fake_cp:
        crawl_matches = search_discord_crawl_data(last_user_msg, limit=1)
        for c in crawl_matches:
            retrieved_parts.append(f"💬 **[Thảo luận Discord]: {c['title']}** (bởi {c.get('author', 'Học viên')})\n{c['content']}")
            citations.append(c["citation"])
            
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
        "citations": citations
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
        "☀️ **[Trợ lý Học viên AI - Ngoài Phạm Vi Khóa Học]**\n\n"
        "Chào bạn, mình rất hiểu sự tò mò của bạn!\n"
        "Tuy nhiên, mình là **Trợ lý Học viên chuyên trách cho khóa học AI Thực Chiến**, nên chỉ hỗ trợ các thông tin nằm trong phạm vi khóa học như:\n"
        "1. 📅 **Hạn nộp & Yêu cầu Checkpoint**: CP1 đến CP6 (Ví dụ: `!hoi hạn nộp CP4 khi nào?`)\n"
        "2. 🛠️ **Sửa lỗi kỹ thuật**: Lỗi AI Log, Git pre-push hook, Antigravity IDE, RAG...\n"
        "3. 📖 **Quy định & Tài liệu**: VLearn, Codelabs, Slide bài giảng, Form xin nghỉ phép...\n\n"
        "Nếu bạn có bất kỳ thắc mắc nào liên quan đến bài học và quy định trên, mình luôn sẵn sàng đồng hành hỗ trợ nhé! 😊"
    )
    return {
        "final_response": format_discord_channel_links(response),
        "citations": []
    }

def answer_synthesizer_node(state: ChatbotState) -> Dict[str, Any]:
    """
    Node 6: AI Tutor Synthesizer minh bạch (HAX G2) - Tuyệt đối không sinh chuỗi placeholder thô dạng <#ID_THREAD>.
    """
    context = state.get("retrieved_context", "")
    raw_citations = state.get("citations", [])
    messages = state.get("messages", [])
    user_query = messages[-1].get("content", "") if messages else ""
    
    citations = list(dict.fromkeys(raw_citations))
    
    best_citation = None
    thread_citations = [c for c in citations if "Thread <#" in c]
    kb_citations = [c for c in citations if "Thread <#" not in c and "Không có nguồn" not in c and "Guardrail" not in c]
    
    if thread_citations:
        best_citation = thread_citations[0]
    elif kb_citations:
        best_citation = kb_citations[0]

    if llm_client:
        try:
            system_prompt = (
                "Bạn là một Trợ lý AI Học tập (AI Tutor) vô cùng tinh tế, chu đáo và minh bạch cho khóa học AI Thực Chiến.\n"
                "QUY TẮC PHÂN LOẠI NGUỒN VÀ TRÁNH PLACEHOLDER (HAX G2 TRANSPARENCY):\n"
                "1. NẾU NGUỒN LÀ BÀI VIẾT / CHIA SẺ CỦA HỌC VIÊN:\n"
                "   -> BẮT BUỘC mở đầu bằng: 'Dưới đây là phần chia sẻ kinh nghiệm của học viên [Tên Học Viên trong ngữ cảnh]...'\n"
                "   -> TUYỆT ĐỐI KHÔNG ghi các từ placeholder mẫu như '<#ID_THREAD>' hay '<#ID...>' vào thân bài trả lời.\n"
                "2. NẾU NGUỒN LÀ TÀI LIỆU CHÍNH THỨC CỦA BTC HOẶC LAB COACH:\n"
                "   -> Trình bày trực tiếp là quy định/thông tin chính thức từ BTC.\n"
                "3. CHỈ NÓI 'Chưa tìm thấy căn cứ chính thức' KHI VÀ CHỈ KHI trong ngữ cảnh hoàn toàn KHÔNG CÓ dữ liệu.\n"
                "4. Giữ văn phong lịch sự, ấm áp, mạch lạc.\n\n"
                f"NGỮ CẢNH DỮ LIỆU TRA CỨU:\n{context}\n\n"
                f"CÂU HỎI CỦA HỌC VIÊN: {user_query}"
            )
            
            config = types.GenerateContentConfig(
                temperature=LLM_TEMPERATURE,
                top_p=0.95
            ) if types else None
            
            try:
                llm_response = llm_client.models.generate_content(
                    model=LLM_MODEL,
                    contents=system_prompt,
                    config=config
                )
            except Exception:
                llm_response = llm_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=system_prompt,
                    config=config
                )
                
            if llm_response and llm_response.text:
                clean_text = llm_response.text.strip().replace("<#ID_THREAD>", "").replace("<#ID...>", "")
                if best_citation and best_citation != "Không có nguồn" and "Guardrail" not in best_citation:
                    raw_resp = f"{clean_text}\n\n📌 **Trích dẫn minh bạch**:\n- *Nguồn chính xác: {best_citation}*"
                else:
                    raw_resp = clean_text
                return {
                    "final_response": format_discord_channel_links(raw_resp),
                    "citations": [best_citation] if best_citation else []
                }
        except Exception:
            pass

    if "Chưa tìm thấy căn cứ chính thức" in context:
        response = (
            "🔍 **[Chưa có căn cứ chính thức - HAX G10]**\n"
            "Hiện tại mình chưa tìm thấy thông tin chính thức của BTC về câu hỏi này.\n"
            "📩 Mình đã ghi nhận và chuyển câu hỏi tới các anh chị **Lab Coach / TA** (@LabCoach) để hỗ trợ bạn sớm nhất nhé!"
        )
    else:
        citation_str = f"\n\n📌 **Trích dẫn minh bạch**:\n- *Nguồn chính xác: {best_citation}*" if best_citation and "Guardrail" not in best_citation else ""
        response = (
            f"🤖 **[Trợ lý Học viên AI]**\n\n"
            f"{context}"
            f"{citation_str}"
        )
        
    return {
        "final_response": format_discord_channel_links(response),
        "citations": [best_citation] if best_citation else []
    }
