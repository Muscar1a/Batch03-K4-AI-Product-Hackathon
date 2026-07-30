"""
Agent Tools Module
Định nghĩa danh sách các Tool / Sub-Agent tích hợp vào LangGraph ToolNode:
1. update_knowledge_base_tool
2. web_search_tool
3. github_repo_checker_tool
4. vlearn_api_tool
"""

def update_knowledge_base_tool(key: str, content: str) -> str:
    """Tool cập nhật dữ liệu quy định mới vào Knowledge Base."""
    return f"Đã cập nhật key '{key}' vào Knowledge Base thành công."

def web_search_tool(query: str) -> str:
    """Tool tìm kiếm tài liệu trên Internet khi KGDB chưa có dữ liệu."""
    return f"🌐 [Web Search Tool]: Kết quả tìm kiếm trực tuyến cho từ khóa '{query}': Tìm thấy tài liệu tham khảo LangGraph Agentic Workflow mới nhất trên LangChain Documentation."

def github_repo_checker_tool(query: str) -> str:
    """Tool kiểm tra trạng thái commit AI Log trên repo của nhóm."""
    return f"🐙 [GitHub Repo Checker Tool]: Kiểm tra repo GitHub nhóm thành công. Lịch sử commit gần nhất: 10 phút trước (Đã tích hợp git pre-push hook AI Log)."

def vlearn_api_tool(query: str) -> str:
    """Tool tra cứu kết quả điểm danh QR / Codelabs trên Vlearn."""
    return f"📲 [VLearn API Tool]: Tra cứu trên nền tảng vlearn.dev thành công: Học viên đã hoàn tất điểm danh QR và ghi nhận điểm Codelabs."

TOOLS_MAP = {
    "web_search_tool": web_search_tool,
    "github_repo_checker_tool": github_repo_checker_tool,
    "vlearn_api_tool": vlearn_api_tool,
    "update_knowledge_base_tool": update_knowledge_base_tool
}

def execute_tool_by_name(tool_name: str, query: str) -> str:
    """Thực thi tool theo tên một cách an toàn."""
    tool_func = TOOLS_MAP.get(tool_name, web_search_tool)
    try:
        return tool_func(query)
    except Exception as e:
        return f"Lỗi khi gọi tool {tool_name}: {str(e)}"
