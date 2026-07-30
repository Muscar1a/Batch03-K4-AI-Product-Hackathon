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
    return f"Kết quả tìm kiếm web cho '{query}': [Dữ liệu giả lập]"

def github_repo_checker_tool(group_id: str) -> str:
    """Tool kiểm tra trạng thái commit AI Log trên repo của nhóm."""
    return f"Repo nhóm {group_id} đã commit AI Log gần nhất 10 phút trước."

def vlearn_api_tool(user_id: str) -> str:
    """Tool tra cứu kết quả điểm danh QR / Codelabs trên Vlearn."""
    return f"Học viên {user_id} đã hoàn thành điểm danh Codelabs."
