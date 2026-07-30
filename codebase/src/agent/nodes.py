"""
LangGraph Nodes Processing Module.
Chứa các Node xử lý chính trong State Machine:
1. memory_extractor_and_router_node
2. kg_retriever_node
3. tool_execution_node
4. answer_synthesizer_node
"""

from typing import Dict, Any
from .state import ChatbotState

def memory_extractor_and_router_node(state: ChatbotState) -> Dict[str, Any]:
    """
    Node 1: Phân tích tin nhắn mới phát hiện Facts cá nhân (OS, Group, Issue) 
    và phân loại Intent câu hỏi.
    """
    messages = state.get("messages", [])
    last_message = messages[-1]["content"] if messages else ""
    
    # Logic sơ bộ phân loại intent
    intent = "LOGISTICS"
    if "lỗi" in last_message.lower() or "bug" in last_message.lower():
        intent = "TECH_BUG"
    elif "tìm" in last_message.lower() or "search" in last_message.lower():
        intent = "EXECUTE_TOOL"
        
    return {
        "intent": intent,
        "extracted_user_facts": []
    }

def kg_retriever_node(state: ChatbotState) -> Dict[str, Any]:
    """
    Node 2: Truy vấn Knowledge Graph DB đa chặng dựa trên hồ sơ User & câu hỏi.
    """
    return {
        "retrieved_context": "Thông tin tra cứu từ KGDB...",
        "kg_triples": []
    }

def tool_execution_node(state: ChatbotState) -> Dict[str, Any]:
    """
    Node 3: Thực thi các Tool (Web search, Update KB, Git Check API...).
    """
    return {
        "retrieved_context": "Kết quả thực thi Tool..."
    }

def answer_synthesizer_node(state: ChatbotState) -> Dict[str, Any]:
    """
    Node 4: Tổng hợp thông tin từ KGDB, Tool, và tài liệu chính thức 
    để sinh câu trả lời + Citation.
    """
    intent = state.get("intent", "LOGISTICS")
    context = state.get("retrieved_context", "")
    
    response = f"🤖 [AI Assistant Response based on intent: {intent}]\n{context}"
    return {
        "final_response": response,
        "citations": ["01-de-bai.md", "04-rubric.md"]
    }
