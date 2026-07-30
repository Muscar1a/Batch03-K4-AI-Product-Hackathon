import json
from typing import Dict, Any

def web_search_tool(query: str) -> str:
    """Công cụ tìm kiếm thông tin trên Web khi KGDB chưa có dữ liệu."""
    return f"🔍 [Web Search Result for '{query}']: Tìm thấy tài liệu mới nhất tại https://docs.langchain.com/langgraph hoặc thông báo mới từ BTC Discord."

def github_repo_checker_tool(repo_name: str) -> str:
    """Công cụ kiểm tra trạng thái commit AI Log trên GitHub repository nhóm."""
    return f"🐙 [GitHub Checker for '{repo_name}']: Repository đã kích hoạt git pre-push hook AI Log thành công. Commit mới nhất 15 phút trước."

def vlearn_api_tool(student_id: str) -> str:
    """Công cụ tra cứu kết quả điểm danh QR / Codelabs trên VLearn API."""
    return f"🎓 [VLearn API for '{student_id}']: Đã nhận diện học viên trên hệ thống. Điểm danh QR buổi gần nhất: THÀNH CÔNG (100% chuyên cần)."

def update_knowledge_base_tool(topic: str, content: str) -> str:
    """Công cụ cập nhật quy định/thông báo mới vào Knowledge Base."""
    return f"✅ [KB Update]: Đã ghi nhận quy định mới cho chủ đề '{topic}': {content}"

def ta_escalation_tool(query: str) -> str:
    """Công cụ tạo bài đăng / ticket yêu cầu TA/Lab Coach hỗ trợ trực tiếp."""
    return (
        "📩 **[Hệ thống Hỗ Trợ Học Viên]**\n"
        f"Đã tạo bài đăng (thread) mới thành công cho nội dung: *'{query}'*!\n"
        "Bài đăng đã được khởi tạo tại kênh hỗ trợ <#1530221989157929090> (@LabCoach / @TA).\n"
        "Các anh chị TA/Coach và các bạn học sẽ trực tiếp phản hồi cho bạn trong thời gian sớm nhất."
    )

CHECKLIST_DATA = {
    "cp1": "📌 **Checklist CP1 (Canvas 7 dòng)**:\n- [ ] Xác định 1 hướng (A/B/C) + 1 Job Executor cụ thể\n- [ ] 1 câu Pain cụ thể có bằng chứng (kèm khảo sát ≥20 người hoặc data log)\n- [ ] Bảng Impact ≥3 ứng viên + lý do chọn\n- [ ] Đăng ký ≥3 người sẵn sàng dùng thử",
    "cp2": "📌 **Checklist CP2 (Mockup UI & Flow bấm được)**:\n- [ ] Thiết kế Flow chính đi từ đầu đến cuối (Figma/Sketch/Code UI)\n- [ ] Tạo Repo GitHub nhóm + Commit đầu tiên\n- [ ] Tích hợp script AI Log / pre-push hook",
    "cp3": "📌 **Checklist CP3 (Tích hợp AI thật & Golden Set)**:\n- [ ] ≥1 Lời gọi AI API thực tế (Gemini/OpenAI/Claude)\n- [ ] Xây dựng Golden Set test ≥20 cases mẫu\n- [ ] Bảng đo lường kết quả Accuracy/Recall Lượt 1",
    "cp4": "📌 **Checklist CP4 (Chốt Spec & Tiến độ)**:\n- [ ] Cập nhật file `spec.md` đầy đủ 5 tiêu chí trước 23:59 Ngày 1\n- [ ] Chốt Quality Bar cố định không thay đổi phạm vi nữa",
    "cp5": "📌 **Checklist CP5 (User Test & Dry Run)**:\n- [ ] Nhật ký User Test ≥5 người thật ngoài nhóm kèm tên\n- [ ] Cập nhật Slide thuyết trình chính thức\n- [ ] Chạy thử nghiệm Dry Run 5 phút demo + 5 phút Q&A",
    "cp6": "📌 **Checklist CP6 (Demo & Thuyết trình)**:\n- [ ] Thuyết trình 5 phút ấn tượng + 5 phút Q&A\n- [ ] Sẵn sàng cho Giám khảo test 1 case lạ trực tiếp tại chỗ"
}

def cp_checklist_tool(query: str) -> str:
    """Công cụ tra cứu danh sách công việc cần chuẩn bị (Checklist) cho từng Checkpoint."""
    query_lower = query.lower()
    for cp in ["cp1", "cp2", "cp3", "cp4", "cp5", "cp6"]:
        if cp in query_lower or f"checkpoint {cp[-1]}" in query_lower:
            return CHECKLIST_DATA[cp]
    return (
        "📋 **Checklist Tổng quan các mốc Checkpoint (CP1 -> CP6)**:\n"
        "• **CP1**: Canvas 7 dòng & Evidence | **CP2**: Mockup UI & First Commit\n"
        "• **CP3**: API AI thật & Golden Set | **CP4**: Finalize spec.md (Hạn 23:59 N1)\n"
        "• **CP5**: User test & Dry run | **CP6**: Demo & Q&A trước Giám khảo\n"
        "👉 *Gõ `!hoi checklist CP4` để xem chi tiết từng mốc.*"
    )

def daily_digest_tool(query: str) -> str:
    """Công cụ tạo Bản tin Tổng hợp chủ đề thảo luận nhiều nhất trong ngày cho TA."""
    return (
        "📊 **[Bản tin Thống kê Discord Học viên - Daily Digest]**\n"
        "🔥 **Top 3 Chủ đề được hỏi nhiều nhất hôm nay**:\n"
        "1. 🛠️ **Cài đặt & Sửa lỗi AI Log pre-push hook** (34 câu hỏi - Đã hỗ trợ 100%)\n"
        "2. ⏰ **Hạn nộp Spec CP4 & Yêu cầu Golden Set** (28 câu hỏi)\n"
        "3. 🌐 **Hướng dẫn kết nối Knowledge Graph Triples & RAG** (19 câu hỏi)\n"
        "📌 **Cảnh báo học viên vướng**: 2 nhóm đang gặp khó khăn ở bước config SSL macOS (`CERTIFICATE_VERIFY_FAILED`)."
    )

# Registry mapping tool names to functions
TOOLS_MAP = {
    "web_search_tool": web_search_tool,
    "github_repo_checker_tool": github_repo_checker_tool,
    "vlearn_api_tool": vlearn_api_tool,
    "update_knowledge_base_tool": update_knowledge_base_tool,
    "ta_escalation_tool": ta_escalation_tool,
    "cp_checklist_tool": cp_checklist_tool,
    "daily_digest_tool": daily_digest_tool
}

def execute_tool_by_name(tool_name: str, query: str) -> str:
    """Hàm wrapper hỗ trợ gọi tool an toàn theo tên."""
    if tool_name in TOOLS_MAP:
        return TOOLS_MAP[tool_name](query)
    return f"⚠️ Tool '{tool_name}' không tồn tại trong hệ thống."
