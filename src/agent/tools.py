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

# Registry mapping tool names to functions
TOOLS_MAP = {
    "web_search_tool": web_search_tool,
    "github_repo_checker_tool": github_repo_checker_tool,
    "vlearn_api_tool": vlearn_api_tool,
    "update_knowledge_base_tool": update_knowledge_base_tool
}

def execute_tool_by_name(tool_name: str, query: str) -> str:
    """Hàm wrapper hỗ trợ gọi tool an toàn theo tên."""
    if tool_name in TOOLS_MAP:
        return TOOLS_MAP[tool_name](query)
    return f"⚠️ Tool '{tool_name}' không tồn tại trong hệ thống."
